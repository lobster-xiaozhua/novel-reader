import pytest
import pytest_asyncio
import time
import tempfile
import os
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from app.services.cache_service import CacheService
from app.services.reading_service import ReadingService
from app.services.search_service import SearchService
from app.services.auth_service import AuthService
from app.services.scan_service import BookScanner
from app.core.config import get_settings

settings = get_settings()


class TestCacheService:
    @pytest_asyncio.fixture
    async def cache_service(self):
        service = CacheService()
        service._client = AsyncMock()
        return service

    @pytest.mark.asyncio
    async def test_get_success(self, cache_service):
        cache_service._client.get = AsyncMock(return_value="test_value")
        result = await cache_service.get("test_key")
        assert result == "test_value"

    @pytest.mark.asyncio
    async def test_get_not_available(self, cache_service):
        cache_service._client = None
        result = await cache_service.get("test_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_success(self, cache_service):
        cache_service._client.set = AsyncMock(return_value=True)
        result = await cache_service.set("key", "value", expire=300)
        assert result is True

    @pytest.mark.asyncio
    async def test_get_json(self, cache_service):
        cache_service._client.get = AsyncMock(return_value='{"name": "test"}')
        result = await cache_service.get_json("key")
        assert result == {"name": "test"}

    @pytest.mark.asyncio
    async def test_get_json_invalid(self, cache_service):
        cache_service._client.get = AsyncMock(return_value="invalid json")
        result = await cache_service.get_json("key")
        assert result is None


class TestReadingService:
    @pytest_asyncio.fixture
    async def reading_service(self):
        return ReadingService()

    @pytest.mark.asyncio
    async def test_save_progress_new(self, reading_service):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.flush = AsyncMock()

        result = await reading_service.save_progress(
            user_id=1, book_id=1, chapter_id=1, position=100, db=mock_db
        )
        assert result is not None
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_progress_update(self, reading_service):
        mock_db = AsyncMock()
        existing_progress = MagicMock()
        existing_progress.chapter_id = 1
        existing_progress.position = 50
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=existing_progress)
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await reading_service.save_progress(
            user_id=1, book_id=1, chapter_id=2, position=200, db=mock_db
        )
        assert result is existing_progress
        assert existing_progress.chapter_id == 2
        assert existing_progress.position == 200


class TestSearchService:
    def test_search_service_initialization(self):
        service = SearchService()
        assert service is not None

    def test_ensure_fts_table_exists(self):
        import inspect
        assert hasattr(SearchService, 'ensure_fts_table')
        assert inspect.iscoroutinefunction(SearchService.ensure_fts_table)


