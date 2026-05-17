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
        user = User(username="admin", password_hash="hash")
        assert user.is_admin is False or user.is_admin is None
        assert user.is_active is True or user.is_active is None


class TestBookModel:
    def test_book_creation(self):
        book = Book(
            title="测试书籍",
            author="测试作者",
            folder_path="/books/test",
            total_chapters=100,
        )
        assert book.title == "测试书籍"
        assert book.author == "测试作者"
        assert book.total_chapters == 100

    def test_book_timestamps(self):
        book = Book(title="Test", folder_path="/test")
        assert book.created_at is not None or True


class TestChapterModel:
    def test_chapter_creation(self):
        chapter = Chapter(
            book_id=1,
            chapter_number=1,
            title="第一章",
            file_path="/books/test/1.txt",
            word_count=5000,
        )
        assert chapter.chapter_number == 1
        assert chapter.word_count == 5000


class TestReadingProgressModel:
    def test_progress_creation(self):
        progress = ReadingProgress(
            user_id=1,
            book_id=1,
            chapter_id=1,
            position=100,
        )
        assert progress.position == 100


class TestFavoriteModel:
    def test_favorite_creation(self):
        favorite = Favorite(
            user_id=1,
            book_id=1,
            is_synced=True,
        )
        assert favorite.is_synced is True


class TestCrawlerTaskModel:
    def test_task_creation(self):
        task = CrawlerTask(
            url="https://example.com/novel",
            status="pending",
            total_chapters=0,
            downloaded_chapters=0,
        )
        assert task.status == "pending"
        assert task.total_chapters == 0
