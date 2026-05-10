import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.database import get_db
from app.models import Chapter, ReadingProgress
from app.core.security import get_current_user_id
from app.schemas.schemas import (
    ChapterResponse, ChapterContentResponse,
    ReadingProgressUpdate, ReadingProgressResponse,
)
from app.services.reading_service import reading_service
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/chapters", tags=["章节"])


@router.get("/{chapter_id}", response_model=ChapterContentResponse)
async def get_chapter(
    chapter_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    chapter = result.scalar_one_or_none()
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    content = await _read_chapter_file(chapter.file_path)
    return ChapterContentResponse(
        id=chapter.id,
        book_id=chapter.book_id,
        chapter_number=chapter.chapter_number,
        title=chapter.title,
        word_count=chapter.word_count,
        content=content or "",
    )


@router.get("/{chapter_id}/next", response_model=ChapterResponse)
async def get_next_chapter(
    chapter_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    current = result.scalar_one_or_none()
    if not current:
        raise HTTPException(status_code=404, detail="章节不存在")

    result = await db.execute(
        select(Chapter).where(
            and_(
                Chapter.book_id == current.book_id,
                Chapter.chapter_number == current.chapter_number + 1,
            )
        )
    )
    next_chapter = result.scalar_one_or_none()
    if not next_chapter:
        raise HTTPException(status_code=404, detail="已经是最后一章")
    return next_chapter


@router.get("/{chapter_id}/prev", response_model=ChapterResponse)
async def get_prev_chapter(
    chapter_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    current = result.scalar_one_or_none()
    if not current:
        raise HTTPException(status_code=404, detail="章节不存在")

    result = await db.execute(
        select(Chapter).where(
            and_(
                Chapter.book_id == current.book_id,
                Chapter.chapter_number == current.chapter_number - 1,
            )
        )
    )
    prev_chapter = result.scalar_one_or_none()
    if not prev_chapter:
        raise HTTPException(status_code=404, detail="已经是第一章")
    return prev_chapter


@router.get("/{chapter_id}/preload")
async def preload_chapters(
    chapter_id: int,
    db: AsyncSession = Depends(get_db),
):
    return await reading_service.get_preload_chapters(chapter_id, db)


@router.post("/reading-progress", response_model=ReadingProgressResponse)
async def update_reading_progress(
    data: ReadingProgressUpdate,
    current_user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    progress = await reading_service.save_progress(
        user_id=current_user_id,
        book_id=data.book_id,
        chapter_id=data.chapter_id,
        position=data.position,
        db=db,
    )
    return progress


@router.get("/reading-progress/{book_id}", response_model=ReadingProgressResponse)
async def get_reading_progress(
    book_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    progress = await reading_service.get_progress(current_user_id, book_id, db)
    if not progress:
        raise HTTPException(status_code=404, detail="无阅读进度")
    return progress


@router.get("/reading-history")
async def get_reading_history(
    limit: int = 20,
    current_user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await reading_service.get_reading_history(current_user_id, limit, db)


async def _read_chapter_file(file_path: str) -> Optional[str]:
    try:
        path = Path(file_path)
        if not path.exists():
            return None
        content = path.read_text(encoding="utf-8", errors="replace")
        lines = content.split("\n", 1)
        if len(lines) > 1:
            return lines[1].strip()
        return content
    except Exception as e:
        logger.error(f"读取章节文件失败: {file_path}, {e}")
        return None
