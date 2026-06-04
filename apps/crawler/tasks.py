import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone
from .models import CrawlerTask
from utils.crawler_engine import CrawlerEngine

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def run_crawler_task(self, task_id):
    try:
        task = CrawlerTask.objects.get(id=task_id)
    except CrawlerTask.DoesNotExist:
        logger.error(f'任务 {task_id} 不存在')
        return

    # 超时检测：pending 超过 30 分钟视为超时
    if task.status == 'pending':
        timeout = task.created_at + timedelta(minutes=30)
        if timezone.now() > timeout:
            task.status = 'failed'
            task.error_message = '任务等待超时（30分钟未开始执行）'
            task.save()
            logger.warning(f'[Crawler] 任务超时: {task_id}')
            return

    engine = CrawlerEngine(task.id, str(settings.BOOKS_DIR))
    try:
        engine.run(task)
    except Exception as e:
        logger.error(f'任务 {task_id} 执行失败: {e}')
        task.status = 'failed'
        task.error_message = str(e)[:500]
        task.save()
        raise self.retry(exc=e, countdown=60)
