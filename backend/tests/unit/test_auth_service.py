import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.auth_service import AuthService, auth_service
from app.core.config import get_settings

settings = get_settings()


class TestAuthServiceLoginAttempts:
    @pytest_asyncio.fixture
    async def auth_service_instance(self):
        return AuthService()

    @pytest.mark.asyncio
    async def test_check_login_attempts_no_history(self, auth_service_instance):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.get = AsyncMock(return_value=None)
            result = await auth_service_instance.check_login_attempts("testuser")
            assert result is True

    @pytest.mark.asyncio
    async def test_check_login_attempts_under_limit(self, auth_service_instance):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.get = AsyncMock(return_value="3")
            mock_cache.ttl = AsyncMock(return_value=600)
            result = await auth_service_instance.check_login_attempts("testuser")
            assert result is True

    @pytest.mark.asyncio
    async def test_check_login_attempts_at_limit(self, auth_service_instance):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.get = AsyncMock(return_value="5")
            mock_cache.ttl = AsyncMock(return_value=300)
            result = await auth_service_instance.check_login_attempts("testuser")
            assert result is False

    @pytest.mark.asyncio
    async def test_check_login_attempts_exceeds_limit(self, auth_service_instance):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.get = AsyncMock(return_value="10")
            mock_cache.ttl = AsyncMock(return_value=600)
            result = await auth_service_instance.check_login_attempts("testuser")
            assert result is False

    @pytest.mark.asyncio
    async def test_record_failed_login_first_attempt(self, auth_service_instance):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.incr = AsyncMock(return_value=1)
            mock_cache.expire = AsyncMock()
            await auth_service_instance.record_failed_login("testuser")
            mock_cache.incr.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_failed_login_sets_expiry_on_first(self, auth_service_instance):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.incr = AsyncMock(return_value=1)
            mock_cache.expire = AsyncMock()
            await auth_service_instance.record_failed_login("testuser")
            mock_cache.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_failed_login_no_expiry_on_subsequent(self, auth_service_instance):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.incr = AsyncMock(return_value=3)
            mock_cache.expire = AsyncMock()
            await auth_service_instance.record_failed_login("testuser")
            mock_cache.expire.assert_not_called()

    @pytest.mark.asyncio
    async def test_reset_login_attempts(self, auth_service_instance):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.delete = AsyncMock()
            await auth_service_instance.reset_login_attempts("testuser")
            mock_cache.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_remaining_attempts_no_history(self, auth_service_instance):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.get = AsyncMock(return_value=None)
            result = await auth_service_instance.get_remaining_attempts("testuser")
            assert result == settings.MAX_LOGIN_ATTEMPTS

    @pytest.mark.asyncio
    async def test_get_remaining_attempts_with_history(self, auth_service_instance):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.get = AsyncMock(return_value="3")
            result = await auth_service_instance.get_remaining_attempts("testuser")
            assert result == max(0, settings.MAX_LOGIN_ATTEMPTS - 3)

    @pytest.mark.asyncio
    async def test_get_remaining_attempts_exceeds_max(self, auth_service_instance):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.get = AsyncMock(return_value="10")
            result = await auth_service_instance.get_remaining_attempts("testuser")
            assert result == 0

    @pytest.mark.asyncio
    async def test_get_lockout_remaining(self, auth_service_instance):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.ttl = AsyncMock(return_value=600)
            result = await auth_service_instance.get_lockout_remaining("testuser")
            assert result == 600


class TestAuthServiceTokenBlacklist:
    @pytest.fixture
    def auth_service_instance(self):
        return AuthService()

    @pytest.mark.asyncio
    async def test_blacklist_token(self, auth_service_instance):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.set = AsyncMock(return_value=True)
            await auth_service_instance.blacklist_token("test_token", expire_seconds=3600)
            mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_blacklist_token_uses_default_expiry(self, auth_service_instance):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.set = AsyncMock(return_value=True)
            await auth_service_instance.blacklist_token("test_token")
            expected_ttl = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
            call_args = mock_cache.set.call_args
            assert call_args[1]["expire"] == expected_ttl

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_true(self, auth_service_instance):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.get = AsyncMock(return_value="1")
            result = await auth_service_instance.is_token_blacklisted("blacklisted_token")
            assert result is True

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_false(self, auth_service_instance):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.get = AsyncMock(return_value=None)
            result = await auth_service_instance.is_token_blacklisted("valid_token")
            assert result is False
