import json
import threading
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import CrawlerTask
from utils.crawler_engine import CrawlerEngine
from django.conf import settings


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

    # Start crawler in background thread
    engine = CrawlerEngine(task.id, settings.BOOKS_DIR)
    thread = threading.Thread(target=engine.run, args=(task,))
    thread.daemon = True
    thread.start()

    messages.success(request, '爬虫任务已创建')
    return redirect('crawler_tasks')


@login_required
def task_detail(request, pk):
    task = get_object_or_404(CrawlerTask, pk=pk, user=request.user)
    logs = []
    if task.logs:
        try:
            logs = json.loads(task.logs)
        except Exception:
            pass
    return JsonResponse({
        'id': task.id,
        'status': task.status,
        'total_chapters': task.total_chapters,
        'downloaded_chapters': task.downloaded_chapters,
        'error_message': task.error_message,
        'logs': logs,
    })
