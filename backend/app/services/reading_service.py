import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import ReadingProgress, Book, Chapter
from app.services.cache_service import cache_service

logger = logging.getLogger(__name__)
settings = get_settings()


class ReadingService:
    PROGRESS_CACHE_PREFIX = "reading:progress:"
    HISTORY_CACHE_PREFIX = "reading:history:"

    async def save_progress(
        self,
        user_id: int,
        book_id: int,
        chapter_id: int,
        position: int,
        db: AsyncSession,
    ) -> ReadingProgress:
        result = await db.execute(
            select(ReadingProgress).where(
                and_(
                    ReadingProgress.user_id == user_id,
                    ReadingProgress.book_id == book_id,
                )
            )
        )
        progress = result.scalar_one_or_none()

        if progress:
            progress.chapter_id = chapter_id
            progress.position = position
            progress.updated_at = datetime.now(timezone.utc)
        else:
            progress = ReadingProgress(
                user_id=user_id,
                book_id=book_id,
                chapter_id=chapter_id,
                position=position,
            )
            db.add(progress)

        await db.flush()

        cache_key = f"{self.PROGRESS_CACHE_PREFIX}{user_id}:{book_id}"
        await cache_service.set_json(cache_key, {
            "book_id": book_id,
            "chapter_id": chapter_id,
            "position": position,
            "updated_at": progress.updated_at.isoformat() if progress.updated_at else None,
        }, expire=3600)

        history_key = f"{self.HISTORY_CACHE_PREFIX}{user_id}"
        await cache_service.delete(history_key)

        logger.debug(f"用户 {user_id} 阅读进度已保存: 书籍 {book_id}, 章节 {chapter_id}, 位置 {position}")
        return progress

    async def get_progress(
        self,
        user_id: int,
        book_id: int,
        db: AsyncSession,
    ) -> Optional[Dict]:
        cache_key = f"{self.PROGRESS_CACHE_PREFIX}{user_id}:{book_id}"
        cached = await cache_service.get_json(cache_key)
        if cached:
            return cached

        result = await db.execute(
            select(ReadingProgress).where(
                and_(
                    ReadingProgress.user_id == user_id,
                    ReadingProgress.book_id == book_id,
                )
            )
        )
        progress = result.scalar_one_or_none()

        if not progress:
            return None

        data = {
            "id": progress.id,
            "book_id": progress.book_id,
            "chapter_id": progress.chapter_id,
            "position": progress.position,
            "updated_at": progress.updated_at.isoformat() if progress.updated_at else None,
        }

        await cache_service.set_json(cache_key, data, expire=3600)
        return data

    async def get_reading_history(
        self,
        user_id: int,
        limit: int = 20,
        db: AsyncSession = None,
    ) -> List[Dict]:
        cache_key = f"{self.HISTORY_CACHE_PREFIX}{user_id}"
        cached = await cache_service.get_json(cache_key)
        if cached:
            return cached

        result = await db.execute(
            select(ReadingProgress)
            .where(ReadingProgress.user_id == user_id)
            .order_by(ReadingProgress.updated_at.desc())
            .limit(limit)
        )
        progress_list = result.scalars().all()

        book_ids = list(set(p.book_id for p in progress_list))
        chapter_ids = list(set(p.chapter_id for p in progress_list))

        book_map = {}
        if book_ids:
            book_result = await db.execute(select(Book).where(Book.id.in_(book_ids)))
            for book in book_result.scalars().all():
                book_map[book.id] = book

        chapter_map = {}
        if chapter_ids:
            chapter_result = await db.execute(select(Chapter).where(Chapter.id.in_(chapter_ids)))
            for chapter in chapter_result.scalars().all():
                chapter_map[chapter.id] = chapter

        history = []
        for p in progress_list:
            book = book_map.get(p.book_id)
            chapter = chapter_map.get(p.chapter_id)
            history.append({
                "book_id": p.book_id,
                "book_title": book.title if book else "未知",
                "chapter_id": p.chapter_id,
                "chapter_title": chapter.title if chapter else "未知",
                "position": p.position,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            })

        await cache_service.set_json(cache_key, history, expire=600)
        return history

    async def get_preload_chapters(
        self,
        chapter_id: int,
        db: AsyncSession,
    ) -> Dict:
        result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
        current = result.scalar_one_or_none()
        if not current:
            return {"current": None, "prev": None, "next": None}

        current_data = await self._chapter_with_content(current)

        prev_data = None
        next_data = None

        result = await db.execute(
            select(Chapter).where(
                and_(
                    Chapter.book_id == current.book_id,
                    Chapter.chapter_number.in_([
                        current.chapter_number - 1,
                        current.chapter_number + 1,
                    ])
                )
            )
        )
        chapters = result.scalars().all()
        for chapter in chapters:
            if chapter.chapter_number == current.chapter_number - 1:
                prev_data = await self._chapter_with_content(chapter)
            elif chapter.chapter_number == current.chapter_number + 1:
                next_data = await self._chapter_with_content(chapter)

        return {
            "current": current_data,
            "prev": prev_data,
            "next": next_data,
        }

    async def _chapter_with_content(self, chapter: Chapter) -> Optional[Dict]:
        content = await self._read_chapter_file(chapter.file_path)
        return {
            "id": chapter.id,
            "book_id": chapter.book_id,
            "chapter_number": chapter.chapter_number,
            "title": chapter.title,
            "word_count": chapter.word_count,
            "content": content,
        }

    async def _read_chapter_file(self, file_path: str) -> Optional[str]:
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


reading_service = ReadingService()
