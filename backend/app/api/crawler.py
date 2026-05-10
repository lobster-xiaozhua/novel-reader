import logging

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.models import CrawlerTask
from app.core.security import get_current_user_id
from app.schemas.schemas import CrawlerTaskCreate, CrawlerTaskResponse
from app.services.crawler_service import crawler_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/crawler", tags=["爬虫"])


@router.post("/tasks", response_model=CrawlerTaskResponse)
async def create_task(
    data: CrawlerTaskCreate,
    background_tasks: BackgroundTasks,
    current_user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    task = CrawlerTask(url=data.url, status="pending")
    db.add(task)
    await db.commit()
    await db.refresh(task)

    background_tasks.add_task(crawler_service.run_task, task.id)
    logger.info(f"爬虫任务已创建: id={task.id}, url={data.url}")
    return task


@router.get("/tasks", response_model=List[CrawlerTaskResponse])
async def get_tasks(
    page: int = 1,
    page_size: int = 20,
    current_user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CrawlerTask)
        .order_by(CrawlerTask.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return result.scalars().all()


@router.get("/tasks/{task_id}", response_model=CrawlerTaskResponse)
async def get_task(
    task_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(CrawlerTask).where(CrawlerTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@router.get("/tasks/{task_id}/logs")
async def get_task_logs(
    task_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(CrawlerTask).where(CrawlerTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    import json
    try:
        logs = json.loads(task.logs) if task.logs else []
    except (json.JSONDecodeError, TypeError):
        logs = []

    return {"logs": logs, "status": task.status, "error_message": task.error_message}


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(CrawlerTask).where(CrawlerTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status not in ["pending", "running"]:
        raise HTTPException(status_code=400, detail="任务无法取消")

    task.status = "cancelled"
    crawler_service.cancel_task(task_id)
    await db.commit()

    logger.info(f"爬虫任务已取消: id={task_id}")
    return {"message": "任务已取消"}
