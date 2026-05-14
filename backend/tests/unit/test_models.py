import pytest
from datetime import datetime
from app.models import User, Book, Chapter, ReadingProgress, Favorite, CrawlerTask


class TestUserModel:
    def test_user_creation(self):
        user = User(
            username="testuser",
            password_hash="hashed_password",
            is_admin=False,
            is_active=True,
        )
        assert user.username == "testuser"
        assert user.is_admin is False
        assert user.is_active is True

    def test_user_admin_defaults(self):
        user = User(username="admin", password_hash="hash", is_admin=False, is_active=True)
        assert user.is_admin is False
        assert user.is_active is True
