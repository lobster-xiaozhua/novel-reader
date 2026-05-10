import logging
from datetime import datetime

from app.core.config import get_settings
from app.services.cache_service import cache_service

logger = logging.getLogger(__name__)
settings = get_settings()


class AuthService:
    LOGIN_ATTEMPT_PREFIX = "auth:login_attempts:"
    TOKEN_BLACKLIST_PREFIX = "auth:blacklist:"

    async def check_login_attempts(self, username: str) -> bool:
        key = f"{self.LOGIN_ATTEMPT_PREFIX}{username}"
        count = await cache_service.get(key)
        if count is None:
            return True
        if int(count) >= settings.MAX_LOGIN_ATTEMPTS:
            ttl = await cache_service.ttl(key)
            logger.warning(f"用户 {username} 登录尝试次数超限，剩余锁定 {ttl} 秒")
            return False
        return True

    async def record_failed_login(self, username: str):
        key = f"{self.LOGIN_ATTEMPT_PREFIX}{username}"
        count = await cache_service.incr(key)
        if count == 1:
            await cache_service.expire(key, settings.LOGIN_LOCKOUT_MINUTES * 60)
        logger.info(f"用户 {username} 登录失败，第 {count} 次尝试")

    async def reset_login_attempts(self, username: str):
        key = f"{self.LOGIN_ATTEMPT_PREFIX}{username}"
        await cache_service.delete(key)

    async def get_remaining_attempts(self, username: str) -> int:
        key = f"{self.LOGIN_ATTEMPT_PREFIX}{username}"
        count = await cache_service.get(key)
        if count is None:
            return settings.MAX_LOGIN_ATTEMPTS
        return max(0, settings.MAX_LOGIN_ATTEMPTS - int(count))

    async def get_lockout_remaining(self, username: str) -> int:
        key = f"{self.LOGIN_ATTEMPT_PREFIX}{username}"
        return await cache_service.ttl(key)

    async def blacklist_token(self, token: str, expire_seconds: int = None):
        key = f"{self.TOKEN_BLACKLIST_PREFIX}{token}"
        ex = expire_seconds or settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        await cache_service.set(key, "1", expire=ex)
        logger.info(f"Token 已加入黑名单")

    async def is_token_blacklisted(self, token: str) -> bool:
        key = f"{self.TOKEN_BLACKLIST_PREFIX}{token}"
        result = await cache_service.get(key)
        return result is not None


auth_service = AuthService()
