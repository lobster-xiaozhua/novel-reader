import os
import logging
from pathlib import Path
from typing import List, Dict

import aiofiles

from app.core.config import get_settings
from app.database import AsyncSessionLocal
from app.models import Book, Chapter

logger = logging.getLogger(__name__)
settings = get_settings()


class BookScanner:
    ALLOWED_EXTENSIONS = {'.txt'}
    AUTO_CONVERT_EXTENSIONS = {'.md', '.markdown'}
    SYSTEM_FILES = {'.ds_store', 'thumbs.db', 'desktop.ini'}
    TEMP_PATTERNS = ['~', '.tmp', '.temp', '.bak', '.swp']

    def __init__(self, books_dir: str = None):
        self.books_dir = Path(books_dir or settings.BOOKS_DIR)

    async def scan_directory(self):
        if not self.books_dir.exists():
            logger.warning(f"书籍目录不存在: {self.books_dir}")
            self.books_dir.mkdir(parents=True, exist_ok=True)
            return

        logger.info(f"开始扫描目录: {self.books_dir}")

        cleaned = 0
        converted = 0
        for root, dirs, files in os.walk(self.books_dir):
            for filename in files:
                file_path = Path(root) / filename
                result = await self.process_file(file_path)
                if result == "deleted":
                    cleaned += 1
                elif result == "converted":
                    converted += 1

        books_added = await self._register_books()

        logger.info(f"扫描完成: 清理 {cleaned} 个文件, 转换 {converted} 个文件, 注册 {books_added} 本书籍")

    async def process_file(self, file_path: Path) -> str:
        filename = file_path.name
        ext = file_path.suffix.lower()
        filename_lower = filename.lower()

        if filename_lower in self.SYSTEM_FILES:
            await self.delete_file(file_path, "系统文件")
            return "deleted"

        if self.is_temp_file(filename):
            await self.delete_file(file_path, "临时文件")
            return "deleted"

        if ext in self.AUTO_CONVERT_EXTENSIONS:
            new_path = file_path.with_suffix('.txt')
            await self.rename_file(file_path, new_path, "格式转换")
            return "converted"

        if ext not in self.ALLOWED_EXTENSIONS:
            await self.delete_file(file_path, f"不支持的格式: {ext}")
            return "deleted"

        if file_path.stat().st_size == 0:
            await self.delete_file(file_path, "空文件")
            return "deleted"

        if not await self.is_readable(file_path):
            await self.delete_file(file_path, "文件损坏")
            return "deleted"

        return "ok"

    def is_temp_file(self, filename: str) -> bool:
        lower_name = filename.lower()
        return any(pattern in lower_name for pattern in self.TEMP_PATTERNS)

    async def delete_file(self, path: Path, reason: str):
        try:
            path.unlink()
            logger.info(f"删除文件: {path}, 原因: {reason}")
        except Exception as e:
            logger.error(f"删除文件失败: {path}, 错误: {e}")

    async def rename_file(self, old_path: Path, new_path: Path, reason: str):
        try:
            old_path.rename(new_path)
            logger.info(f"重命名文件: {old_path} -> {new_path}, 原因: {reason}")
        except Exception as e:
            logger.error(f"重命名文件失败: {old_path}, 错误: {e}")

    async def is_readable(self, path: Path) -> bool:
        try:
            async with aiofiles.open(path, 'r', encoding='utf-8') as f:
                await f.read(1024)
            return True
        except UnicodeDecodeError:
            try:
                async with aiofiles.open(path, 'r', encoding='gbk') as f:
                    await f.read(1024)
                return True
            except Exception:
                return False
        except Exception:
            return False

    async def _register_books(self) -> int:
        from sqlalchemy import select

        added = 0
        async with AsyncSessionLocal() as db:
            if not self.books_dir.exists():
                return 0

            for book_dir in sorted(self.books_dir.iterdir()):
                if not book_dir.is_dir():
                    continue

                book_name = book_dir.name
                result = await db.execute(
                    select(Book).where(Book.folder_path == str(book_dir))
                )
                existing_book = result.scalar_one_or_none()

                if existing_book:
                    await self._update_book_chapters(db, existing_book, book_dir)
                    continue

                chapter_files = sorted([
                    f for f in book_dir.iterdir()
                    if f.is_file() and f.suffix.lower() == '.txt'
                ])

                if not chapter_files:
                    continue

                book = Book(
                    title=book_name,
                    author=await self._detect_author(book_dir),
                    folder_path=str(book_dir),
                    description="",
                    total_chapters=len(chapter_files),
                )
                db.add(book)
                await db.flush()

                for idx, chapter_file in enumerate(chapter_files, 1):
                    title = await self._extract_chapter_title(chapter_file)
                    word_count = await self._count_words(chapter_file)
                    chapter = Chapter(
                        book_id=book.id,
                        chapter_number=idx,
                        title=title,
                        file_path=str(chapter_file),
                        word_count=word_count,
                    )
                    db.add(chapter)

                added += 1
                logger.info(f"注册书籍: {book_name}, {len(chapter_files)} 章")

            await db.commit()

        return added

    async def _update_book_chapters(self, db, book: Book, book_dir: Path):
        from sqlalchemy import select

        chapter_files = sorted([
            f for f in book_dir.iterdir()
            if f.is_file() and f.suffix.lower() == '.txt'
        ])

        result = await db.execute(
            select(Chapter).where(Chapter.book_id == book.id)
        )
        existing_chapters = {c.chapter_number: c for c in result.scalars().all()}

        current_count = 0
        for idx, chapter_file in enumerate(chapter_files, 1):
            current_count = idx
            if idx in existing_chapters:
                continue

            title = await self._extract_chapter_title(chapter_file)
            word_count = await self._count_words(chapter_file)
            chapter = Chapter(
                book_id=book.id,
                chapter_number=idx,
                title=title,
                file_path=str(chapter_file),
                word_count=word_count,
            )
            db.add(chapter)

        if book.total_chapters != current_count:
            book.total_chapters = current_count
            logger.info(f"更新书籍章节数: {book.title}, {current_count} 章")

    async def _detect_author(self, book_dir: Path) -> str:
        info_file = book_dir / "info.txt"
        if info_file.exists():
            try:
                async with aiofiles.open(info_file, 'r', encoding="utf-8", errors="replace") as f:
                    content = await f.read()
                for line in content.splitlines()[:5]:
                    if "作者" in line:
                        parts = line.split("：", 1)
                        if len(parts) == 2:
                            return parts[1].strip()
                        parts = line.split(":", 1)
                        if len(parts) == 2:
                            return parts[1].strip()
            except Exception:
                pass
        return ""

    async def _extract_chapter_title(self, chapter_file: Path) -> str:
        try:
            async with aiofiles.open(chapter_file, 'r', encoding='utf-8', errors='replace') as f:
                first_line = (await f.readline()).strip()
            if first_line and len(first_line) < 100:
                return first_line
        except Exception:
            pass
        return chapter_file.stem

    async def _count_words(self, chapter_file: Path) -> int:
        try:
            async with aiofiles.open(chapter_file, 'r', encoding="utf-8", errors="replace") as f:
                content = await f.read()
            return len(content)
        except Exception:
            return 0
