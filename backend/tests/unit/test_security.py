import pytest
from datetime import timedelta

from app.core.security import (
    hash_password,
    verify_password,
    validate_password_strength,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.config import get_settings

settings = get_settings()


class TestHashPassword:
    def test_hash_password_returns_string(self):
        hashed = hash_password("testpassword123")
        assert isinstance(hashed, str)
        assert hashed != "testpassword123"

    def test_hash_password_different_each_time(self):
        hash1 = hash_password("password")
        hash2 = hash_password("password")
        assert hash1 != hash2

    def test_hash_password_correct_length(self):
        hashed = hash_password("testpassword123")
        assert len(hashed) >= 50


class TestVerifyPassword:
    def test_verify_password_correct(self):
        password = "SecurePass123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        hashed = hash_password("correctpassword")
        assert verify_password("wrongpassword", hashed) is False

    def test_verify_password_empty_plain(self):
        hashed = hash_password("somepassword")
        assert verify_password("", hashed) is False

    def test_verify_password_empty_hash(self):
        assert verify_password("password", "") is False

    def test_verify_password_invalid_hash_format(self):
        assert verify_password("password", "not_a_valid_hash") is False


class TestValidatePasswordStrength:
    def test_password_too_short(self):
        is_valid, message = validate_password_strength("Ab1")
        assert is_valid is False
        assert "至少" in message
        assert str(settings.PASSWORD_MIN_LENGTH) in message

    def test_password_no_uppercase(self):
        is_valid, message = validate_password_strength("abcdefgh")
        assert is_valid is False
        assert "大写字母" in message

    def test_password_no_lowercase(self):
        is_valid, message = validate_password_strength("ABCDEFGH")
        assert is_valid is False
        assert "小写字母" in message

    def test_password_no_digit(self):
        is_valid, message = validate_password_strength("AbCdEfGh")
        assert is_valid is False
        assert "数字" in message

    def test_password_valid(self):
        is_valid, message = validate_password_strength("ValidPass123")
        assert is_valid is True
        assert "合格" in message

    def test_password_at_minimum_length(self):
        min_len = settings.PASSWORD_MIN_LENGTH
        password = "A" + "b" * (min_len - 2) + "1"
        is_valid, message = validate_password_strength(password)
        assert is_valid is True

    def test_password_exactly_minimum_length_too_short(self):
        min_len = settings.PASSWORD_MIN_LENGTH
        password = "A" + "b" * (min_len - 2)
        is_valid, message = validate_password_strength(password)
        assert is_valid is False


class TestCreateAccessToken:
    def test_create_access_token_basic(self):
        token = create_access_token({"sub": "123"})
        assert isinstance(token, str)
        assert len(token) > 20

    def test_create_access_token_with_expiry(self):
        token = create_access_token({"sub": "123"}, expires_delta=timedelta(hours=1))
        assert isinstance(token, str)

    def test_create_access_token_contains_exp_claim(self):
        payload = decode_token(create_access_token({"sub": "123"}))
        assert "exp" in payload
        assert payload["type"] == "access"
        assert payload["sub"] == "123"

    def test_access_token_default_expiry(self):
        payload = decode_token(create_access_token({"sub": "123"}))
        assert "exp" in payload


class TestCreateRefreshToken:
    def test_create_refresh_token_basic(self):
        token = create_refresh_token({"sub": "123"})
        assert isinstance(token, str)
        assert len(token) > 20

    def test_refresh_token_contains_exp_claim(self):
        payload = decode_token(create_refresh_token({"sub": "123"}))
        assert "exp" in payload
        assert payload["type"] == "refresh"
        assert payload["sub"] == "123"

    def test_refresh_token_has_longer_expiry(self):
        access_payload = decode_token(create_access_token({"sub": "123"}))
        refresh_payload = decode_token(create_refresh_token({"sub": "123"}))
        assert access_payload["exp"] < refresh_payload["exp"]


class TestDecodeToken:
    def test_decode_valid_token(self):
        token = create_access_token({"sub": "123", "data": "test"})
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "123"
        assert payload["data"] == "test"

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

    def test_decode_expired_token(self):
        token = create_access_token(
            {"sub": "123"},
            expires_delta=timedelta(seconds=-1)
        )
        payload = decode_token(token)
        assert payload is None

    def test_decode_token_without_exp(self):
        from jose import jwt
        custom_token = jwt.encode(
            {"sub": "123", "type": "access"},
            settings.SECRET_KEY,
            algorithm="HS256"
        )
        payload = decode_token(custom_token)
        assert payload is not None
