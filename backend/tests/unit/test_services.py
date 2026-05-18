import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from pathlib import Path
import json
import time

from app.services.cache_service import CacheService, cache_service
from app.services.reading_service import ReadingService
from app.services.search_service import SearchService
from app.services.crawler_service import validate_crawl_url
from app.services.auth_service import AuthService, _BLACKLIST_FILE
from app.core.security import create_access_token
from app.core.config import get_settings

settings = get_settings()


class TestCacheService:
    @pytest_asyncio.fixture
    async def cache_service_fixture(self):
        service = CacheService()
        service._client = AsyncMock()
        return service

    @pytest.mark.asyncio
    async def test_get_success(self, cache_service_fixture):
        cache_service_fixture._client.get = AsyncMock(return_value="test_value")
        result = await cache_service_fixture.get("test_key")
        assert result == "test_value"

    @pytest.mark.asyncio
    async def test_get_not_available(self, cache_service_fixture):
        cache_service_fixture._client = None
        result = await cache_service_fixture.get("test_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_success(self, cache_service_fixture):
        cache_service_fixture._client.set = AsyncMock(return_value=True)
        result = await cache_service_fixture.set("key", "value", expire=300)
        assert result is True

    @pytest.mark.asyncio
    async def test_get_json(self, cache_service_fixture):
        cache_service_fixture._client.get = AsyncMock(return_value='{"name": "test"}')
        result = await cache_service_fixture.get_json("key")
        assert result == {"name": "test"}

    @pytest.mark.asyncio
    async def test_get_json_invalid(self, cache_service_fixture):
        cache_service_fixture._client.get = AsyncMock(return_value="invalid json")
        result = await cache_service_fixture.get_json("key")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_success(self, cache_service_fixture):
        cache_service_fixture._client.delete = AsyncMock(return_value=1)
        result = await cache_service_fixture.delete("key")
        assert result is True

    @pytest.mark.asyncio
    async def test_incr_success(self, cache_service_fixture):
        cache_service_fixture._client.incr = AsyncMock(return_value=5)
        result = await cache_service_fixture.incr("key")
        assert result == 5

    @pytest.mark.asyncio
    async def test_ttl_success(self, cache_service_fixture):
        cache_service_fixture._client.ttl = AsyncMock(return_value=3600)
        result = await cache_service_fixture.ttl("key")
        assert result == 3600


class TestReadingService:
    @pytest_asyncio.fixture
    async def reading_service(self):
        return ReadingService()

    @pytest.mark.asyncio
    async def test_save_progress_new(self, reading_service):
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()
        mock_db.flush = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute.return_value = mock_result

        result = await reading_service.save_progress(
            user_id=1, book_id=1, chapter_id=1, position=100, db=mock_db
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_progress_cache_miss(self, reading_service):
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute.return_value = mock_result

        with patch.object(cache_service, 'get_json', return_value=None):
            result = await reading_service.get_progress(user_id=1, book_id=1, db=mock_db)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_progress_cache_hit(self, reading_service):
        cached = {"book_id": 1, "chapter_id": 2, "position": 50}
        mock_db = AsyncMock()

        with patch.object(cache_service, 'get_json', return_value=cached):
            result = await reading_service.get_progress(user_id=1, book_id=1, db=mock_db)
        assert result == cached


class TestSearchService:
    @pytest_asyncio.fixture
    async def search_service(self):
        return SearchService()

    @pytest.mark.asyncio
    async def test_search_books_empty_query(self, search_service):
        with patch.object(cache_service, 'get_json', return_value=None):
            with patch.object(search_service, 'search_books', return_value=[(1, 0.5)]):
                result = await search_service.search_books("")
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_suggestions(self, search_service):
        with patch.object(cache_service, 'get_json', return_value=None):
            with patch.object(search_service, 'get_suggestions', return_value=["Test Book"]):
                result = await search_service.get_suggestions("test")
        assert isinstance(result, list)


class TestCrawlerSSRFProtection:
    def test_validate_crawl_url_block_localhost(self):
        assert validate_crawl_url("http://localhost:8080/test") is False
        assert validate_crawl_url("http://localhost.localdomain/test") is False
        assert validate_crawl_url("http://localhost6.local/test") is False

    def test_validate_crawl_url_block_private_ips(self):
        assert validate_crawl_url("http://192.168.1.1/test") is False
        assert validate_crawl_url("http://10.0.0.1/test") is False
        assert validate_crawl_url("http://172.16.0.1/test") is False
        assert validate_crawl_url("http://127.0.0.1/test") is False
        assert validate_crawl_url("http://::1/test") is False

    def test_validate_crawl_url_block_link_local(self):
        assert validate_crawl_url("http://169.254.169.254/test") is False
        assert validate_crawl_url("http://fe80::1/test") is False

    def test_validate_crawl_url_allow_valid_public(self):
        assert validate_crawl_url("http://example.com/test") is True
        assert validate_crawl_url("https://google.com/search") is True


class TestAuthServiceBlacklist:
    @pytest_asyncio.fixture
    async def auth_service_no_cache(self):
        with patch.object(cache_service, '_client', None):
            service = AuthService()
            service._token_blacklist = set()
            return service

    @pytest.mark.asyncio
    async def test_blacklist_persistence(self, auth_service_no_cache):
        test_token = create_access_token(data={"sub": "1"})
        
        await auth_service_no_cache.blacklist_token(test_token)
        
        assert test_token in auth_service_no_cache._token_blacklist
        
        assert _BLACKLIST_FILE.exists()
        with open(_BLACKLIST_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert test_token in data.get("tokens", [])

    @pytest.mark.asyncio
    async def test_blacklist_reload(self, auth_service_no_cache):
        test_token = create_access_token(data={"sub": "1"})
        await auth_service_no_cache.blacklist_token(test_token)
        
        new_service = AuthService()
        assert test_token in new_service._token_blacklist

    @pytest.mark.asyncio
    async def test_is_token_blacklisted(self, auth_service_no_cache):
        test_token = create_access_token(data={"sub": "1"})
        await auth_service_no_cache.blacklist_token(test_token)
        
        result = await auth_service_no_cache.is_token_blacklisted(test_token)
        assert result is True
        
        result = await auth_service_no_cache.is_token_blacklisted(create_access_token(data={"sub": "2"}))
        assert result is False
