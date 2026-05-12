import pytest
from datetime import timedelta

from app.core.security import (
    hash_password, verify_password, validate_password_strength,
    create_access_token, create_refresh_token, decode_token
)
from app.core.config import get_settings

settings = get_settings()


class TestPasswordHashing:
    def test_hash_password_generates_different_hashes(self):
        password = "Password123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2

    def test_verify_password_correct(self):
        password = "Password123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        password = "Password123"
        hashed = hash_password(password)
        assert verify_password("WrongPassword", hashed) is False

    def test_verify_password_empty(self):
        hashed = hash_password("Password123")
        assert verify_password("", hashed) is False

    def test_verify_password_invalid_hash_format(self):
        assert verify_password("password", "invalid_hash_format") is False

    def test_verify_password_bcrypt_fallback(self):
        try:
            import bcrypt
            bcrypt_hash = bcrypt.hashpw(b"test_password", bcrypt.gensalt())
            assert verify_password("test_password", bcrypt_hash.decode("utf-8")) is True
        except ImportError:
            pytest.skip("bcrypt not installed")


class TestPasswordStrengthValidation:
    def test_password_meets_all_requirements(self):
        valid, message = validate_password_strength("Password123")
        assert valid is True
        assert "合格" in message

    def test_password_too_short(self):
        valid, message = validate_password_strength("Pass1")
        assert valid is False
        assert str(settings.PASSWORD_MIN_LENGTH) in message

    def test_password_no_uppercase(self):
        valid, message = validate_password_strength("password123")
        assert valid is False
        assert "大写字母" in message

    def test_password_no_lowercase(self):
        valid, message = validate_password_strength("PASSWORD123")
        assert valid is False
        assert "小写字母" in message

    def test_password_no_digit(self):
        valid, message = validate_password_strength("Password")
        assert valid is False
        assert "数字" in message

    def test_password_empty(self):
        valid, message = validate_password_strength("")
        assert valid is False


class TestJWTToken:
    def test_create_and_decode_access_token(self):
        data = {"sub": "123"}
        token = create_access_token(data)
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "123"
        assert payload["type"] == "access"

    def test_create_and_decode_refresh_token(self):
        data = {"sub": "123"}
        token = create_refresh_token(data)
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "123"
        assert payload["type"] == "refresh"

    def test_decode_token_invalid_signature(self):
        invalid_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjMiLCJ0eXBlIjoiYWNjZXNzIn0.invalid_signature"
        payload = decode_token(invalid_token)
        assert payload is None

    def test_decode_token_expired(self):
        data = {"sub": "123"}
        token = create_access_token(data, expires_delta=timedelta(seconds=-10))
        payload = decode_token(token)
        assert payload is None

    def test_decode_token_invalid_format(self):
        payload = decode_token("not_a_valid_token")
        assert payload is None

    def test_token_types_differ(self):
        access_token = create_access_token({"sub": "123"})
        refresh_token = create_refresh_token({"sub": "123"})
        access_payload = decode_token(access_token)
        refresh_payload = decode_token(refresh_token)
        assert access_payload["type"] == "access"
        assert refresh_payload["type"] == "refresh"