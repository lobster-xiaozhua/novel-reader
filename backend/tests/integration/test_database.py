import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, Book, Chapter, ReadingProgress, Favorite


class TestDatabaseConnection:
    @pytest.mark.asyncio
    async def test_connection(self, db_session):
        result = await db_session.execute(text("SELECT 1"))
        assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_create_user(self, db_session):
        user = User(
            username="testuser",
            password_hash="hashed_password",
            is_admin=False,
        )
        db_session.add(user)
        await db_session.commit()

        result = await db_session.execute(
            select(User).where(User.username == "testuser")
        )
        fetched = result.scalar_one_or_none()
        assert fetched is not None
        assert fetched.username == "testuser"

    @pytest.mark.asyncio
    async def test_create_book(self, db_session):
        book = Book(
            title="测试书籍",
            author="测试作者",
            folder_path="/books/test",
            total_chapters=10,
        )
        db_session.add(book)
        await db_session.commit()

        result = await db_session.execute(
            select(Book).where(Book.title == "测试书籍")
        )
        fetched = result.scalar_one_or_none()
        assert fetched is not None
        assert fetched.author == "测试作者"

    @pytest.mark.asyncio
    async def test_create_chapter(self, db_session):
        book = Book(
            title="章节测试书",
            folder_path="/books/chapter_test",
            total_chapters=1,
        )
        db_session.add(book)
        await db_session.flush()

        chapter = Chapter(
            book_id=book.id,
            chapter_number=1,
            title="第一章",
            file_path="/books/chapter_test/1.txt",
            word_count=1000,
        )
        db_session.add(chapter)
        await db_session.commit()

        result = await db_session.execute(
            select(Chapter).where(Chapter.book_id == book.id)
        )
        fetched = result.scalar_one_or_none()
        assert fetched is not None
        assert fetched.title == "第一章"

    @pytest.mark.asyncio
    async def test_reading_progress(self, db_session):
        user = User(username="progressuser", password_hash="hash")
        book = Book(title="进度测试书", folder_path="/books/progress")
        db_session.add_all([user, book])
        await db_session.flush()

        progress = ReadingProgress(
            user_id=user.id,
            book_id=book.id,
            chapter_id=1,
            position=500,
        )
        db_session.add(progress)
        await db_session.commit()

        result = await db_session.execute(
            select(ReadingProgress).where(
                ReadingProgress.user_id == user.id,
                ReadingProgress.book_id == book.id,
            )
        )
        fetched = result.scalar_one_or_none()
        assert fetched is not None
        assert fetched.position == 500

    @pytest.mark.asyncio
    async def test_favorite_unique_constraint(self, db_session):
        user = User(username="favuser", password_hash="hash")
        book = Book(title="收藏测试书", folder_path="/books/fav")
        db_session.add_all([user, book])
        await db_session.flush()

        fav1 = Favorite(user_id=user.id, book_id=book.id)
        db_session.add(fav1)
        await db_session.commit()

        fav2 = Favorite(user_id=user.id, book_id=book.id)
        db_session.add(fav2)
        with pytest.raises(Exception):
            await db_session.commit()
