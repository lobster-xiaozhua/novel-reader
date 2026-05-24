"""Celery 异步爬虫任务模块。

负责将爬虫任务提交到 Celery 消息队列中执行，
支持任务重试、异常捕获和状态管理。
"""
import logging
from celery import shared_task
from django.conf import settings
from .models import CrawlerTask
from utils.crawler_engine import CrawlerEngine

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def run_crawler_task(self, task_id):
    """执行单个爬虫任务的 Celery 异步任务。

    根据 task_id 从数据库加载爬虫任务记录，
    初始化爬虫引擎并执行抓取。如果执行失败，
    自动重试（最多 3 次），每次重试间隔 60 秒。

    Args:
        self: Celery 任务实例（bind=True 时自动注入）。
        task_id: CrawlerTask 记录的主键 ID。
    """
    try:
        task = CrawlerTask.objects.get(id=task_id)
    except CrawlerTask.DoesNotExist:
        logger.error(f'任务 {task_id} 不存在')
        return

    engine = CrawlerEngine(task.id, str(settings.BOOKS_DIR))
    try:
        engine.run(task)
    except Exception as e:
        logger.error(f'任务 {task_id} 执行失败: {e}')
        # 更新任务状态为失败，记录错误信息（截断至 500 字符）
        task.status = 'failed'
        task.error_message = str(e)[:500]
        task.save()
        # 触发 Celery 重试机制，60 秒后重新执行
        raise self.retry(exc=e, countdown=60)
