import logging
from typing import List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.database import engine
from app.services.cache_service import cache_service

logger = logging.getLogger(__name__)
settings = get_settings()


class SearchService:
    async def ensure_fts_table(self) -> None:
        async with engine.begin() as conn:
            await conn.execute(text("""
                CREATE VIRTUAL TABLE IF NOT EXISTS books_fts USING fts5(
                    title,
                    author,
                    description,
                    content='books',
                    content_rowid='id'
                )
            """))

            await conn.execute(text("""
                CREATE TRIGGER IF NOT EXISTS books_ai AFTER INSERT ON books BEGIN
                    INSERT INTO books_fts(rowid, title, author, description)
                    VALUES (new.id, new.title, new.author, new.description);
                END
            """))

            await conn.execute(text("""
                CREATE TRIGGER IF NOT EXISTS books_ad AFTER DELETE ON books BEGIN
                    INSERT INTO books_fts(books_fts, rowid, title, author, description)
                    VALUES ('delete', old.id, old.title, old.author, old.description);
                END
            """))

            await conn.execute(text("""
                CREATE TRIGGER IF NOT EXISTS books_au AFTER UPDATE ON books BEGIN
                    INSERT INTO books_fts(books_fts, rowid, title, author, description)
                    VALUES ('delete', old.id, old.title, old.author, old.description);
                    INSERT INTO books_fts(rowid, title, author, description)
                    VALUES (new.id, new.title, new.author, new.description);
                END
            """))
        logger.info("FTS5 索引表和触发器已就绪")

    async def search_books(self, query: str, limit: int = 50) -> List[Tuple[int, float]]:
        cache_key = f"search:books:{query}:{limit}"
        cached = await cache_service.get_json(cache_key)
        if cached is not None:
            return cached

        async with engine.begin() as conn:
            result = await conn.execute(
                text("""
                    SELECT b.id,
                           bm25(books_fts) as rank
                    FROM books_fts f
                    JOIN books b ON b.id = f.rowid
                    WHERE books_fts MATCH :query
                    ORDER BY rank
                    LIMIT :limit
                """),
                {"query": query, "limit": limit}
            )
            rows = [(row[0], float(row[1])) for row in result.fetchall()]

        await cache_service.set_json(cache_key, rows, expire=settings.CACHE_EXPIRE_MINUTES * 60)
        return rows

    async def get_suggestions(self, prefix: str, limit: int = 10) -> List[str]:
        cache_key = f"search:suggestions:{prefix}:{limit}"
        cached = await cache_service.get_json(cache_key)
        if cached is not None:
            return cached

        async with engine.begin() as conn:
            result = await conn.execute(
                text("""
                    SELECT DISTINCT title
                    FROM books
                    WHERE title LIKE :prefix
                    ORDER BY updated_at DESC
                    LIMIT :limit
                """),
                {"prefix": f"{prefix}%", "limit": limit}
            )
            suggestions = [row[0] for row in result.fetchall()]

        await cache_service.set_json(cache_key, suggestions, expire=settings.CACHE_EXPIRE_MINUTES * 60)
        return suggestions


search_service = SearchService()
