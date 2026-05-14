import pytest
from datetime import timedelta
from unittest.mock import patch, MagicMock

from app.core.security import (
    hash_password,
    verify_password,
    validate_password_strength,
    create_access_token,
    create_refresh_token,
    decode_token,
)


class TestHashPassword:
    def test_hash_password_returns_formatted_string(self):
        hashed = hash_password("TestPassword123")
        assert hashed.startswith("pbkdf2_sha256$")
        parts = hashed.split("$")
        assert len(parts) == 4
        assert parts[0] == "pbkdf2_sha256"
        assert parts[1] == "100000"

    def test_hash_password_unique_salts(self):
        hash1 = hash_password("TestPassword123")
        hash2 = hash_password("TestPassword123")
        assert hash1 != hash2

    def test_hash_password_different_passwords_different_hashes(self):
        hash1 = hash_password("Password1")
        hash2 = hash_password("Password2")
        assert hash1 != hash2


class TestVerifyPassword:
    def test_verify_correct_password(self):
        password = "TestPassword123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_incorrect_password(self):
        hashed = hash_password("CorrectPassword123")
        assert verify_password("WrongPassword123", hashed) is False

    def test_verify_empty_password(self):
        hashed = hash_password("TestPassword123")
        assert verify_password("", hashed) is False

    def test_verify_malformed_hash(self):
        assert verify_password("password", "not_valid_hash_format") is False
        assert verify_password("password", "only_two$parts") is False

    def test_verify_bcrypt_format(self):
        bcrypt_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.5d5d5d5d5d5d5d"
        result = verify_password("password", bcrypt_hash)
        assert isinstance(result, bool)

    def test_verify_with_different_iterations(self):
        custom_hash = hash_password("TestPass99")
        assert verify_password("TestPass99", custom_hash) is True
        assert verify_password("WrongPass99", custom_hash) is False


class TestValidatePasswordStrength:
    def test_valid_password(self):
        is_valid, msg = validate_password_strength("ValidPass1")
        assert is_valid is True
        assert "合格" in msg

    def test_password_too_short(self):
        is_valid, msg = validate_password_strength("Aa1")
        assert is_valid is False
        assert "至少" in msg

    def test_password_no_uppercase(self):
        is_valid, msg = validate_password_strength("lowercase123")
        assert is_valid is False
        assert "大写" in msg

    def test_password_no_lowercase(self):
        is_valid, msg = validate_password_strength("UPPERCASE123")
        assert is_valid is False
        assert "小写" in msg

    def test_password_no_digit(self):
        is_valid, msg = validate_password_strength("NoDigitsHere")
        assert is_valid is False
        assert "数字" in msg

    def test_password_min_length_exactly_8(self):
        pwd = "Aa1" + "b" * 5
        assert len(pwd) == 8
        is_valid, _ = validate_password_strength(pwd)
        assert is_valid is True


class TestTokenCreation:
    def test_create_access_token(self):
        token = create_access_token({"sub": "123"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_expiry(self):
        token = create_access_token({"sub": "123"}, expires_delta=timedelta(minutes=30))
        assert isinstance(token, str)

    def test_create_refresh_token(self):
        token = create_refresh_token({"sub": "123"})
        assert isinstance(token, str)
        assert len(token) > 0


class TestDecodeToken:
    def test_decode_valid_access_token(self):
        token = create_access_token({"sub": "456"})
        payload = decode_token(token)
        assert payload is not None
        assert payload.get("sub") == "456"
        assert payload.get("type") == "access"

    def test_decode_valid_refresh_token(self):
        token = create_refresh_token({"sub": "789"})
        payload = decode_token(token)
        assert payload is not None
        assert payload.get("sub") == "789"
        assert payload.get("type") == "refresh"

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
