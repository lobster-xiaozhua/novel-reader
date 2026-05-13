import pytest
from datetime import timedelta

from app.core.security import (
    hash_password, verify_password, validate_password_strength,
    create_access_token, create_refresh_token, decode_token
)
from app.core.config import get_settings

settings = get_settings()


class TestPasswordHashing:
    def test_hash_password_generates_valid_hash(self):
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        assert hashed is not None
        assert len(hashed) > 0
        assert hashed.startswith("pbkdf2_sha256$")

    def test_verify_password_correct(self):
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        result = verify_password(password, hashed)
        assert result is True

    def test_verify_password_incorrect(self):
        password = "TestPassword123!"
        wrong_password = "WrongPassword!"
        hashed = hash_password(password)
        
        result = verify_password(wrong_password, hashed)
        assert result is False

    def test_verify_password_empty_password(self):
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        result = verify_password("", hashed)
        assert result is False

    def test_verify_password_invalid_hash_format(self):
        result = verify_password("password", "invalid_hash_format")
        assert result is False

    def test_verify_password_corrupted_hash(self):
        result = verify_password("password", "pbkdf2_sha256$100000$invalid$hash")
        assert result is False


class TestPasswordStrength:
    def test_validate_password_strong(self):
        password = "StrongPass123!"
        is_valid, message = validate_password_strength(password)
        assert is_valid is True
        assert message == "密码强度合格"

    def test_validate_password_too_short(self):
        password = "Ab1"
        is_valid, message = validate_password_strength(password)
        assert is_valid is False
        assert "密码至少" in message

    def test_validate_password_no_uppercase(self):
        password = "alllower123!"
        is_valid, message = validate_password_strength(password)
        assert is_valid is False
        assert "大写字母" in message

    def test_validate_password_no_lowercase(self):
        password = "ALLUPPER123!"
        is_valid, message = validate_password_strength(password)
        assert is_valid is False
        assert "小写字母" in message

    def test_validate_password_no_digit(self):
        password = "NoDigitHere!"
        is_valid, message = validate_password_strength(password)
        assert is_valid is False
        assert "数字" in message


class TestJWTToken:
    def test_create_access_token(self):
        data = {"sub": "123"}
        token = create_access_token(data)
        
        assert token is not None
        assert len(token) > 0

    def test_create_access_token_with_expiry(self):
        data = {"sub": "123"}
        expires_delta = timedelta(hours=1)
        token = create_access_token(data, expires_delta)
        
        assert token is not None

    def test_create_refresh_token(self):
        data = {"sub": "123"}
        token = create_refresh_token(data)
        
        assert token is not None
        assert len(token) > 0

    def test_decode_access_token_valid(self):
        data = {"sub": "123"}
        token = create_access_token(data)
        
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "123"
        assert payload["type"] == "access"

    def test_decode_refresh_token_valid(self):
        data = {"sub": "123"}
        token = create_refresh_token(data)
        
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "123"
        assert payload["type"] == "refresh"

    def test_decode_token_invalid(self):
        payload = decode_token("invalid.token.string")
        assert payload is None

    def test_decode_token_expired(self):
        data = {"sub": "123"}
        token = create_access_token(data, expires_delta=timedelta(seconds=-10))
        
        payload = decode_token(token)
        assert payload is None