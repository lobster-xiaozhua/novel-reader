import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Favorite, FavoriteFolder, User
from app.schemas.schemas import FavoriteCreate, FavoriteResponse, FavoriteFolderCreate, FavoriteFolderResponse
from app.core.security import get_current_user_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/favorites", tags=["收藏"])


@router.get("", response_model=list[FavoriteResponse])
async def list_favorites(
    folder_id: int = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    query = select(Favorite).where(Favorite.user_id == current_user_id)
    if folder_id is not None:
        query = query.where(Favorite.folder_id == folder_id)
    query = query.order_by(Favorite.created_at.desc())

    result = await db.execute(query)
    favorites = result.scalars().all()
    return [FavoriteResponse.model_validate(f) for f in favorites]


@router.post("", response_model=FavoriteResponse, status_code=status.HTTP_201_CREATED)
async def create_favorite(
    favorite_data: FavoriteCreate,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    favorite = Favorite(
        user_id=current_user_id,
        book_id=favorite_data.book_id,
        folder_id=favorite_data.folder_id,
    )
    db.add(favorite)
    await db.commit()
    await db.refresh(favorite)

    logger.info(f"收藏创建成功: user={current_user_id}, book={favorite_data.book_id}")
    return favorite


@router.delete("/{favorite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_favorite(
    favorite_id: int,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    result = await db.execute(
        select(Favorite).where(
            Favorite.id == favorite_id,
            Favorite.user_id == current_user_id,
        )
    )
    favorite = result.scalar_one_or_none()
    if not favorite:
        raise HTTPException(status_code=404, detail="收藏不存在")

    await db.delete(favorite)
    await db.commit()
    logger.info(f"收藏已删除: {favorite_id}")


@router.get("/folders", response_model=list[FavoriteFolderResponse])
async def list_folders(
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    result = await db.execute(
        select(FavoriteFolder)
        .where(FavoriteFolder.user_id == current_user_id)
        .order_by(FavoriteFolder.sort_order)
    )
    folders = result.scalars().all()
    return [FavoriteFolderResponse.model_validate(f) for f in folders]


@router.post("/folders", response_model=FavoriteFolderResponse, status_code=status.HTTP_201_CREATED)
async def create_folder(
    folder_data: FavoriteFolderCreate,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    folder = FavoriteFolder(
        user_id=current_user_id,
        name=folder_data.name,
        description=folder_data.description,
        color=folder_data.color,
    )
    db.add(folder)
    await db.commit()
    await db.refresh(folder)

    logger.info(f"收藏夹创建成功: {folder.id} - {folder.name}")
    return folder
