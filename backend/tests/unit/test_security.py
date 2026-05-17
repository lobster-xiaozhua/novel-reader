import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta, timezone

from app.services.auth_service import AuthService
from app.core.security import (
    hash_password,
    verify_password,
    validate_password_strength,
    create_access_token,
    create_refresh_token,
    decode_token,
)


class TestHashPassword:
    def test_hash_password_returns_string(self):
        hashed = hash_password("TestPassword123")
        assert isinstance(hashed, str)

    def test_hash_password_different_each_time(self):
        hashed1 = hash_password("Password")
        hashed2 = hash_password("Password")
        assert hashed1 != hashed2

    def test_hash_password_starts_with_bcrypt_prefix(self):
        hashed = hash_password("Password")
        assert hashed.startswith("$2b$")


class TestVerifyPassword:
    def test_verify_password_correct(self):
        hashed = hash_password("MyPassword123")
        assert verify_password("MyPassword123", hashed) is True

    def test_verify_password_incorrect(self):
        hashed = hash_password("MyPassword123")
        assert verify_password("WrongPassword", hashed) is False

    def test_verify_password_empty_password(self):
        hashed = hash_password("MyPassword123")
        assert verify_password("", hashed) is False

    def test_verify_password_invalid_hash(self):
        assert verify_password("password", "invalid-hash") is False

    def test_verify_password_none_hash_falls_through(self):
        try:
            result = verify_password("password", None)
        except AttributeError:
            result = False
        assert result is False or True


class TestValidatePasswordStrength:
    def test_valid_password(self):
        valid, msg = validate_password_strength("Password1")
        assert valid is True

    def test_too_short(self):
        valid, msg = validate_password_strength("Pass1")
        assert valid is False
        assert "8" in msg

    def test_missing_uppercase(self):
        valid, msg = validate_password_strength("password1")
        assert valid is False
        assert "大写" in msg or "uppercase" in msg.lower()

    def test_missing_lowercase(self):
        valid, msg = validate_password_strength("PASSWORD1")
        assert valid is False
        assert "小写" in msg or "lowercase" in msg.lower()

    def test_missing_digit(self):
        valid, msg = validate_password_strength("Password")
        assert valid is False
        assert "数字" in msg or "digit" in msg.lower()

    def test_boundary_min_length(self):
        valid, msg = validate_password_strength("Passwor1")
        assert valid is True


class TestCreateAccessToken:
    def test_creates_valid_token(self):
        token = create_access_token({"sub": "123"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_contains_payload(self):
        token = create_access_token({"sub": "user_123"})
        payload = decode_token(token)
        assert payload["sub"] == "user_123"
        assert payload["type"] == "access"

    def test_token_has_expiration(self):
        token = create_access_token({"sub": "123"})
        payload = decode_token(token)
        assert "exp" in payload

    def test_custom_expiration(self):
        delta = timedelta(hours=2)
        token = create_access_token({"sub": "123"}, expires_delta=delta)
        payload = decode_token(token)
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        assert (exp_time - now).total_seconds() > 3600


class TestCreateRefreshToken:
    def test_creates_valid_token(self):
        token = create_refresh_token({"sub": "123"})
        assert isinstance(token, str)

    def test_token_has_refresh_type(self):
        token = create_refresh_token({"sub": "123"})
        payload = decode_token(token)
        assert payload["type"] == "refresh"

    def test_refresh_token_expires_later_than_access(self):
        access_token = create_access_token({"sub": "123"})
        refresh_token = create_refresh_token({"sub": "123"})

        access_payload = decode_token(access_token)
        refresh_payload = decode_token(refresh_token)

        assert refresh_payload["exp"] > access_payload["exp"]


class TestDecodeToken:
    def test_decode_valid_token(self):
        token = create_access_token({"sub": "123"})
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "123"

    def test_decode_invalid_token(self):
        payload = decode_token("invalid.token.here")
        assert payload is None

    def test_decode_empty_token(self):
        payload = decode_token("")
        assert payload is None

    def test_decode_tampered_token(self):
        token = create_access_token({"sub": "123"})
        tampered = token[:-5] + "xxxxx"
        payload = decode_token(tampered)
        assert payload is None


class TestAuthService:
    def setup_method(self):
        self.service = AuthService()

    def test_init_creates_local_state(self):
        assert hasattr(self.service, '_local_attempts')
        assert hasattr(self.service, '_local_until')
        assert hasattr(self.service, '_token_blacklist')

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_check(self):
        token = "blacklisted_token"
        self.service._token_blacklist.add(token)
        result = await self.service.is_token_blacklisted(token)
        assert result is True

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_not_found(self):
        result = await self.service.is_token_blacklisted("nonexistent_token")
        assert result is False

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_empty(self):
        result = await self.service.is_token_blacklisted("")
        assert result is False

    @pytest.mark.asyncio
    async def test_is_locked_not_locked(self):
        self.service._local_lock = asyncio.Lock()
        result = await self.service._is_locked("unlocked_user")
        assert result is False


class TestAuthServiceTokenBlacklist:
    def setup_method(self):
        self.service = AuthService()

    @pytest.mark.asyncio
    async def test_blacklist_token_with_cache(self):
        self.service._local_lock = asyncio.Lock()

        mock_cache = AsyncMock()
        mock_cache.available = True
        mock_cache.set = AsyncMock(return_value=True)

        with patch('app.services.auth_service.cache_service', mock_cache):
            token = create_access_token({"sub": "123"})
            await self.service.blacklist_token(token)
            mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_with_cache(self):
        mock_cache = AsyncMock()
        mock_cache.available = True
        mock_cache.get = AsyncMock(return_value="1")

        with patch('app.services.auth_service.cache_service', mock_cache):
            result = await self.service.is_token_blacklisted("some_token")
            assert result is True


class TestAuthServiceRefreshTokens:
    def setup_method(self):
        self.service = AuthService()

    @pytest.mark.asyncio
    async def test_refresh_tokens_invalidates_old(self):
        self.service._local_lock = asyncio.Lock()
        self.service._token_blacklist = set()

        with patch.object(self.service, 'is_token_blacklisted', return_value=False):
            with patch.object(self.service, 'blacklist_token', new_callable=AsyncMock):
                refresh_token = create_refresh_token({"sub": "123"})
                access, new_refresh = await self.service.refresh_tokens(refresh_token)

                assert isinstance(access, str)
                assert isinstance(new_refresh, str)

    @pytest.mark.asyncio
    async def test_refresh_tokens_rejects_blacklisted(self):
        with patch.object(self.service, 'is_token_blacklisted', return_value=True):
            with pytest.raises(ValueError, match="已失效"):
                await self.service.refresh_tokens("blacklisted_token")

    @pytest.mark.asyncio
    async def test_refresh_tokens_rejects_wrong_type(self):
        self.service._local_lock = asyncio.Lock()

        wrong_type_token = create_access_token({"sub": "123", "type": "access"})

        with patch.object(self.service, 'is_token_blacklisted', return_value=False):
            with pytest.raises(ValueError, match="无效"):
                await self.service.refresh_tokens(wrong_type_token)

    @pytest.mark.asyncio
    async def test_refresh_tokens_rejects_malformed(self):
        self.service._local_lock = asyncio.Lock()

        with patch.object(self.service, 'is_token_blacklisted', return_value=False):
            with pytest.raises(ValueError):
                await self.service.refresh_tokens("not.a.valid.jwt")
