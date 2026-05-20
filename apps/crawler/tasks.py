import logging
from celery import shared_task
from django.conf import settings
from .models import CrawlerTask
from utils.crawler_engine import CrawlerEngine

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def run_crawler_task(self, task_id):
    try:
        task = CrawlerTask.objects.get(id=task_id)
    except CrawlerTask.DoesNotExist:
        logger.error(f"任务 {task_id} 不存在")
        return

    engine = CrawlerEngine(task.id, str(settings.BOOKS_DIR))
    try:
        engine.run(task)
    except Exception as e:
        logger.error(f"任务 {task_id} 执行失败: {e}")
        task.status = "failed"
        task.error_message = str(e)[:500]
        task.save()
        raise self.retry(exc=e, countdown=60)
