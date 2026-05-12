import pytest
import pytest_asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.auth_service import AuthService
from app.services.cache_service import CacheService


class TestAuthService:
    @pytest_asyncio.fixture
    async def auth_service(self):
        service = AuthService()
        service._local_attempts = {}
        service._local_until = {}
        service._token_bl = set()
        return service

    @pytest.mark.asyncio
    async def test_record_fail_increases_attempts(self, auth_service):
        mock_cache = AsyncMock(spec=CacheService)
        mock_cache.is_redis_available = False
        
        with patch('app.services.auth_service.cache_service', mock_cache):
            await auth_service._record_fail("testuser")
            assert auth_service._local_attempts.get("testuser") == 1

    @pytest.mark.asyncio
    async def test_record_fail_locks_after_max_attempts(self, auth_service):
        mock_cache = AsyncMock(spec=CacheService)
        mock_cache.is_redis_available = False
        
        with patch('app.services.auth_service.cache_service', mock_cache):
            for _ in range(5):
                await auth_service._record_fail("lockuser")
            is_locked = await auth_service._is_locked("lockuser")
            assert is_locked is True

    @pytest.mark.asyncio
    async def test_clear_attempts_resets_state(self, auth_service):
        mock_cache = AsyncMock(spec=CacheService)
        mock_cache.is_redis_available = False
        
        with patch('app.services.auth_service.cache_service', mock_cache):
            await auth_service._record_fail("testuser")
            assert auth_service._local_attempts.get("testuser") == 1
            await auth_service._clear_attempts("testuser")
            assert "testuser" not in auth_service._local_attempts
            assert "testuser" not in auth_service._local_until

    @pytest.mark.asyncio
    async def test_is_locked_false_when_no_attempts(self, auth_service):
        mock_cache = AsyncMock(spec=CacheService)
        mock_cache.is_redis_available = False
        
        with patch('app.services.auth_service.cache_service', mock_cache):
            is_locked = await auth_service._is_locked("nonexistent")
            assert is_locked is False

    @pytest.mark.asyncio
    async def test_is_locked_false_after_clear(self, auth_service):
        mock_cache = AsyncMock(spec=CacheService)
        mock_cache.is_redis_available = False
        
        with patch('app.services.auth_service.cache_service', mock_cache):
            for _ in range(5):
                await auth_service._record_fail("lockuser")
            await auth_service._clear_attempts("lockuser")
            is_locked = await auth_service._is_locked("lockuser")
            assert is_locked is False

    @pytest.mark.asyncio
    async def test_blacklist_token_adds_to_local_set(self, auth_service):
        mock_cache = AsyncMock(spec=CacheService)
        mock_cache.is_redis_available = False
        
        with patch('app.services.auth_service.cache_service', mock_cache):
            with patch('app.services.auth_service.decode_token', return_value={'exp': time.time() + 3600}):
                test_token = "test_token_123"
                await auth_service.blacklist_token(test_token)
                assert test_token in auth_service._token_bl

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_true_for_blacklisted(self, auth_service):
        mock_cache = AsyncMock(spec=CacheService)
        mock_cache.is_redis_available = False
        
        with patch('app.services.auth_service.cache_service', mock_cache):
            with patch('app.services.auth_service.decode_token', return_value={'exp': time.time() + 3600}):
                test_token = "test_token_123"
                await auth_service.blacklist_token(test_token)
            is_blacklisted = await auth_service.is_token_blacklisted(test_token)
            assert is_blacklisted is True

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_false_for_not_blacklisted(self, auth_service):
        mock_cache = AsyncMock(spec=CacheService)
        mock_cache.is_redis_available = False
        
        with patch('app.services.auth_service.cache_service', mock_cache):
            is_blacklisted = await auth_service.is_token_blacklisted("unknown_token")
            assert is_blacklisted is False

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_false_for_empty_token(self, auth_service):
        is_blacklisted = await auth_service.is_token_blacklisted("")
        assert is_blacklisted is False

    @pytest.mark.asyncio
    async def test_logout_adds_token_to_blacklist(self, auth_service):
        mock_cache = AsyncMock(spec=CacheService)
        mock_cache.is_redis_available = False
        
        with patch('app.services.auth_service.cache_service', mock_cache):
            with patch('app.services.auth_service.decode_token', return_value={'exp': time.time() + 3600}):
                test_token = "logout_token"
                await auth_service.logout(test_token)
                assert test_token in auth_service._token_bl

    @pytest.mark.asyncio
    async def test_blacklist_token_with_redis(self, auth_service):
        mock_cache = AsyncMock(spec=CacheService)
        mock_cache.is_redis_available = True
        mock_cache.setex = AsyncMock(return_value=True)

        with patch('app.services.auth_service.cache_service', mock_cache):
            with patch('app.services.auth_service.decode_token', return_value={'exp': time.time() + 3600}):
                test_token = "redis_token"
                await auth_service.blacklist_token(test_token)
                mock_cache.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_with_redis(self, auth_service):
        mock_cache = AsyncMock(spec=CacheService)
        mock_cache.is_redis_available = True
        mock_cache.get = AsyncMock(return_value="1")

        with patch('app.services.auth_service.cache_service', mock_cache):
            is_blacklisted = await auth_service.is_token_blacklisted("redis_token")
            assert is_blacklisted is True
            mock_cache.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_fail_with_redis(self, auth_service):
        mock_cache = AsyncMock(spec=CacheService)
        mock_cache.is_redis_available = True
        mock_cache.incr = AsyncMock(return_value=1)
        mock_cache.expire = AsyncMock(return_value=True)

        with patch('app.services.auth_service.cache_service', mock_cache):
            await auth_service._record_fail("redis_user")
            mock_cache.incr.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_fail_redis_error_fallback(self, auth_service):
        from redis import RedisError
        mock_cache = AsyncMock(spec=CacheService)
        mock_cache.is_redis_available = True
        mock_cache.incr = AsyncMock(side_effect=RedisError("Redis down"))
        mock_cache.expire = AsyncMock(return_value=True)

        with patch('app.services.auth_service.cache_service', mock_cache):
            await auth_service._record_fail("fallback_user")
            assert auth_service._local_attempts.get("fallback_user") == 1

    @pytest.mark.asyncio
    async def test_refresh_tokens_blacklists_old_token(self, auth_service):
        mock_cache = AsyncMock(spec=CacheService)
        mock_cache.is_redis_available = False
        
        with patch('app.services.auth_service.cache_service', mock_cache):
            with patch('app.services.auth_service.decode_token', return_value={'sub': '1', 'type': 'refresh'}):
                old_refresh = "old_refresh_token"
                await auth_service.refresh_tokens(old_refresh)
                assert old_refresh in auth_service._token_bl