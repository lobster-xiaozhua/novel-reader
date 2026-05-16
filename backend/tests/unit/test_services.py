import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import tempfile
import shutil

from app.services.cache_service import CacheService
from app.services.reading_service import ReadingService
from app.services.search_service import SearchService
from app.services.version_service import VersionManager, VersionStatus
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


class TestVersionManager:
    @pytest.fixture
    def temp_project_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            # Create some test files
            (project_root / "test.txt").write_text("test content")
            (project_root / "subdir").mkdir(exist_ok=True)
            (project_root / "subdir" / "another.txt").write_text("another content")
            yield project_root

    @pytest.fixture
    def version_manager(self, temp_project_root):
        return VersionManager(str(temp_project_root))

    def test_create_version(self, version_manager, temp_project_root):
        snapshot = version_manager.create_version(
            name="v1.0.0",
            description="Initial version",
            tags=["test", "initial"]
        )
        assert snapshot.version_id is not None
        assert snapshot.name == "v1.0.0"
        assert snapshot.description == "Initial version"
        assert snapshot.status == VersionStatus.ACTIVE
        assert "test.txt" in snapshot.files
        assert "subdir/another.txt" in snapshot.files
        assert "test" in snapshot.tags
        assert version_manager.current_version == snapshot.version_id

    def test_list_versions(self, version_manager):
        v1 = version_manager.create_version(name="v1", description="v1 desc")
        v2 = version_manager.create_version(name="v2", description="v2 desc")
        
        versions = version_manager.list_versions()
        assert len(versions) == 2
        assert versions[0]["version_id"] == v2.version_id
        assert versions[1]["version_id"] == v1.version_id

    def test_get_version_detail(self, version_manager):
        snapshot = version_manager.create_version(name="v1.0.0")
        detail = version_manager.get_version_detail(snapshot.version_id)
        assert detail is not None
        assert detail["name"] == "v1.0.0"
        assert detail["is_current"] is True

    def test_switch_version(self, version_manager, temp_project_root):
        # Create first version
        v1 = version_manager.create_version(name="v1")
        # Modify a file
        (temp_project_root / "test.txt").write_text("modified content")
        # Create second version
        v2 = version_manager.create_version(name="v2")
        # Switch back to v1
        result = version_manager.switch_version(v1.version_id)
        assert result is True
        assert (temp_project_root / "test.txt").read_text() == "test content"
        assert version_manager.current_version == v1.version_id

    def test_switch_invalid_version(self, version_manager):
        result = version_manager.switch_version("nonexistent")
        assert result is False

    def test_delete_version(self, version_manager):
        snapshot = version_manager.create_version(name="to_delete")
        result = version_manager.delete_version(snapshot.version_id)
        assert result is True
        assert snapshot.version_id not in version_manager.versions
        assert version_manager.get_version_detail(snapshot.version_id) is None

    def test_delete_invalid_version(self, version_manager):
        result = version_manager.delete_version("nonexistent")
        assert result is False

    def test_compare_versions(self, version_manager, temp_project_root):
        # Create first version
        v1 = version_manager.create_version(name="v1")
        # Modify existing file, add new file, delete a file
        (temp_project_root / "test.txt").write_text("modified")
        (temp_project_root / "new_file.txt").write_text("new")
        (temp_project_root / "subdir" / "another.txt").unlink()
        # Create second version
        v2 = version_manager.create_version(name="v2")
        # Compare versions
        compare_result = version_manager.compare_versions(v1.version_id, v2.version_id)
        assert "test.txt" in compare_result.files_modified
        assert "new_file.txt" in compare_result.files_added
        assert "subdir/another.txt" in compare_result.files_deleted

    def test_tag_and_untag_version(self, version_manager):
        snapshot = version_manager.create_version(name="v1")
        # Tag
        result = version_manager.tag_version(snapshot.version_id, "stable")
        assert result is True
        assert "stable" in version_manager.versions[snapshot.version_id].tags
        # Untag
        result = version_manager.untag_version(snapshot.version_id, "stable")
        assert result is True
        assert "stable" not in version_manager.versions[snapshot.version_id].tags

    def test_find_versions_by_tag(self, version_manager):
        v1 = version_manager.create_version(name="v1", tags=["stable"])
        v2 = version_manager.create_version(name="v2", tags=["stable"])
        v3 = version_manager.create_version(name="v3")
        found = version_manager.find_versions_by_tag("stable")
        assert len(found) == 2
        version_ids = [f["version_id"] for f in found]
        assert v1.version_id in version_ids
        assert v2.version_id in version_ids

    def test_auto_save_version(self, version_manager):
        snapshot = version_manager.auto_save_version()
        assert snapshot.name.startswith("自动保存_")
        assert snapshot.version_id is not None

    def test_get_current_version(self, version_manager):
        # No current version
        assert version_manager.get_current_version() is None
        # Create version
        snapshot = version_manager.create_version(name="v1")
        current = version_manager.get_current_version()
        assert current is not None
        assert current["version_id"] == snapshot.version_id
