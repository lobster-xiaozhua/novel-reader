import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.database import get_db
from app.core.security import get_current_user_id
from app.services.search_service import search_service
from app.schemas.schemas import SearchResult, SearchSuggestion

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/search", tags=["搜索"])


@router.get("/books")
async def search_books(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await search_service.search_books(q, page, page_size, db)


@router.get("/content")
async def search_content(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    book_id: Optional[int] = Query(None, description="限定书籍ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await search_service.search_content(q, book_id, page, page_size, db)


@router.get("/suggestions", response_model=List[SearchSuggestion])
async def get_suggestions(
    q: str = Query(..., min_length=1, description="输入关键词"),
    limit: int = Query(10, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    return await search_service.get_suggestions(q, limit, db)


@router.get("/tags")
async def search_by_tag(
    tag: str = Query(..., description="标签名称"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await search_service.search_by_tag(tag, page, page_size, db)
