import json
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import CrawlerTask
from .tasks import run_crawler_task

logger = logging.getLogger(__name__)


@login_required
def crawler_tasks(request):
    tasks = CrawlerTask.objects.filter(user=request.user)
    return render(request, 'crawler/tasks.html', {'tasks': tasks})


@login_required
@require_POST
def create_task(request):
    url = request.POST.get('url', '').strip()
    if not url:
        messages.error(request, '请输入URL')
        return redirect('crawler_tasks')

    task = CrawlerTask.objects.create(user=request.user, url=url)
    logger.info(f'创建爬虫任务: {task.id} - {url}')

    run_crawler_task.delay(task.id)

    messages.success(request, '爬虫任务已创建')
    return redirect('crawler_tasks')


@login_required
def task_detail(request, pk):
    task = get_object_or_404(CrawlerTask, pk=pk, user=request.user)
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
