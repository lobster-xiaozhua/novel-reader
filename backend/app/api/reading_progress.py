import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_no_commit
from app.models import ReadingProgress, Book, Chapter
from app.schemas.schemas import ReadingProgressUpdate, ReadingProgressResponse
from app.core.security import get_current_user_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reading-progress", tags=["阅读进度"])


@router.get("/book/{book_id}", response_model=ReadingProgressResponse)
async def get_progress(
    book_id: int,
    db: AsyncSession = Depends(get_db_no_commit),
    current_user_id: int = Depends(get_current_user_id),
):
    """获取指定书籍的阅读进度。"""
    result = await db.execute(
        select(ReadingProgress)
        .where(
            ReadingProgress.user_id == current_user_id,
            ReadingProgress.book_id == book_id,
        )
    )
    progress = result.scalar_one_or_none()
    if not progress:
        raise HTTPException(status_code=404, detail="暂无阅读进度")
    return progress


@router.post("/book/{book_id}", response_model=ReadingProgressResponse)
async def update_progress(
    book_id: int,
    data: ReadingProgressUpdate,
    db: AsyncSession = Depends(get_db_no_commit),
    current_user_id: int = Depends(get_current_user_id),
):
    """更新指定书籍的阅读进度。"""
    book_result = await db.execute(select(Book).where(Book.id == book_id))
    book = book_result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")

    chapter_result = await db.execute(
        select(Chapter).where(Chapter.id == data.chapter_id, Chapter.book_id == book_id)
    )
    chapter = chapter_result.scalar_one_or_none()
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    result = await db.execute(
        select(ReadingProgress)
        .where(
            ReadingProgress.user_id == current_user_id,
            ReadingProgress.book_id == book_id,
        )
    )
    progress = result.scalar_one_or_none()

    if progress:
        progress.chapter_id = data.chapter_id
        progress.position = data.position
    else:
        progress = ReadingProgress(
            user_id=current_user_id,
            book_id=book_id,
            chapter_id=data.chapter_id,
            position=data.position,
        )
        db.add(progress)

    await db.commit()
    await db.refresh(progress)

    logger.info(f"阅读进度更新: user={current_user_id}, book={book_id}, chapter={data.chapter_id}")
    return progress


@router.delete("/book/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_progress(
    book_id: int,
    db: AsyncSession = Depends(get_db_no_commit),
    current_user_id: int = Depends(get_current_user_id),
):
    """删除指定书籍的阅读进度。"""
    result = await db.execute(
        select(ReadingProgress)
        .where(
            ReadingProgress.user_id == current_user_id,
            ReadingProgress.book_id == book_id,
        )
    )
    progress = result.scalar_one_or_none()
    if not progress:
        raise HTTPException(status_code=404, detail="阅读进度不存在")

    await db.delete(progress)
    await db.commit()
    logger.info(f"阅读进度已删除: user={current_user_id}, book={book_id}")
