import asyncio
import json
import time
from pathlib import Path
from typing import Dict, Set

from redis import RedisError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .cache_service import cache_service
from app.database import AsyncSessionLocal
from app.models import User
from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

settings = get_settings()

_BLACKLIST_FILE = Path(settings.DATA_DIR) / "token_blacklist.json"


class AuthService:
    def __init__(self):
        self._local_attempts: Dict[str, int] = {}
        self._local_until: Dict[str, float] = {}
        self._token_blacklist: Set[str] = set()
        self._local_lock = asyncio.Lock()
        self._load_blacklist()

    def _load_blacklist(self):
        if _BLACKLIST_FILE.exists():
            try:
                with open(_BLACKLIST_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._token_blacklist = set(data.get("tokens", []))
            except Exception:
                self._token_blacklist = set()

    def _save_blacklist(self):
        try:
            _BLACKLIST_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(_BLACKLIST_FILE, "w", encoding="utf-8") as f:
                json.dump({"tokens": list(self._token_blacklist)}, f)
        except Exception:
            pass

    async def register_user(self, username: str, password: str, email: str = None) -> User:
        async with AsyncSessionLocal() as db:
            existing = (await db.execute(select(User).where(User.username == username))).scalar_one_or_none()
            if existing:
                raise ValueError("用户名已存在")

            hashed = hash_password(password)
            user = User(username=username, password_hash=hashed)
            db.add(user)
            await db.commit()
            await db.refresh(user)
            return user

    async def authenticate_user(self, username: str, password: str) -> tuple[User, str, str]:
        async with AsyncSessionLocal() as db:
            if await self._is_locked(username):
                raise ValueError(f"登录尝试过于频繁，请 {settings.LOGIN_RATE_LIMIT_WINDOW} 秒后再试")

            result = await db.execute(select(User).where(User.username == username))
            user = result.scalar_one_or_none()

            if not user or not verify_password(password, user.password_hash):
                await self._record_failed_login(username)
                raise ValueError("用户名或密码错误")

            await self._clear_attempts(username)
            access = create_access_token({"sub": str(user.id)})
            refresh = create_refresh_token({"sub": str(user.id)})
            return user, access, refresh

    async def refresh_tokens(self, refresh_token: str) -> tuple[str, str]:
        if await self.is_token_blacklisted(refresh_token):
            raise ValueError("刷新令牌已失效")

        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise ValueError("无效的刷新令牌")

        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("无效的刷新令牌")

        access = create_access_token({"sub": user_id})
        refresh = create_refresh_token({"sub": user_id})
        await self.blacklist_token(refresh_token)
        return access, refresh

    async def logout(self, token: str):
        await self.blacklist_token(token)

    async def blacklist_token(self, token: str):
        payload = decode_token(token)
        if not payload:
            return

        exp = payload.get("exp")
        ttl = max(0, exp - int(time.time())) if exp else 3600 * 24 * 7

        try:
            if cache_service.available:
                await cache_service.set(f"blacklist:{token}", "1", expire=ttl)
            else:
                self._token_blacklist.add(token)
                self._save_blacklist()
        except RedisError:
            self._token_blacklist.add(token)
            self._save_blacklist()

    async def is_token_blacklisted(self, token: str) -> bool:
        if not token:
            return False

        try:
            if cache_service.available:
                val = await cache_service.get(f"blacklist:{token}")
                return val is not None
            else:
                return token in self._token_blacklist
        except RedisError:
            return token in self._token_blacklist

    async def _is_locked(self, username: str) -> bool:
        async with self._local_lock:
            now = time.time()
            try:
                if cache_service.available:
                    key = f"login_lock:{username}"
                    return bool(await cache_service.get(key))
                else:
                    until = self._local_until.get(username, 0)
                    return now < until
            except RedisError:
                until = self._local_until.get(username, 0)
                return now < until

    async def _record_failed_login(self, username: str):
        async with self._local_lock:
            key = f"login_attempts:{username}"
            now = time.time()
            try:
                if cache_service.available:
                    count = await cache_service.incr(key)
                    if count == 1:
                        await cache_service.expire(key, settings.LOGIN_RATE_LIMIT_WINDOW)

                    if count >= settings.LOGIN_RATE_LIMIT_MAX:
                        await cache_service.set(
                            f"login_lock:{username}",
                            "1",
                            expire=settings.LOGIN_RATE_LIMIT_WINDOW,
                        )
                else:
                    attempts = self._local_attempts.get(username, 0) + 1
                    self._local_attempts[username] = attempts

                    if attempts >= settings.LOGIN_RATE_LIMIT_MAX:
                        self._local_until[username] = now + settings.LOGIN_RATE_LIMIT_WINDOW
                        self._local_attempts.pop(username, None)
            except RedisError:
                attempts = self._local_attempts.get(username, 0) + 1
                self._local_attempts[username] = attempts
                if attempts >= settings.LOGIN_RATE_LIMIT_MAX:
                    self._local_until[username] = now + settings.LOGIN_RATE_LIMIT_WINDOW
                    self._local_attempts.pop(username, None)

    async def _clear_attempts(self, username: str):
        async with self._local_lock:
            try:
                if cache_service.available:
                    await cache_service.delete(f"login_attempts:{username}")
                    await cache_service.delete(f"login_lock:{username}")
                else:
                    self._local_attempts.pop(username, None)
                    self._local_until.pop(username, None)
            except RedisError:
                self._local_attempts.pop(username, None)
                self._local_until.pop(username, None)


auth_service = AuthService()
