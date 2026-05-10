import json
import logging
from typing import Any, Optional

import redis.asyncio as redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CacheService:
    def __init__(self):
        self._client: Optional[redis.Redis] = None

    async def connect(self):
        try:
            self._client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                max_connections=settings.REDIS_POOL_SIZE,
                health_check_interval=30,
            )
            await self._client.ping()
            logger.info("Redis 连接成功")
        except Exception as e:
            logger.warning(f"Redis 连接失败，降级为无缓存模式: {e}")
            self._client = None

    async def disconnect(self):
        if self._client:
            await self._client.close()

    @property
    def available(self) -> bool:
        return self._client is not None

    async def get(self, key: str) -> Optional[str]:
        if not self.available:
            return None
        try:
            return await self._client.get(key)
        except Exception as e:
            logger.error(f"Redis GET 失败 key={key}: {e}")
            return None

    async def set(self, key: str, value: str, expire: int = None) -> bool:
        if not self.available:
            return False
        try:
            ex = expire or settings.CACHE_EXPIRE_MINUTES * 60
            await self._client.set(key, value, ex=ex)
            return True
        except Exception as e:
            logger.error(f"Redis SET 失败 key={key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        if not self.available:
            return False
        try:
            await self._client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis DELETE 失败 key={key}: {e}")
            return False

    async def get_json(self, key: str) -> Optional[Any]:
        raw = await self.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None

    async def set_json(self, key: str, value: Any, expire: int = None) -> bool:
        try:
            return await self.set(key, json.dumps(value), expire)
        except (TypeError, ValueError):
            return False

    async def incr(self, key: str) -> int:
        if not self.available:
            return 1
        try:
            return await self._client.incr(key)
        except Exception as e:
            logger.error(f"Redis INCR 失败 key={key}: {e}")
            return 1

    async def expire(self, key: str, seconds: int) -> bool:
        if not self.available:
            return False
        try:
            await self._client.expire(key, seconds)
            return True
        except Exception as e:
            logger.error(f"Redis EXPIRE 失败 key={key}: {e}")
            return False

    async def ttl(self, key: str) -> int:
        if not self.available:
            return 0
        try:
            return await self._client.ttl(key)
        except Exception as e:
            logger.error(f"Redis TTL 失败 key={key}: {e}")
            return 0


cache_service = CacheService()
