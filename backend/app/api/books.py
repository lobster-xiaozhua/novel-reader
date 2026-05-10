import logging
import re
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional

from app.database import get_db
from app.models import Book, Chapter
from app.core.security import get_current_user_id
from app.core.config import get_settings
from app.schemas.schemas import BookResponse, BookCreate, BookListResponse, ChapterResponse
from app.services.scan_service import BookScanner

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/books", tags=["书籍"])


@router.get("", response_model=BookListResponse)
async def get_books(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    db: AsyncSession = Depends(get_db),
):
    query = select(Book)

    if search:
        query = query.where(
            (Book.title.contains(search)) | (Book.author.contains(search))
        )

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar()

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    books = result.scalars().all()

    return {
        "items": books,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.get("/{book_id}", response_model=BookResponse)
async def get_book(book_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")
    return book


@router.post("/scan")
async def scan_books(
    background_tasks: BackgroundTasks,
    current_user_id: int = Depends(get_current_user_id),
):
    scanner = BookScanner()
    background_tasks.add_task(scanner.scan_directory)
    logger.info(f"用户 {current_user_id} 触发书籍扫描")
    return {"message": "扫描任务已启动"}


@router.post("/upload")
async def upload_book(
    file: UploadFile = File(..., description="上传的TXT文件"),
    current_user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith('.txt'):
        raise HTTPException(status_code=400, detail="仅支持 TXT 文件上传")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="文件为空")

    safe_name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', Path(file.filename).stem)
    if not safe_name or safe_name.startswith('.'):
        safe_name = "unnamed"
    safe_name = safe_name[:100]

    book_dir = Path(settings.BOOKS_DIR) / safe_name
    book_dir.mkdir(parents=True, exist_ok=True)

    dest = (book_dir / f"{safe_name}.txt").resolve()
    books_dir_resolved = Path(settings.BOOKS_DIR).resolve()
    if not str(dest).startswith(str(books_dir_resolved)):
        raise HTTPException(status_code=400, detail="非法文件名")

    dest.write_bytes(content)

    book = Book(
        title=safe_name,
        folder_path=str(book_dir),
        total_chapters=1,
    )
    db.add(book)
    await db.commit()
    await db.refresh(book)

    chapter = Chapter(
        book_id=book.id,
        chapter_number=1,
        title=safe_name,
        file_path=str(dest),
        word_count=len(content),
    )
    db.add(chapter)
    await db.commit()

    logger.info(f"用户 {current_user_id} 上传书籍: {safe_name}")
    return {"message": "文件上传成功", "filename": f"{safe_name}.txt", "book_id": book.id}


@router.get("/{book_id}/chapters", response_model=List[ChapterResponse])
async def get_chapters(
    book_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Chapter).where(Chapter.book_id == book_id).order_by(Chapter.chapter_number)
    )
    chapters = result.scalars().all()
    return chapters


@router.put("/{book_id}", response_model=BookResponse)
async def update_book(
    book_id: int,
    book_data: BookCreate,
    current_user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")

    book.title = book_data.title
    book.author = book_data.author
    book.description = book_data.description
    await db.commit()
    await db.refresh(book)

    logger.info(f"用户 {current_user_id} 更新书籍: {book.title}")
    return book


@router.delete("/{book_id}")
async def delete_book(
    book_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")

    chapters_result = await db.execute(
        select(Chapter).where(Chapter.book_id == book_id)
    )
    chapters = chapters_result.scalars().all()
    for chapter in chapters:
        await db.delete(chapter)

    await db.delete(book)
    await db.commit()

    try:
        book_dir = Path(book.folder_path)
        if book_dir.exists():
            shutil.rmtree(book_dir)
    except Exception as e:
        logger.error(f"删除书籍文件夹失败: {e}")

    logger.info(f"用户 {current_user_id} 删除书籍: {book.title}")
    return {"message": "书籍已删除"}
