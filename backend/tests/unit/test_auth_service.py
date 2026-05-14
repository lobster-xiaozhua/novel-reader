import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.core.security import create_access_token, create_refresh_token


class TestAuthServiceLogic:
    @pytest.fixture
    def mock_auth_service(self):
        from app.services.auth_service import AuthService
        service = AuthService()
        service._local_attempts = {}
        service._local_until = {}
        service._token_bl = set()
        service._local_lock = asyncio.Lock()
        return service

    @pytest.mark.asyncio
    async def test_record_fail_increments_attempts(self, mock_auth_service):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.is_redis_available = False
            with patch('app.services.auth_service.settings') as mock_settings:
                mock_settings.LOGIN_RATE_LIMIT_MAX = 5
                mock_settings.LOGIN_RATE_LIMIT_WINDOW = 300
                await mock_auth_service._record_fail("testuser")
                assert mock_auth_service._local_attempts.get("testuser") == 1

    @pytest.mark.asyncio
    async def test_record_fail_locks_after_max_attempts(self, mock_auth_service):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.is_redis_available = False
            with patch('app.services.auth_service.settings') as mock_settings:
                mock_settings.LOGIN_RATE_LIMIT_MAX = 3
                mock_settings.LOGIN_RATE_LIMIT_WINDOW = 300
                for _ in range(3):
                    await mock_auth_service._record_fail("lockeduser")
                assert "lockeduser" in mock_auth_service._local_until

    @pytest.mark.asyncio
    async def test_is_locked_returns_true_when_locked(self, mock_auth_service):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.is_redis_available = False
            mock_auth_service._local_until["lockeduser"] = float('inf')
            result = await mock_auth_service._is_locked("lockeduser")
            assert result is True

    @pytest.mark.asyncio
    async def test_is_locked_returns_false_when_not_locked(self, mock_auth_service):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.is_redis_available = False
            result = await mock_auth_service._is_locked("normaluser")
            assert result is False

    @pytest.mark.asyncio
    async def test_clear_attempts_removes_user_data(self, mock_auth_service):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.is_redis_available = False
            mock_auth_service._local_attempts["testuser"] = 5
            mock_auth_service._local_until["testuser"] = 100.0
            await mock_auth_service._clear_attempts("testuser")
            assert "testuser" not in mock_auth_service._local_attempts
            assert "testuser" not in mock_auth_service._local_until

    @pytest.mark.asyncio
    async def test_blacklist_token_adds_to_local_blacklist(self, mock_auth_service):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.is_redis_available = False
            token = create_access_token({"sub": "123"})
            await mock_auth_service.blacklist_token(token)
            assert token in mock_auth_service._token_bl

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_with_local_blacklist(self, mock_auth_service):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.is_redis_available = False
            token = create_access_token({"sub": "123"})
            mock_auth_service._token_bl.add(token)
            result = await mock_auth_service.is_token_blacklisted(token)
            assert result is True

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_empty_token(self, mock_auth_service):
        result = await mock_auth_service.is_token_blacklisted("")
        assert result is False

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_not_in_blacklist(self, mock_auth_service):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.is_redis_available = False
            token = create_access_token({"sub": "456"})
            result = await mock_auth_service.is_token_blacklisted(token)
            assert result is False

    @pytest.mark.asyncio
    async def test_blacklist_token_handles_invalid_token(self, mock_auth_service):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.is_redis_available = False
            await mock_auth_service.blacklist_token("invalid.token")
            await mock_auth_service.blacklist_token(None)

    @pytest.mark.asyncio
    async def test_refresh_tokens_rejects_blacklisted_token(self, mock_auth_service):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.is_redis_available = False
            refresh_token = create_refresh_token({"sub": "123"})
            mock_auth_service._token_bl.add(refresh_token)
            with pytest.raises(ValueError, match="Token invalid"):
                await mock_auth_service.refresh_tokens(refresh_token)

    @pytest.mark.asyncio
    async def test_refresh_tokens_validates_token_type(self, mock_auth_service):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.is_redis_available = False
            access_token = create_access_token({"sub": "123"})
            with pytest.raises(ValueError, match="Invalid token"):
                await mock_auth_service.refresh_tokens(access_token)

    @pytest.mark.asyncio
    async def test_logout_blacklists_token(self, mock_auth_service):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.is_redis_available = False
            token = create_access_token({"sub": "789"})
            await mock_auth_service.logout(token)
            assert token in mock_auth_service._token_bl
