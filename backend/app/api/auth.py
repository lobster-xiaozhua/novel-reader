import logging

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.database import get_db_session
from app.models import User
from app.core.security import (
    hash_password, verify_password, validate_password_strength,
    create_access_token, create_refresh_token, decode_token, get_current_user_id, get_current_token
)
from app.schemas.schemas import UserCreate, UserResponse, TokenResponse
from app.services.auth_service import auth_service
from app.core.exceptions import ValidationError, AuthenticationError, NotFoundError, RateLimitError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise ValidationError("用户名已存在")

    is_valid, message = validate_password_strength(user_data.password)
    if not is_valid:
        raise ValidationError(message)

    user = User(
        username=user_data.username,
        password_hash=hash_password(user_data.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info(f"用户注册成功: {user.username}")
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db_session),
):
    if not await auth_service.check_login_attempts(form_data.username):
        remaining = await auth_service.get_lockout_remaining(form_data.username)
        raise RateLimitError(f"登录尝试次数超限，请 {remaining} 秒后再试")

    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.password_hash):
        await auth_service.record_failed_login(form_data.username)
        remaining = await auth_service.get_remaining_attempts(form_data.username)
        raise AuthenticationError(f"用户名或密码错误，剩余尝试次数: {remaining}")

    if not user.is_active:
        raise ValidationError("用户已被禁用")

    await auth_service.reset_login_attempts(form_data.username)

    user.last_login = datetime.utcnow()
    await db.commit()

    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    logger.info(f"用户登录成功: {user.username}")
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 60 * 24,
    }


@router.post("/logout")
async def logout(
    current_user_id: int = Depends(get_current_user_id),
    token: str = Depends(get_current_token),
):
    await auth_service.blacklist_token(token)
    logger.info(f"用户 {current_user_id} 登出")
    return {"message": "登出成功"}


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
):
    result = await db.execute(select(User).where(User.id == current_user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError("用户", str(current_user_id))
    return user
