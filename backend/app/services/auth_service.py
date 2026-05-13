import asyncio
import time
from typing import Dict, Set

from redis import RedisError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.cache_service import cache_service
from app.database import AsyncSessionLocal
from app.models import User
from app.core.config import get_settings
from app.core.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password

settings = get_settings()

class AuthService:
    def __init__(self):
        self._local_attempts: Dict[str, int] = {}
        self._local_until: Dict[str, float] = {}
        self._token_bl: Set[str] = set()
        self._local_lock = asyncio.Lock()

    async def register_user(self, username: str, password: str, email: str = None):
        async with AsyncSessionLocal() as db:
            existing = (await db.execute(select(User).where(User.username == username))).scalar_one_or_none()
            if existing:
                raise ValueError("Username taken")
            user = User(username=username, email=email, hashed_password=hash_password(password))
            db.add(user)
            await db.commit()
            await db.refresh(user)
            return user

    async def authenticate_user(self, username, password):
        async with AsyncSessionLocal() as db:
            if await self._is_locked(username):
                raise ValueError(f"Login locked for {settings.LOGIN_RATE_LIMIT_WINDOW}s")
            result = await db.execute(select(User).where(User.username == username))
            user = result.scalar_one_or_none()
            if not user or not verify_password(password, user.hashed_password):
                await self._record_fail(username)
                raise ValueError("Bad credentials")
            await self._clear_attempts(username)
            access = create_access_token({'sub': str(user.id)})
            refresh = create_refresh_token({'sub': str(user.id)})
            return user, access, refresh

    async def refresh_tokens(self, refresh):
        if await self.is_token_blacklisted(refresh):
            raise ValueError("Token invalid")
        payload = decode_token(refresh)
        if not payload or payload.get('type') != 'refresh':
            raise ValueError("Invalid token")
        sub = payload.get('sub')
        if not sub:
            raise ValueError("Invalid token")
        new_access = create_access_token({'sub': sub})
        new_refresh = create_refresh_token({'sub': sub})
        await self.blacklist_token(refresh)
        return new_access, new_refresh

    async def logout(self, token):
        await self.blacklist_token(token)

    async def blacklist_token(self, token):
        payload = decode_token(token)
        if not payload:
            return
        ttl = max(0, (payload.get('exp', time.time() + 86400 * 7) - int(time.time())))
        try:
            if cache_service.is_redis_available:
                await cache_service.setex(f"blacklist:{token}", ttl, "1")
            else:
                self._token_bl.add(token)
        except RedisError:
            self._token_bl.add(token)

    async def is_token_blacklisted(self, token):
        if not token:
            return False
        try:
            if cache_service.is_redis_available:
                return bool(await cache_service.get(f"blacklist:{token}"))
            else:
                return token in self._token_bl
        except RedisError:
            return token in self._token_bl

    async def _is_locked(self, username):
        async with self._local_lock:
            now = time.time()
            try:
                if cache_service.is_redis_available:
                    return bool(await cache_service.get(f"login_lock:{username}"))
                else:
                    return now < self._local_until.get(username, 0)
            except RedisError:
                return now < self._local_until.get(username, 0)

    async def _record_fail(self, username):
        async with self._local_lock:
            key_att = f"login_attempts:{username}"
            key_lock = f"login_lock:{username}"
            now = time.time()
            try:
                if cache_service.is_redis_available:
                    count = await cache_service.incr(key_att)
                    if count == 1:
                        await cache_service.expire(key_att, settings.LOGIN_RATE_LIMIT_WINDOW)
                    if count >= settings.LOGIN_RATE_LIMIT_MAX:
                        await cache_service.setex(key_lock, settings.LOGIN_RATE_LIMIT_WINDOW, "1")
                else:
                    att = self._local_attempts.get(username, 0) + 1
                    self._local_attempts[username] = att
                    if att >= settings.LOGIN_RATE_LIMIT_MAX:
                        self._local_until[username] = now + settings.LOGIN_RATE_LIMIT_WINDOW
                        self._local_attempts.pop(username, None)
            except RedisError:
                att = self._local_attempts.get(username, 0) + 1
                self._local_attempts[username] = att
                if att >= settings.LOGIN_RATE_LIMIT_MAX:
                    self._local_until[username] = now + settings.LOGIN_RATE_LIMIT_WINDOW
                    self._local_attempts.pop(username, None)

    async def _clear_attempts(self, username):
        async with self._local_lock:
            try:
                if cache_service.is_redis_available:
                    await cache_service.delete(f"login_attempts:{username}")
                    await cache_service.delete(f"login_lock:{username}")
                else:
                    self._local_attempts.pop(username, None)
                    self._local_until.pop(username, None)
            except RedisError:
                self._local_attempts.pop(username, None)
                self._local_until.pop(username, None)

    async def check_login_attempts(self, username: str) -> bool:
        return not await self._is_locked(username)

    async def get_lockout_remaining(self, username: str) -> int:
        async with self._local_lock:
            try:
                if cache_service.is_redis_available:
                    ttl = await cache_service.ttl(f"login_lock:{username}")
                    return max(0, ttl)
                else:
                    remaining = self._local_until.get(username, 0) - time.time()
                    return max(0, int(remaining))
            except RedisError:
                remaining = self._local_until.get(username, 0) - time.time()
                return max(0, int(remaining))

    async def record_failed_login(self, username: str):
        await self._record_fail(username)

    async def get_remaining_attempts(self, username: str) -> int:
        async with self._local_lock:
            try:
                if cache_service.is_redis_available:
                    count = await cache_service.get(f"login_attempts:{username}")
                    if count is None:
                        return settings.LOGIN_RATE_LIMIT_MAX
                    return max(0, settings.LOGIN_RATE_LIMIT_MAX - int(count))
                else:
                    attempts = self._local_attempts.get(username, 0)
                    return max(0, settings.LOGIN_RATE_LIMIT_MAX - attempts)
            except RedisError:
                attempts = self._local_attempts.get(username, 0)
                return max(0, settings.LOGIN_RATE_LIMIT_MAX - attempts)

    async def reset_login_attempts(self, username: str):
        await self._clear_attempts(username)

auth_service = AuthService()