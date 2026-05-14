import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from app.services.cache_service import CacheService


class TestCacheService:
    @pytest_asyncio.fixture
    async def cache_service(self):
        service = CacheService()
        service._client = AsyncMock()
        return service

    @pytest.mark.asyncio
    async def test_get_success(self, cache_service):
        cache_service._client.get = AsyncMock(return_value="test_value")
        result = await cache_service.get("test_key")
        assert result == "test_value"

    @pytest.mark.asyncio
    async def test_get_not_available(self, cache_service):
        cache_service._client = None
        result = await cache_service.get("test_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_success(self, cache_service):
        cache_service._client.set = AsyncMock(return_value=True)
        result = await cache_service.set("key", "value", expire=300)
        assert result is True

    @pytest.mark.asyncio
    async def test_get_json(self, cache_service):
        cache_service._client.get = AsyncMock(return_value='{"name": "test"}')
        result = await cache_service.get_json("key")
        assert result == {"name": "test"}

    @pytest.mark.asyncio
    async def test_get_json_invalid(self, cache_service):
        cache_service._client.get = AsyncMock(return_value="invalid json")
        result = await cache_service.get_json("key")
        assert result is None
