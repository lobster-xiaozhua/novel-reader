import json
import logging
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import CrawlerTask
from .tasks import run_crawler_task

logger = logging.getLogger(__name__)


@login_required
def crawler_tasks(request):
    tasks = CrawlerTask.objects.filter(user=request.user)
    return JsonResponse({
        'items': [{
            'id': t.id,
            'url': t.url,
            'status': t.status,
            'total_chapters': t.total_chapters,
            'downloaded_chapters': t.downloaded_chapters,
            'error_message': t.error_message,
            'created_at': t.created_at.isoformat(),
            'updated_at': t.updated_at.isoformat(),
        } for t in tasks],
        'total': tasks.count(),
    })


@login_required
@require_POST
def create_task(request):
    import json
    data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
    url = data.get('url', '').strip()
    if not url:
        return JsonResponse({'success': False, 'error': '请输入URL'}, status=400)

    task = CrawlerTask.objects.create(user=request.user, url=url)
    logger.info(f'创建爬虫任务: {task.id} - {url}')
    run_crawler_task.delay(task.id)

    return JsonResponse({'success': True, 'task_id': task.id})


@login_required
def task_detail(request, pk):
    task = CrawlerTask.objects.get(pk=pk, user=request.user)
    logs = []
    if task.logs:
        try:
            logs = json.loads(task.logs)
        except Exception as e:
            logger.warning(f'解析任务日志失败: {e}')
    return JsonResponse({
        'id': task.id,
        'status': task.status,
        'total_chapters': task.total_chapters,
        'downloaded_chapters': task.downloaded_chapters,
        'error_message': task.error_message,
        'logs': logs,
    })
