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


class TestPasswordHashing:
    def test_hash_password_returns_hash(self):
        password = "SecurePassword123"
        hashed = hash_password(password)

        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$2")

    def test_verify_password_correct(self):
        password = "SecurePassword123"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        password = "SecurePassword123"
        wrong_password = "WrongPassword456"
        hashed = hash_password(password)

        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_invalid_hash(self):
        result = verify_password("password", "invalid_hash")
        assert result is False

    def test_verify_password_none_hash(self):
        import pytest
        with pytest.raises(AttributeError):
            verify_password("password", None)


class TestPasswordValidation:
    def test_validate_password_too_short(self):
        is_valid, message = validate_password_strength("Ab1")
        assert is_valid is False
        assert "至少" in message

    def test_validate_password_no_uppercase(self):
        is_valid, message = validate_password_strength("password123")
        assert is_valid is False
        assert "大写" in message

    def test_validate_password_no_lowercase(self):
        is_valid, message = validate_password_strength("PASSWORD123")
        assert is_valid is False
        assert "小写" in message

    def test_validate_password_no_digit(self):
        is_valid, message = validate_password_strength("PasswordABC")
        assert is_valid is False
        assert "数字" in message

    def test_validate_password_valid(self):
        is_valid, message = validate_password_strength("SecurePass123")
        assert is_valid is True

    def test_validate_password_edge_case(self):
        is_valid, _ = validate_password_strength("Ab1")
        assert is_valid is False

        is_valid, _ = validate_password_strength("Ab12345678")
        assert is_valid is True


class TestTokenCreation:
    def test_create_access_token(self):
        data = {"sub": "12345", "username": "testuser"}
        token = create_access_token(data)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_expiry(self):
        data = {"sub": "12345"}
        token = create_access_token(data, expires_delta=timedelta(minutes=30))

        assert isinstance(token, str)

    def test_create_refresh_token(self):
        data = {"sub": "12345"}
        token = create_refresh_token(data)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_access_and_refresh_tokens_different(self):
        data = {"sub": "12345"}
        access_token = create_access_token(data)
        refresh_token = create_refresh_token(data)

        assert access_token != refresh_token


class TestTokenDecoding:
    def test_decode_valid_access_token(self):
        data = {"sub": "12345", "username": "testuser"}
        token = create_access_token(data)

        payload = decode_token(token)

        assert payload is not None
        assert payload["sub"] == "12345"
        assert payload["username"] == "testuser"
        assert payload["type"] == "access"
        assert "exp" in payload

    def test_decode_valid_refresh_token(self):
        data = {"sub": "12345"}
        token = create_refresh_token(data)

        payload = decode_token(token)

        assert payload is not None
        assert payload["sub"] == "12345"
        assert payload["type"] == "refresh"

    def test_decode_invalid_token(self):
        payload = decode_token("invalid.token.here")
        assert payload is None

    def test_decode_empty_token(self):
        payload = decode_token("")
        assert payload is None
