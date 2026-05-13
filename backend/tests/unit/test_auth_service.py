import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.auth_service import AuthService
from app.core.config import get_settings

settings = get_settings()


class TestAuthService:
    @pytest_asyncio.fixture
    async def auth_service(self):
        service = AuthService()
        with patch.object(service, '_is_locked', return_value=False):
            yield service

    @pytest.mark.asyncio
    async def test_register_user_success(self, auth_service):
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = "testuser"
        
        with patch('app.services.auth_service.AsyncSessionLocal') as mock_session:
            mock_db = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db
            
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_db.execute.return_value = mock_result
            
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()
            mock_db.add = MagicMock()
            
            user = await auth_service.register_user("testuser", "password123")
            
            assert user is not None

    @pytest.mark.asyncio
    async def test_register_user_username_taken(self, auth_service):
        mock_user = MagicMock()
        mock_user.username = "testuser"
        
        with patch('app.services.auth_service.AsyncSessionLocal') as mock_session:
            mock_db = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db
            
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_user
            mock_db.execute.return_value = mock_result
            
            with pytest.raises(ValueError, match="Username taken"):
                await auth_service.register_user("testuser", "password123")

    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, auth_service):
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = "testuser"
        mock_user.hashed_password = "$2b$12$EixZaYbB.rK4fl8x2q7Meu6Q6D2V5fF5Q5Q5Q5Q5Q5Q5Q5Q5Q5Q"
        
        with patch('app.services.auth_service.AsyncSessionLocal') as mock_session:
            mock_db = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db
            
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_user
            mock_db.execute.return_value = mock_result
            
            with patch('app.services.auth_service.hash_password') as mock_hash:
                mock_hash.return_value = mock_user.hashed_password
                with patch('app.services.auth_service.verify_password', return_value=True):
                    with patch('app.services.auth_service.create_access_token') as mock_access:
                        mock_access.return_value = "access_token"
                        with patch('app.services.auth_service.create_refresh_token') as mock_refresh:
                            mock_refresh.return_value = "refresh_token"
                            
                            user, access, refresh = await auth_service.authenticate_user("testuser", "password")
                            
                            assert user is not None
                            assert access == "access_token"
                            assert refresh == "refresh_token"

    @pytest.mark.asyncio
    async def test_authenticate_user_invalid_credentials(self, auth_service):
        with patch('app.services.auth_service.AsyncSessionLocal') as mock_session:
            mock_db = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db
            
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_db.execute.return_value = mock_result
            
            with pytest.raises(ValueError, match="Bad credentials"):
                await auth_service.authenticate_user("testuser", "wrongpassword")

    @pytest.mark.asyncio
    async def test_authenticate_user_locked(self, auth_service):
        with patch.object(auth_service, '_is_locked', return_value=True):
            with pytest.raises(ValueError, match="Login locked"):
                await auth_service.authenticate_user("testuser", "password")

    @pytest.mark.asyncio
    async def test_refresh_tokens_valid(self, auth_service):
        with patch('app.services.auth_service.decode_token') as mock_decode:
            mock_decode.return_value = {"sub": "123", "type": "refresh"}
            
            with patch('app.services.auth_service.is_token_blacklisted', return_value=False):
                with patch('app.services.auth_service.create_access_token') as mock_access:
                    mock_access.return_value = "new_access_token"
                    with patch('app.services.auth_service.create_refresh_token') as mock_refresh:
                        mock_refresh.return_value = "new_refresh_token"
                        with patch.object(auth_service, 'blacklist_token') as mock_blacklist:
                            access, refresh = await auth_service.refresh_tokens("old_refresh_token")
                            
                            assert access == "new_access_token"
                            assert refresh == "new_refresh_token"
                            mock_blacklist.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_tokens_blacklisted(self, auth_service):
        with patch('app.services.auth_service.is_token_blacklisted', return_value=True):
            with pytest.raises(ValueError, match="Token invalid"):
                await auth_service.refresh_tokens("blacklisted_token")

    @pytest.mark.asyncio
    async def test_refresh_tokens_invalid_type(self, auth_service):
        with patch('app.services.auth_service.decode_token') as mock_decode:
            mock_decode.return_value = {"sub": "123", "type": "access"}
            
            with pytest.raises(ValueError, match="Invalid token"):
                await auth_service.refresh_tokens("access_token")

    @pytest.mark.asyncio
    async def test_blacklist_token_memory(self, auth_service):
        with patch('app.services.cache_service.is_redis_available', False):
            token = "test_token"
            await auth_service.blacklist_token(token)
            
            is_blacklisted = await auth_service.is_token_blacklisted(token)
            assert is_blacklisted is True

    @pytest.mark.asyncio
    async def test_blacklist_token_redis(self, auth_service):
        with patch('app.services.cache_service.is_redis_available', True):
            with patch('app.services.cache_service.setex') as mock_setex:
                mock_setex.return_value = True
                
                token = "test_token"
                with patch('app.services.auth_service.decode_token') as mock_decode:
                    mock_decode.return_value = {"exp": 9999999999}
                    await auth_service.blacklist_token(token)
                    
                    mock_setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_not_blacklisted(self, auth_service):
        with patch('app.services.cache_service.is_redis_available', False):
            result = await auth_service.is_token_blacklisted("nonexistent_token")
            assert result is False

    @pytest.mark.asyncio
    async def test_logout(self, auth_service):
        with patch.object(auth_service, 'blacklist_token') as mock_blacklist:
            await auth_service.logout("test_token")
            mock_blacklist.assert_called_once_with("test_token")

    @pytest.mark.asyncio
    async def test_record_fail_memory(self, auth_service):
        with patch('app.services.cache_service.is_redis_available', False):
            settings.LOGIN_RATE_LIMIT_MAX = 3
            
            await auth_service._record_fail("testuser")
            await auth_service._record_fail("testuser")
            await auth_service._record_fail("testuser")
            
            is_locked = await auth_service._is_locked("testuser")
            assert is_locked is True

    @pytest.mark.asyncio
    async def test_clear_attempts(self, auth_service):
        with patch('app.services.cache_service.is_redis_available', False):
            auth_service._local_attempts["testuser"] = 2
            
            await auth_service._clear_attempts("testuser")
            
            assert "testuser" not in auth_service._local_attempts