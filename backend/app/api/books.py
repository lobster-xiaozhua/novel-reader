import logging
import math
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_no_commit
from app.models import Book, Chapter
from app.schemas.schemas import BookCreate, BookResponse, BookListResponse, ChapterResponse
from app.core.security import get_current_user_id
from app.core.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/books", tags=["书籍"])
settings = get_settings()

DATA_DIR = Path(settings.DATA_DIR).resolve()


def _validate_path(file_path: Path) -> Path:
    resolved = file_path.resolve()
    if not str(resolved).startswith(str(DATA_DIR)):
        raise HTTPException(status_code=403, detail="访问路径被拒绝")
    return resolved


@router.get("", response_model=BookListResponse)
async def list_books(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    author: Optional[str] = None,
    db: AsyncSession = Depends(get_db_no_commit),
):
    query = select(Book)
    count_query = select(func.count(Book.id))

    if author:
        query = query.where(Book.author.ilike(f"%{author}%"))
        count_query = count_query.where(Book.author.ilike(f"%{author}%"))

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.order_by(Book.updated_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    books = result.scalars().all()

    return BookListResponse(
        items=[BookResponse.model_validate(b) for b in books],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get("/{book_id}", response_model=BookResponse)
async def get_book(book_id: int, db: AsyncSession = Depends(get_db_no_commit)):
    result = await db.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")
    return book


@router.post("", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def create_book(
    book_data: BookCreate,
    db: AsyncSession = Depends(get_db_no_commit),
    current_user_id: int = Depends(get_current_user_id),
):
    folder_path = _validate_path(Path(book_data.folder_path))
    if not folder_path.exists():
        folder_path.mkdir(parents=True, exist_ok=True)

    book = Book(
        title=book_data.title,
        author=book_data.author,
        description=book_data.description,
        folder_path=str(folder_path),
    )
    db.add(book)
    await db.commit()
    await db.refresh(book)

    logger.info(f"书籍创建成功: {book.id} - {book.title}")
    return book


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(
    book_id: int,
    db: AsyncSession = Depends(get_db_no_commit),
    current_user_id: int = Depends(get_current_user_id),
):
    result = await db.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")

    folder_path = _validate_path(Path(book.folder_path))
    if folder_path.exists():
        import shutil
        try:
            shutil.rmtree(folder_path)
        except OSError as e:
            logger.warning(f"删除书籍文件夹失败: {folder_path} - {e}")

    await db.delete(book)
    await db.commit()
    logger.info(f"书籍已删除: {book_id}")


@router.get("/{book_id}/chapters", response_model=list[ChapterResponse])
async def list_chapters(book_id: int, db: AsyncSession = Depends(get_db_no_commit)):
    result = await db.execute(
        select(Chapter)
        .where(Chapter.book_id == book_id)
        .order_by(Chapter.chapter_number)
    )
    chapters = result.scalars().all()
    return [ChapterResponse.model_validate(c) for c in chapters]
