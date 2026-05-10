"""
收藏相关API路由
提供异步收藏、取消收藏、收藏夹管理等功能
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional

from app.database import get_db
from app.models import Favorite, FavoriteFolder
from app.core.security import get_current_user_id
from app.schemas.schemas import (
    FavoriteCreate, FavoriteResponse, FavoriteFolderCreate, FavoriteFolderResponse
)

router = APIRouter(prefix="/favorites", tags=["收藏"])


@router.get("", response_model=List[FavoriteResponse])
async def get_favorites(
    folder_id: Optional[int] = None,
    current_user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    query = select(Favorite).where(Favorite.user_id == current_user_id)
    
    if folder_id:
        query = query.where(Favorite.folder_id == folder_id)
    
    query = query.order_by(Favorite.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/async", response_model=FavoriteResponse)
async def add_favorite_async(
    data: FavoriteCreate,
    background_tasks: BackgroundTasks,
    current_user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Favorite).where(
            and_(Favorite.user_id == current_user_id, Favorite.book_id == data.book_id)
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="已经收藏过该书籍")
    
    favorite = Favorite(
        user_id=current_user_id,
        book_id=data.book_id,
        folder_id=data.folder_id,
        is_synced=False
    )
    db.add(favorite)
    await db.commit()
    await db.refresh(favorite)
    
    background_tasks.add_task(sync_favorite, favorite.id)
    
    return favorite


@router.delete("/{book_id}/async")
async def remove_favorite_async(
    book_id: int,
    background_tasks: BackgroundTasks,
    current_user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Favorite).where(
            and_(Favorite.user_id == current_user_id, Favorite.book_id == book_id)
        )
    )
    favorite = result.scalar_one_or_none()
    
    if not favorite:
        raise HTTPException(status_code=404, detail="未收藏该书籍")
    
    favorite.is_synced = False
    await db.commit()
    
    background_tasks.add_task(remove_favorite, favorite.id)
    
    return {"success": True}


@router.get("/folders", response_model=List[FavoriteFolderResponse])
async def get_favorite_folders(
    current_user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(FavoriteFolder)
        .where(FavoriteFolder.user_id == current_user_id)
        .order_by(FavoriteFolder.sort_order)
    )
    return result.scalars().all()


@router.post("/folders", response_model=FavoriteFolderResponse)
async def create_folder(
    data: FavoriteFolderCreate,
    current_user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    folder = FavoriteFolder(
        user_id=current_user_id,
        name=data.name,
        description=data.description,
        color=data.color
    )
    db.add(folder)
    await db.commit()
    await db.refresh(folder)
    return folder


# 后台任务
async def sync_favorite(favorite_id: int):
    pass


async def remove_favorite(favorite_id: int):
    pass
