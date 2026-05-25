import json
import logging

from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.errors import HttpError
from ninja.pagination import paginate

from apps.crawler.models import CrawlerTask

from .auth import jwt_auth
from .schemas import CrawlerTaskDetailSchema, CrawlerTaskIn, CrawlerTaskSchema

logger = logging.getLogger(__name__)
router = Router()


@router.get('/crawler/', response=list[CrawlerTaskSchema], auth=jwt_auth)
@paginate
def list_crawler_tasks(request):
    return CrawlerTask.objects.filter(user=request.user)


@router.post('/crawler/', response=CrawlerTaskSchema, auth=jwt_auth)
def create_crawler_task(request, payload: CrawlerTaskIn) -> CrawlerTask:
    from utils.crawler_engine import validate_crawl_url
    if not validate_crawl_url(payload.url):
        raise HttpError(400, '目标 URL 不合法或指向内网地址')
    active_count: int = CrawlerTask.objects.filter(
        user=request.user, status__in=['pending', 'running']
    ).count()
    if active_count >= 5:
        raise HttpError(429, '当前已有过多运行中的任务，请稍后再试')
    task = CrawlerTask.objects.create(user=request.user, url=payload.url, status='pending')
    from apps.crawler.tasks import run_crawler_task
    run_crawler_task.delay(task.id)
    logger.info(f'[Crawler] 创建任务: {task.id} - {payload.url}')
    return task


@router.get('/crawler/{task_id}/', response=CrawlerTaskDetailSchema, auth=jwt_auth)
def get_crawler_task(request, task_id: int) -> dict:
    task = get_object_or_404(CrawlerTask, id=task_id, user=request.user)
    logs: list = []
    if task.logs:
        try:
            logs = json.loads(task.logs)
        except Exception as exc:
            logger.warning(f'[Crawler] 解析任务日志失败: {exc}')
    return {
        'id': task.id,
        'url': task.url,
        'status': task.status,
        'total_chapters': task.total_chapters,
        'downloaded_chapters': task.downloaded_chapters,
        'error_message': task.error_message,
        'logs': logs,
        'created_at': task.created_at.isoformat(),
        'updated_at': task.updated_at.isoformat(),
    }
