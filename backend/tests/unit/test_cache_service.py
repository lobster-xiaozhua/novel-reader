import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.cache_service import CacheService


class TestCacheServiceComplete:
    @pytest.fixture
    def cache_service(self):
        return CacheService()

    @pytest.fixture
    def mock_redis_client(self, cache_service):
        cache_service._client = AsyncMock()
        return cache_service._client

    @pytest.mark.asyncio
    async def test_available_property_true(self, cache_service, mock_redis_client):
        assert cache_service.available is True

    @pytest.mark.asyncio
    async def test_available_property_false(self, cache_service):
        cache_service._client = None
        assert cache_service.available is False

    @pytest.mark.asyncio
    async def test_get_returns_none_when_unavailable(self, cache_service):
        cache_service._client = None
        result = await cache_service.get("any_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_handles_redis_error(self, cache_service, mock_redis_client):
        mock_redis_client.get = AsyncMock(side_effect=Exception("Redis error"))
        result = await cache_service.get("error_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_returns_false_when_unavailable(self, cache_service):
        cache_service._client = None
        result = await cache_service.set("key", "value")
        assert result is False

    @pytest.mark.asyncio
    async def test_set_with_custom_expire(self, cache_service, mock_redis_client):
        mock_redis_client.set = AsyncMock(return_value=True)
        with patch('app.services.cache_service.settings') as mock_settings:
            mock_settings.CACHE_EXPIRE_MINUTES = 10
            result = await cache_service.set("key", "value", expire=600)
            assert result is True
            mock_redis_client.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_uses_default_expire(self, cache_service, mock_redis_client):
        mock_redis_client.set = AsyncMock(return_value=True)
        with patch('app.services.cache_service.settings') as mock_settings:
            mock_settings.CACHE_EXPIRE_MINUTES = 10
            result = await cache_service.set("key", "value")
            assert result is True
            args = mock_redis_client.set.call_args
            assert args[0][0] == "key"
            assert args[0][1] == "value"
            assert args[1]["ex"] == 600

    @pytest.mark.asyncio
    async def test_set_handles_redis_error(self, cache_service, mock_redis_client):
        mock_redis_client.set = AsyncMock(side_effect=Exception("Redis error"))
        result = await cache_service.set("key", "value")
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_returns_false_when_unavailable(self, cache_service):
        cache_service._client = None
        result = await cache_service.delete("any_key")
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_success(self, cache_service, mock_redis_client):
        mock_redis_client.delete = AsyncMock(return_value=1)
        result = await cache_service.delete("key")
        assert result is True
        mock_redis_client.delete.assert_called_with("key")

    @pytest.mark.asyncio
    async def test_delete_handles_redis_error(self, cache_service, mock_redis_client):
        mock_redis_client.delete = AsyncMock(side_effect=Exception("Redis error"))
        result = await cache_service.delete("error_key")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_json_returns_none_when_unavailable(self, cache_service):
        cache_service._client = None
        result = await cache_service.get_json("key")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_json_success(self, cache_service, mock_redis_client):
        mock_redis_client.get = AsyncMock(return_value='{"count": 42}')
        result = await cache_service.get_json("key")
        assert result == {"count": 42}

    @pytest.mark.asyncio
    async def test_get_json_handles_invalid_json(self, cache_service, mock_redis_client):
        mock_redis_client.get = AsyncMock(return_value="not valid json {")
        result = await cache_service.get_json("key")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_json_success(self, cache_service, mock_redis_client):
        mock_redis_client.set = AsyncMock(return_value=True)
        with patch('app.services.cache_service.settings') as mock_settings:
            mock_settings.CACHE_EXPIRE_MINUTES = 10
            result = await cache_service.set_json("key", {"data": "value"})
            assert result is True

    @pytest.mark.asyncio
    async def test_set_json_handles_non_serializable(self, cache_service):
        class NonSerializable:
            pass
        result = await cache_service.set_json("key", NonSerializable())
        assert result is False

    @pytest.mark.asyncio
    async def test_incr_returns_1_when_unavailable(self, cache_service):
        cache_service._client = None
        result = await cache_service.incr("counter")
        assert result == 1

    @pytest.mark.asyncio
    async def test_incr_success(self, cache_service, mock_redis_client):
        mock_redis_client.incr = AsyncMock(return_value=5)
        result = await cache_service.incr("counter")
        assert result == 5
        mock_redis_client.incr.assert_called_with("counter")

    @pytest.mark.asyncio
    async def test_incr_handles_redis_error(self, cache_service, mock_redis_client):
        mock_redis_client.incr = AsyncMock(side_effect=Exception("Redis error"))
        result = await cache_service.incr("error_counter")
        assert result == 1

    @pytest.mark.asyncio
    async def test_expire_returns_false_when_unavailable(self, cache_service):
        cache_service._client = None
        result = await cache_service.expire("key", 300)
        assert result is False

    @pytest.mark.asyncio
    async def test_expire_success(self, cache_service, mock_redis_client):
        mock_redis_client.expire = AsyncMock(return_value=True)
        result = await cache_service.expire("key", 300)
        assert result is True
        mock_redis_client.expire.assert_called_with("key", 300)

    @pytest.mark.asyncio
    async def test_expire_handles_redis_error(self, cache_service, mock_redis_client):
        mock_redis_client.expire = AsyncMock(side_effect=Exception("Redis error"))
        result = await cache_service.expire("error_key", 300)
        assert result is False

    @pytest.mark.asyncio
    async def test_ttl_returns_0_when_unavailable(self, cache_service):
        cache_service._client = None
        result = await cache_service.ttl("key")
        assert result == 0

    @pytest.mark.asyncio
    async def test_ttl_success(self, cache_service, mock_redis_client):
        mock_redis_client.ttl = AsyncMock(return_value=120)
        result = await cache_service.ttl("key")
        assert result == 120
        mock_redis_client.ttl.assert_called_with("key")

    @pytest.mark.asyncio
    async def test_ttl_handles_redis_error(self, cache_service, mock_redis_client):
        mock_redis_client.ttl = AsyncMock(side_effect=Exception("Redis error"))
        result = await cache_service.ttl("error_key")
        assert result == 0

    @pytest.mark.asyncio
    async def test_disconnect_closes_client(self, cache_service, mock_redis_client):
        mock_redis_client.close = AsyncMock()
        await cache_service.disconnect()
        assert cache_service._client is None
