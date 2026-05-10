import logging
import os
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_no_commit
from app.models import Book, Chapter
from app.schemas.schemas import ChapterContentResponse
from app.core.security import get_current_user_id
from app.core.config import get_settings
from app.core.exceptions import NotFoundError, PermissionError, DatabaseError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chapters", tags=["章节"])
settings = get_settings()

DATA_DIR = Path(settings.DATA_DIR).resolve()


def _validate_path(file_path: Path) -> Path:
    resolved = file_path.resolve()
    if not str(resolved).startswith(str(DATA_DIR)):
        raise PermissionError("访问路径被拒绝")
    return resolved


@router.get("/{chapter_id}", response_model=ChapterContentResponse)
async def get_chapter(
    chapter_id: int,
    db: AsyncSession = Depends(get_db_no_commit),
):
    result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    chapter = result.scalar_one_or_none()
    if not chapter:
        raise NotFoundError("章节", str(chapter_id))

    content = ""
    file_path = _validate_path(Path(chapter.file_path))
    if file_path.exists() and file_path.is_file():
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            logger.error(f"读取章节文件失败: {file_path} - {e}")
            raise DatabaseError("章节内容读取失败")

    if len(content) > settings.MAX_CHAPTER_CONTENT_SIZE:
        content = content[:settings.MAX_CHAPTER_CONTENT_SIZE]

    return ChapterContentResponse(
        id=chapter.id,
        book_id=chapter.book_id,
        chapter_number=chapter.chapter_number,
        title=chapter.title,
        word_count=chapter.word_count,
        content=content,
    )


@router.get("/{chapter_id}/file")
async def get_chapter_file(
    chapter_id: int,
    db: AsyncSession = Depends(get_db_no_commit),
):
    result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    chapter = result.scalar_one_or_none()
    if not chapter:
        raise NotFoundError("章节", str(chapter_id))

    file_path = _validate_path(Path(chapter.file_path))
    if not file_path.exists() or not file_path.is_file():
        raise NotFoundError("章节文件")

    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type="text/plain; charset=utf-8",
    )
