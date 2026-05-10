import json
import logging
import time
from pathlib import Path
from typing import List, Dict, Optional

from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.database import AsyncSessionLocal, engine
from app.models import Book, Chapter, Tag, BookTag
from app.services.cache_service import cache_service

logger = logging.getLogger(__name__)
settings = get_settings()


class SearchService:
    FTS_TABLE = "chapters_fts"
    BOOK_INDEX_KEY = "search:book_index_version"
    SUGGESTION_PREFIX = "search:suggestions"

    async def ensure_fts_table(self):
        async with engine.begin() as conn:
            await conn.execute(text(f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS {self.FTS_TABLE} USING fts5(
                    chapter_id UNINDEXED,
                    book_id UNINDEXED,
                    title,
                    content,
                    tokenize='unicode61'
                )
            """))
            logger.info("FTS5 索引表已就绪")

    async def rebuild_index(self):
        async with engine.begin() as conn:
            await conn.execute(text(f"DELETE FROM {self.FTS_TABLE}"))

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Chapter))
            chapters = result.scalars().all()

            batch_size = settings.FTS_BATCH_SIZE
            for i in range(0, len(chapters), batch_size):
                batch = chapters[i:i + batch_size]
                await self._index_batch(batch)

            await cache_service.set(self.BOOK_INDEX_KEY, str(int(time.time())))
            logger.info(f"全文索引重建完成，共索引 {len(chapters)} 章")

    async def incremental_update(self):
        index_version = await cache_service.get(self.BOOK_INDEX_KEY)
        if not index_version:
            await self.rebuild_index()
            return

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Chapter).where(
                    Chapter.created_at > time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(float(index_version)))
                )
            )
            new_chapters = result.scalars().all()

            if new_chapters:
                await self._index_batch(new_chapters)
                await cache_service.set(self.BOOK_INDEX_KEY, str(int(time.time())))
                logger.info(f"增量索引更新完成，新增 {len(new_chapters)} 章")
            else:
                logger.debug("无新增章节需要索引")

    async def _index_batch(self, chapters: list):
        async with engine.begin() as conn:
            for chapter in chapters:
                content = await self._read_chapter_content(chapter.file_path)
                if content:
                    content = content[:settings.MAX_CHAPTER_CONTENT_SIZE]
                    await conn.execute(
                        text(f"""
                            INSERT OR REPLACE INTO {self.FTS_TABLE} (chapter_id, book_id, title, content)
                            VALUES (:chapter_id, :book_id, :title, :content)
                        """),
                        {
                            "chapter_id": chapter.id,
                            "book_id": chapter.book_id,
                            "title": chapter.title,
                            "content": content,
                        }
                    )

    async def _read_chapter_content(self, file_path: str) -> Optional[str]:
        try:
            path = Path(file_path)
            if not path.exists():
                return None
            with path.open('r', encoding='utf-8', errors='replace') as f:
                return f.read(settings.MAX_CHAPTER_CONTENT_SIZE)
        except Exception as e:
            logger.error(f"读取章节文件失败: {file_path}, {e}")
            return None

    async def search_books(self, query: str, page: int = 1, page_size: int = 20, db: AsyncSession = None) -> Dict:
        cache_key = f"search:books:{query}:{page}:{page_size}"
        cached = await cache_service.get_json(cache_key)
        if cached:
            return cached

        stmt = select(Book).where(
            Book.title.contains(query) | Book.author.contains(query)
        ).order_by(Book.title)

        total_result = await db.execute(
            select(func.count()).select_from(stmt.subquery())
        )
        total = total_result.scalar()

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(stmt)
        books = result.scalars().all()

        items = []
        for book in books:
            items.append({
                "id": book.id,
                "title": book.title,
                "author": book.author,
                "total_chapters": book.total_chapters,
                "relevance": 1.0 if query.lower() in (book.title or "").lower() else 0.5,
            })

        response = {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

        await cache_service.set_json(cache_key, response, expire=settings.CACHE_EXPIRE_MINUTES * 60)
        return response

    async def search_content(self, query: str, book_id: Optional[int] = None,
                             page: int = 1, page_size: int = 20, db: AsyncSession = None) -> Dict:
        cache_key = f"search:content:{query}:{book_id}:{page}:{page_size}"
        cached = await cache_service.get_json(cache_key)
        if cached:
            return cached

        book_filter = f"AND book_id = {book_id}" if book_id else ""
        sql = text(f"""
            SELECT
                fts.chapter_id,
                fts.book_id,
                fts.title,
                snippet({self.FTS_TABLE}, 3, '【', '】', '...', 30) as snippet,
                rank
            FROM {self.FTS_TABLE} fts
            WHERE {self.FTS_TABLE} MATCH :query
            {book_filter}
            ORDER BY rank
            LIMIT :limit OFFSET :offset
        """)

        count_sql = text(f"""
            SELECT COUNT(*)
            FROM {self.FTS_TABLE}
            WHERE {self.FTS_TABLE} MATCH :query
            {book_filter}
        """)

        offset = (page - 1) * page_size
        try:
            count_result = await db.execute(count_sql, {"query": query})
            total = count_result.scalar()

            result = await db.execute(sql, {"query": query, "limit": page_size, "offset": offset})
            rows = result.fetchall()

            book_ids = list(set(row.book_id for row in rows))
            book_map = {}
            if book_ids:
                book_result = await db.execute(select(Book).where(Book.id.in_(book_ids)))
                for book in book_result.scalars().all():
                    book_map[book.id] = book

            items = []
            for row in rows:
                book = book_map.get(row.book_id)
                items.append({
                    "chapter_id": row.chapter_id,
                    "book_id": row.book_id,
                    "book_title": book.title if book else "",
                    "chapter_title": row.title,
                    "snippet": row.snippet,
                    "relevance": -row.rank if row.rank else 0,
                })

            response = {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
            }

            await cache_service.set_json(cache_key, response, expire=settings.CACHE_EXPIRE_MINUTES * 60)
            return response

        except Exception as e:
            logger.error(f"全文搜索失败: {e}")
            return {"items": [], "total": 0, "page": page, "page_size": page_size}

    async def get_suggestions(self, query: str, limit: int = 10, db: AsyncSession = None) -> List[Dict]:
        cache_key = f"{self.SUGGESTION_PREFIX}:{query}:{limit}"
        cached = await cache_service.get_json(cache_key)
        if cached:
            return cached

        suggestions = []

        book_result = await db.execute(
            select(Book).where(Book.title.contains(query)).limit(limit)
        )
        books = book_result.scalars().all()
        for book in books:
            suggestions.append({"text": book.title, "type": "book"})

        author_result = await db.execute(
            select(Book.author).where(Book.author.contains(query)).distinct().limit(limit // 2)
        )
        authors = author_result.scalars().all()
        for author in authors:
            if author and {"text": author, "type": "author"} not in suggestions:
                suggestions.append({"text": author, "type": "author"})

        tag_result = await db.execute(
            select(Tag).where(Tag.name.contains(query)).limit(limit // 3)
        )
        tags = tag_result.scalars().all()
        for tag in tags:
            suggestions.append({"text": tag.name, "type": "tag"})

        suggestions = suggestions[:limit]
        await cache_service.set_json(cache_key, suggestions, expire=300)
        return suggestions

    async def search_by_tag(self, tag_name: str, page: int = 1, page_size: int = 20, db: AsyncSession = None) -> Dict:
        cache_key = f"search:tag:{tag_name}:{page}:{page_size}"
        cached = await cache_service.get_json(cache_key)
        if cached:
            return cached

        stmt = (
            select(Book)
            .join(BookTag, Book.id == BookTag.c.book_id)
            .join(Tag, BookTag.c.tag_id == Tag.id)
            .where(Tag.name == tag_name)
        )

        total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
        total = total_result.scalar()

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(stmt)
        books = result.scalars().all()

        items = [
            {
                "id": book.id,
                "title": book.title,
                "author": book.author,
                "total_chapters": book.total_chapters,
                "relevance": 1.0,
            }
            for book in books
        ]

        response = {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

        await cache_service.set_json(cache_key, response, expire=settings.CACHE_EXPIRE_MINUTES * 60)
        return response

    async def delete_chapter_index(self, chapter_id: int):
        async with engine.begin() as conn:
            await conn.execute(
                text(f"DELETE FROM {self.FTS_TABLE} WHERE chapter_id = :id"),
                {"id": chapter_id}
            )

    async def invalidate_cache(self, pattern: str = "search:"):
        logger.info(f"搜索缓存已失效 (pattern: {pattern})")


search_service = SearchService()
