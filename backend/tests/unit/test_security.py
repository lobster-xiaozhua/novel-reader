import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from app.core.security import (
    hash_password,
    verify_password,
    validate_password_strength,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user_id,
)
from app.core.config import Settings


class TestPasswordHashing:
    def test_hash_password_returns_formatted_string(self):
        password = "SecurePassword123"
        hashed = hash_password(password)

        assert hashed.startswith("pbkdf2_sha256$")
        parts = hashed.split("$")
        assert len(parts) == 4
        assert parts[0] == "pbkdf2_sha256"
        assert parts[1].isdigit()
        assert len(parts[2]) > 0
        assert len(parts[3]) > 0

    def test_hash_password_different_salts(self):
        password = "SamePassword123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2

    def test_verify_password_correct(self):
        password = "CorrectPassword123"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        password = "CorrectPassword123"
        hashed = hash_password(password)

        assert verify_password("WrongPassword123", hashed) is False

    def test_verify_password_empty_plain(self):
        hashed = hash_password("SomePassword123")

        assert verify_password("", hashed) is False

    def test_verify_password_invalid_format(self):
        assert verify_password("password", "invalid_hash_format") is False

    def test_verify_password_malformed_b64(self):
        malformed_hash = "pbkdf2_sha256$100000$!!!$$$!!!"

        assert verify_password("password", malformed_hash) is False

    def test_verify_password_non_integer_iterations(self):
        invalid_hash = "pbkdf2_sha256$notanumber$YWJj$def123"

        assert verify_password("password", invalid_hash) is False

    def test_verify_password_bcrypt_fallback(self):
        bcrypt_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.LkdVFXqB4JKgS"

        result = verify_password("password", bcrypt_hash)
        assert isinstance(result, bool)

    def test_verify_password_unknown_format(self):
        result = verify_password("password", "sha256$abc$def")
        assert result is False


class TestPasswordStrengthValidation:
    def test_password_minimum_length(self):
        is_valid, msg = validate_password_strength("Abc123!")
        assert is_valid is False
        assert "8" in msg

    def test_password_no_uppercase(self):
        is_valid, msg = validate_password_strength("password123!")
        assert is_valid is False
        assert "大写" in msg or "uppercase" in msg.lower()

    def test_password_no_lowercase(self):
        is_valid, msg = validate_password_strength("PASSWORD123!")
        assert is_valid is False
        assert "小写" in msg or "lowercase" in msg.lower()

    def test_password_no_digit(self):
        is_valid, msg = validate_password_strength("Password!")
        assert is_valid is False
        assert "数字" in msg or "digit" in msg.lower()

    def test_password_valid(self):
        is_valid, msg = validate_password_strength("ValidPass123")
        assert is_valid is True
        assert "合格" in msg or "valid" in msg.lower() or "ok" in msg.lower()

    def test_password_edge_case_exactly_min_length(self):
        is_valid, msg = validate_password_strength("Ab1cdefg")
        assert isinstance(is_valid, bool)


class TestJWTTokens:
    def test_create_access_token_default_expiry(self):
        token = create_access_token({"sub": 1})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_custom_expiry(self):
        token = create_access_token(
            {"sub": 1},
            expires_delta=timedelta(minutes=30)
        )
        assert isinstance(token, str)

    def test_create_refresh_token(self):
        token = create_refresh_token({"sub": 1})
        assert isinstance(token, str)

    def test_decode_token_valid(self):
        token = create_access_token({"sub": 123, "username": "testuser"})
        payload = decode_token(token)

        assert payload is not None
        assert payload.get("username") == "testuser"
        assert payload.get("type") == "access"
        assert "exp" in payload

    def test_decode_token_refresh_type(self):
        token = create_refresh_token({"sub": 1})
        payload = decode_token(token)

        assert payload is not None
        assert payload["type"] == "refresh"

    def test_decode_token_invalid(self):
        payload = decode_token("invalid.token.here")
        assert payload is None

    def test_decode_token_malformed(self):
        payload = decode_token("not-a-jwt")
        assert payload is None

    def test_decode_token_empty(self):
        payload = decode_token("")
        assert payload is None


class TestGetCurrentUserId:
    @pytest.mark.asyncio
    async def test_get_current_user_id_invalid_token(self):
        from fastapi import HTTPException
        from unittest.mock import MagicMock

        mock_credentials = MagicMock()
        mock_credentials.credentials = "invalid_token"

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_id(mock_credentials)

        assert exc_info.value.status_code == 401
        assert "无效" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_id_valid_token(self):
        from unittest.mock import MagicMock

        user_id = 42
        token = create_access_token({"sub": user_id})

        mock_credentials = MagicMock()
        mock_credentials.credentials = token

        result = await get_current_user_id(mock_credentials)
        assert result == user_id

    @pytest.mark.asyncio
    async def test_get_current_user_id_refresh_token_rejected(self):
        from fastapi import HTTPException
        from unittest.mock import MagicMock

        token = create_refresh_token({"sub": 1})

        mock_credentials = MagicMock()
        mock_credentials.credentials = token

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_id(mock_credentials)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_id_missing_sub(self):
        from fastapi import HTTPException
        from unittest.mock import MagicMock
        from jwt import encode

        mock_credentials = MagicMock()
        mock_credentials.credentials = encode({"some": "payload"}, "secret", algorithm="HS256")

        with pytest.raises(HTTPException):
            await get_current_user_id(mock_credentials)