class TestAuthService:
    @pytest_asyncio.fixture
    async def auth_service(self):
        service = AuthService()
        service._local_attempts = {}
        service._local_lockout = {}
        return service

    @pytest.mark.asyncio
    async def test_check_login_attempts_no_attempts(self, auth_service):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.available = False
            result = await auth_service.check_login_attempts("newuser")
            assert result is True

    @pytest.mark.asyncio
    async def test_check_login_attempts_locked_out_local(self, auth_service):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.available = False
            auth_service._local_lockout["lockeduser"] = time.time() + 300
            result = await auth_service.check_login_attempts("lockeduser")
            assert result is False

    @pytest.mark.asyncio
    async def test_check_login_attempts_locked_out_cache(self, auth_service):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.available = True
            mock_cache.ttl = AsyncMock(return_value=100)
            result = await auth_service.check_login_attempts("lockeduser")
            assert result is False

    @pytest.mark.asyncio
    async def test_check_login_attempts_no_lockout_cache(self, auth_service):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.available = True
            mock_cache.ttl = AsyncMock(return_value=0)
            result = await auth_service.check_login_attempts("normaluser")
            assert result is True

    @pytest.mark.asyncio
    async def test_record_failed_login_cache(self, auth_service):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.available = True
            mock_cache.incr = AsyncMock(side_effect=[1, 2, 3, 4, 5])
            mock_cache.expire = AsyncMock()
            mock_cache.set = AsyncMock()

            await auth_service.record_failed_login("testuser")
            mock_cache.incr.assert_called_once()
            mock_cache.expire.assert_called_once()

            await auth_service.record_failed_login("testuser")
            mock_cache.incr.assert_called()

    @pytest.mark.asyncio
    async def test_record_failed_login_lockout_triggered(self, auth_service):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.available = True
            mock_cache.incr = AsyncMock(return_value=5)
            mock_cache.expire = AsyncMock()
            mock_cache.set = AsyncMock()

            await auth_service.record_failed_login("testuser")
            mock_cache.set.assert_called()

    @pytest.mark.asyncio
    async def test_record_failed_login_local(self, auth_service):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.available = False

            await auth_service.record_failed_login("testuser")
            assert auth_service._local_attempts["testuser"] == 1

            await auth_service.record_failed_login("testuser")
            assert auth_service._local_attempts["testuser"] == 2

    @pytest.mark.asyncio
    async def test_record_failed_login_local_lockout(self, auth_service):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.available = False

            for _ in range(5):
                await auth_service.record_failed_login("testuser")

            assert "testuser" in auth_service._local_lockout
            assert auth_service._local_lockout["testuser"] > time.time()

    @pytest.mark.asyncio
    async def test_get_remaining_attempts_cache(self, auth_service):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.available = True
            mock_cache.get = AsyncMock(return_value="3")

            result = await auth_service.get_remaining_attempts("testuser")
            assert result == 2

    @pytest.mark.asyncio
    async def test_get_remaining_attempts_no_cache(self, auth_service):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.available = True
            mock_cache.get = AsyncMock(return_value=None)

            result = await auth_service.get_remaining_attempts("newuser")
            assert result == auth_service.max_attempts

    @pytest.mark.asyncio
    async def test_get_remaining_attempts_invalid_value(self, auth_service):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.available = True
            mock_cache.get = AsyncMock(return_value="invalid")

            result = await auth_service.get_remaining_attempts("testuser")
            assert result == auth_service.max_attempts

    @pytest.mark.asyncio
    async def test_reset_login_attempts_cache(self, auth_service):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.available = True
            mock_cache.delete = AsyncMock()

            await auth_service.reset_login_attempts("testuser")
            assert mock_cache.delete.call_count == 2

    @pytest.mark.asyncio
    async def test_reset_login_attempts_local(self, auth_service):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.available = False
            auth_service._local_attempts["testuser"] = 5
            auth_service._local_lockout["testuser"] = time.time() + 300

            await auth_service.reset_login_attempts("testuser")
            assert "testuser" not in auth_service._local_attempts
            assert "testuser" not in auth_service._local_lockout

    @pytest.mark.asyncio
    async def test_blacklist_token(self, auth_service):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.available = True
            mock_cache.set = AsyncMock()

            await auth_service.blacklist_token("token123")
            mock_cache.set.assert_called_once()
            call_args = mock_cache.set.call_args
            assert "auth:blacklist:token123" in str(call_args)

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_true(self, auth_service):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.available = True
            mock_cache.get = AsyncMock(return_value="1")

            result = await auth_service.is_token_blacklisted("token123")
            assert result is True

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_false(self, auth_service):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.available = True
            mock_cache.get = AsyncMock(return_value=None)

            result = await auth_service.is_token_blacklisted("token123")
            assert result is False

    @pytest.mark.asyncio
    async def test_get_lockout_remaining_cache(self, auth_service):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.available = True
            mock_cache.ttl = AsyncMock(return_value=300)

            result = await auth_service.get_lockout_remaining("testuser")
            assert result == 300

    @pytest.mark.asyncio
    async def test_get_lockout_remaining_local(self, auth_service):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.available = False
            auth_service._local_lockout["testuser"] = time.time() + 120

            result = await auth_service.get_lockout_remaining("testuser")
            assert result > 0
            assert result <= 120

    @pytest.mark.asyncio
    async def test_get_lockout_remaining_expired(self, auth_service):
        with patch('app.services.auth_service.cache_service') as mock_cache:
            mock_cache.available = False
            auth_service._local_lockout["testuser"] = time.time() - 10

            result = await auth_service.get_lockout_remaining("testuser")
            assert result == 0


