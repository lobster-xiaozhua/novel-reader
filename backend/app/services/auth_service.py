import logging
import time
from typing import Optional

from app.core.config import get_settings
from app.services.cache_service import cache_service

logger = logging.getLogger(__name__)
settings = get_settings()


class AuthService:
    def __init__(self):
        self.max_attempts = settings.MAX_LOGIN_ATTEMPTS
        self.lockout_minutes = settings.LOGIN_LOCKOUT_MINUTES
        self._local_attempts: dict = {}
        self._local_lockout: dict = {}

    def _login_attempts_key(self, username: str) -> str:
        return f"auth:login_attempts:{username}"

    def _lockout_key(self, username: str) -> str:
        return f"auth:lockout:{username}"

    def _token_blacklist_prefix(self) -> str:
        return "auth:blacklist:"

    def _is_locally_locked_out(self, username: str) -> bool:
        if username in self._local_lockout:
            lockout_until = self._local_lockout[username]
            if time.time() < lockout_until:
                return True
            del self._local_lockout[username]
            self._local_attempts.pop(username, None)
        return False

    async def check_login_attempts(self, username: str) -> bool:
        if cache_service.available:
            lockout_key = self._lockout_key(username)
            lockout_remaining = await cache_service.ttl(lockout_key)
            if lockout_remaining > 0:
                return False
            return True

        return not self._is_locally_locked_out(username)

    async def get_lockout_remaining(self, username: str) -> int:
        if cache_service.available:
            lockout_key = self._lockout_key(username)
            ttl = await cache_service.ttl(lockout_key)
            return max(0, ttl)

        if username in self._local_lockout:
            remaining = int(self._local_lockout[username] - time.time())
            return max(0, remaining)
        return 0

    async def record_failed_login(self, username: str) -> None:
        if cache_service.available:
            attempts_key = self._login_attempts_key(username)
            lockout_key = self._lockout_key(username)

            current_attempts = await cache_service.incr(attempts_key)

            if current_attempts == 1:
                await cache_service.expire(attempts_key, self.lockout_minutes * 60)

            if current_attempts >= self.max_attempts:
                await cache_service.set(
                    lockout_key,
                    "1",
                    expire=self.lockout_minutes * 60
                )
                logger.warning(f"用户 {username} 登录尝试次数超限，已锁定 {self.lockout_minutes} 分钟")
        else:
            attempts = self._local_attempts.get(username, 0) + 1
            self._local_attempts[username] = attempts
            if attempts >= self.max_attempts:
                self._local_lockout[username] = time.time() + self.lockout_minutes * 60
                logger.warning(f"用户 {username} 登录尝试次数超限（本地锁定），已锁定 {self.lockout_minutes} 分钟")

    async def get_remaining_attempts(self, username: str) -> int:
        if cache_service.available:
            attempts_key = self._login_attempts_key(username)
            raw = await cache_service.get(attempts_key)
            if raw is None:
                return self.max_attempts
            try:
                attempts = int(raw)
                return max(0, self.max_attempts - attempts)
            except (ValueError, TypeError):
                return self.max_attempts

        attempts = self._local_attempts.get(username, 0)
        return max(0, self.max_attempts - attempts)

    async def reset_login_attempts(self, username: str) -> None:
        if cache_service.available:
            attempts_key = self._login_attempts_key(username)
            lockout_key = self._lockout_key(username)
            await cache_service.delete(attempts_key)
            await cache_service.delete(lockout_key)

        self._local_attempts.pop(username, None)
        self._local_lockout.pop(username, None)

    async def blacklist_token(self, token_id: str) -> None:
        blacklist_key = f"{self._token_blacklist_prefix()}{token_id}"
        await cache_service.set(
            blacklist_key,
            "1",
            expire=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

    async def is_token_blacklisted(self, token_id: str) -> bool:
        blacklist_key = f"{self._token_blacklist_prefix()}{token_id}"
        raw = await cache_service.get(blacklist_key)
        return raw is not None


auth_service = AuthService()
