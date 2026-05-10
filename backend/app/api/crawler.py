import logging
import uuid
from datetime import datetime
from typing import Optional

import aiohttp
from bs4 import BeautifulSoup
from fastapi import APIRouter, Depends, BackgroundTasks, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential

from app.database import get_db_no_commit
from app.models import CrawlerTask
from app.schemas.schemas import CrawlerTaskCreate, CrawlerTaskResponse
from app.core.security import get_current_user_id
from app.core.config import get_settings
from app.core.exceptions import NotFoundError, CrawlerError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/crawler", tags=["爬虫"])
settings = get_settings()


@router.get("/tasks", response_model=list[CrawlerTaskResponse])
async def list_tasks(
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db_no_commit),
    current_user_id: int = Depends(get_current_user_id),
):
    query = select(CrawlerTask).where(CrawlerTask.user_id == current_user_id).order_by(CrawlerTask.created_at.desc())
    if status_filter:
        query = query.where(CrawlerTask.status == status_filter)

    result = await db.execute(query)
    tasks = result.scalars().all()
    return [CrawlerTaskResponse.model_validate(t) for t in tasks]


@router.get("/tasks/{task_id}", response_model=CrawlerTaskResponse)
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db_no_commit),
    current_user_id: int = Depends(get_current_user_id),
):
    result = await db.execute(
        select(CrawlerTask).where(CrawlerTask.id == task_id, CrawlerTask.user_id == current_user_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise NotFoundError("任务", str(task_id))
    return task


@router.post("/tasks", response_model=CrawlerTaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: CrawlerTaskCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_no_commit),
    current_user_id: int = Depends(get_current_user_id),
):
    task = CrawlerTask(
        url=task_data.url,
        status="pending",
        user_id=current_user_id,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    background_tasks.add_task(execute_crawl, task.id)

    logger.info(f"爬虫任务已创建: {task.id}")
    return task


async def execute_crawl(task_id: int):
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(CrawlerTask).where(CrawlerTask.id == task_id))
            task = result.scalar_one_or_none()
            if not task:
                return

            task.status = "running"
            await db.commit()

            try:
                await crawl_url(task.url)
                task.status = "completed"
                task.downloaded_chapters = 1
                task.total_chapters = 1
            except Exception as e:
                logger.error(f"爬虫任务失败: {task_id} - {e}")
                task.status = "failed"
                task.error_message = str(e)

            task.updated_at = datetime.utcnow()
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error(f"爬虫任务执行异常: {task_id} - {e}")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
async def crawl_url(url: str):
    timeout = aiohttp.ClientTimeout(total=settings.CRAWLER_TIMEOUT)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise CrawlerError(f"HTTP {response.status}")
            await response.text()
