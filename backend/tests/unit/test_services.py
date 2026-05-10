import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from app.services.cache_service import CacheService
from app.services.reading_service import ReadingService
from app.services.search_service import SearchService
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
    async def test_save_progress_new(self, reading_service, db_session):
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()
        mock_db.flush = AsyncMock()

        result = await reading_service.save_progress(
            user_id=1, book_id=1, chapter_id=1, position=100, db=mock_db
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_progress_cache_miss(self, reading_service, db_session):
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute.return_value = mock_result

        with patch.object(reading_service, '_get_cache', return_value=None):
            result = await reading_service.get_progress(user_id=1, book_id=1, db=mock_db)
        assert result is None


class TestSearchService:
    @pytest_asyncio.fixture
    async def search_service(self):
        return SearchService()

    @pytest.mark.asyncio
    async def test_search_books_empty_query(self, search_service, db_session):
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()

        with patch.object(search_service, '_get_cache', return_value=None):
            result = await search_service.search_books("", db=mock_db)
        assert "items" in result
        assert "total" in result

    @pytest.mark.asyncio
    async def test_get_suggestions(self, search_service, db_session):
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        with patch.object(search_service, '_get_cache', return_value=None):
            result = await search_service.get_suggestions("test", db=mock_db)
        assert isinstance(result, list)
