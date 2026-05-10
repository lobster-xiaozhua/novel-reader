import logging
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Book
from app.schemas.schemas import SearchResult, SearchSuggestion
from app.core.security import get_current_user_id
from app.services.search_service import search_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/search", tags=["搜索"])


@router.get("", response_model=List[SearchResult])
async def search_books(
    q: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(50, ge=1, le=100),
    current_user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        results = await search_service.search_books(q, limit)
        search_results = []
        for book_id, relevance in results:
            book_result = await db.execute(select(Book).where(Book.id == book_id))
            book = book_result.scalar_one_or_none()
            search_results.append(SearchResult(
                id=book_id,
                title=book.title if book else "",
                author=book.author if book else None,
                relevance=relevance,
            ))
        return search_results
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        return []


@router.get("/suggestions", response_model=List[SearchSuggestion])
async def get_suggestions(
    q: str = Query(..., min_length=1, max_length=50),
    limit: int = Query(10, ge=1, le=20),
    current_user_id: int = Depends(get_current_user_id),
):
    try:
        suggestions = await search_service.get_suggestions(q, limit)
        return [SearchSuggestion(text=s, type="book") for s in suggestions]
    except Exception as e:
        logger.error(f"获取建议失败: {e}")
        return []