class TestBookScanner:
    @pytest.fixture
    def temp_books_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def scanner(self, temp_books_dir):
        return BookScanner(books_dir=str(temp_books_dir))

    def test_scanner_initialization(self, scanner):
        assert scanner.books_dir.exists()
        assert scanner.ALLOWED_EXTENSIONS == {'.txt'}
        assert scanner.AUTO_CONVERT_EXTENSIONS == {'.md', '.markdown'}

    def test_is_temp_file(self, scanner):
        assert scanner.is_temp_file("file.txt~") is True
        assert scanner.is_temp_file("file.tmp") is True
        assert scanner.is_temp_file("file.bak") is True
        assert scanner.is_temp_file("file.swp") is True
        assert scanner.is_temp_file("file.txt") is False
        assert scanner.is_temp_file("readme.md") is False

    @pytest.mark.asyncio
    async def test_process_file_system_file(self, scanner, temp_books_dir):
        test_file = temp_books_dir / "desktop.ini"
        test_file.write_text("config")

        result = await scanner.process_file(test_file)
        assert result == "deleted"
        assert not test_file.exists()

    @pytest.mark.asyncio
    async def test_process_file_temp_file(self, scanner, temp_books_dir):
        test_file = temp_books_dir / "novel.tmp"
        test_file.write_text("content")

        result = await scanner.process_file(test_file)
        assert result == "deleted"
        assert not test_file.exists()

    @pytest.mark.asyncio
    async def test_process_file_unsupported_format(self, scanner, temp_books_dir):
        test_file = temp_books_dir / "novel.pdf"
        test_file.write_text("content")

        result = await scanner.process_file(test_file)
        assert result == "deleted"
        assert not test_file.exists()

    @pytest.mark.asyncio
    async def test_process_file_empty_file(self, scanner, temp_books_dir):
        test_file = temp_books_dir / "empty.txt"
        test_file.write_text("")

        result = await scanner.process_file(test_file)
        assert result == "deleted"
        assert not test_file.exists()

    @pytest.mark.asyncio
    async def test_process_file_valid_txt(self, scanner, temp_books_dir):
        test_file = temp_books_dir / "valid.txt"
        test_file.write_text("这是一个有效的TXT文件内容")

        result = await scanner.process_file(test_file)
        assert result == "ok"
        assert test_file.exists()

    @pytest.mark.asyncio
    async def test_process_file_markdown_conversion(self, scanner, temp_books_dir):
        test_file = temp_books_dir / "novel.md"
        test_file.write_text("# 小说标题")

        result = await scanner.process_file(test_file)
        assert result == "converted"
        assert not test_file.exists()
        assert (temp_books_dir / "novel.txt").exists()

    @pytest.mark.asyncio
    async def test_is_readable_utf8(self, scanner, temp_books_dir):
        test_file = temp_books_dir / "utf8.txt"
        test_file.write_text("UTF-8内容测试中文", encoding='utf-8')

        result = await scanner.is_readable(test_file)
        assert result is True

    @pytest.mark.asyncio
    async def test_is_readable_gbk_fallback(self, scanner, temp_books_dir):
        test_file = temp_books_dir / "gbk.txt"
        test_file.write_text("GBK内容测试", encoding='gbk')

        result = await scanner.is_readable(test_file)
        assert result is True

    @pytest.mark.asyncio
    async def test_is_readable_invalid_encoding(self, scanner, temp_books_dir):
        test_file = temp_books_dir / "invalid.txt"
        with open(test_file, 'wb') as f:
            f.write(b'\x80\x81\x82\xff')

        result = await scanner.is_readable(test_file)
        assert result is False

    def test_extract_chapter_title_valid(self, scanner, temp_books_dir):
        test_file = temp_books_dir / "chapter.txt"
        test_file.write_text("第一章：开端\n这是正文内容")

        title = scanner._extract_chapter_title(test_file)
        assert title == "第一章：开端"

    def test_extract_chapter_title_fallback(self, scanner, temp_books_dir):
        test_file = temp_books_dir / "chapter.txt"
        test_file.write_text("非常长的行内容" * 20)

        title = scanner._extract_chapter_title(test_file)
        assert title == "chapter"

    def test_count_words(self, scanner, temp_books_dir):
        test_file = temp_books_dir / "words.txt"
        content = "这是测试内容"
        test_file.write_text(content)

        count = scanner._count_words(test_file)
        assert count == len(content)

    def test_detect_author_from_info_file(self, scanner, temp_books_dir):
        book_dir = temp_books_dir / "book1"
        book_dir.mkdir()
        info_file = book_dir / "info.txt"
        info_file.write_text("作者：张三\n简介：这是一本好书")

        author = scanner._detect_author(book_dir)
        assert author == "张三"

    def test_detect_author_english_separator(self, scanner, temp_books_dir):
        book_dir = temp_books_dir / "book2"
        book_dir.mkdir()
        info_file = book_dir / "info.txt"
        info_file.write_text("作者：John Doe\nDescription: A novel")

        author = scanner._detect_author(book_dir)
        assert author == "John Doe"

    def test_detect_author_not_found(self, scanner, temp_books_dir):
        book_dir = temp_books_dir / "book3"
        book_dir.mkdir()

        author = scanner._detect_author(book_dir)
        assert author == ""

    @pytest.mark.asyncio
    async def test_delete_file_success(self, scanner, temp_books_dir):
        test_file = temp_books_dir / "delete_me.txt"
        test_file.write_text("content")

        await scanner.delete_file(test_file, "测试删除")
        assert not test_file.exists()

    @pytest.mark.asyncio
    async def test_rename_file_success(self, scanner, temp_books_dir):
        old_file = temp_books_dir / "old.txt"
        old_file.write_text("content")
        new_file = temp_books_dir / "new.txt"

        await scanner.rename_file(old_file, new_file, "测试重命名")
        assert not old_file.exists()
        assert new_file.exists()
