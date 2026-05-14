import pytest
import json
import tempfile
import shutil
from pathlib import Path

from app.services.version_service import (
    VersionManager,
    VersionSnapshot,
    VersionStatus,
    VersionCompareResult,
)


class TestVersionSnapshot:
    def test_snapshot_to_dict(self):
        snapshot = VersionSnapshot(
            version_id="v1_test",
            name="Test Version",
            description="A test version",
            timestamp="2024-01-01T00:00:00",
            status=VersionStatus.ACTIVE,
            files=["main.py", "config.py"],
            file_hashes={"main.py": "abc123", "config.py": "def456"},
            snapshot_path="/path/to/snapshot",
            tags=["stable"]
        )
        d = snapshot.to_dict()
        assert d["version_id"] == "v1_test"
        assert d["status"] == "active"
        assert "stable" in d["tags"]

    def test_snapshot_tags_default_empty(self):
        snapshot = VersionSnapshot(
            version_id="v1",
            name="Test",
            description="",
            timestamp="2024-01-01",
            status=VersionStatus.ACTIVE,
            files=[],
            file_hashes={},
            snapshot_path="/path"
        )
        assert snapshot.tags == []


class TestVersionManager:
    @pytest.fixture
    def temp_project_root(self):
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def version_manager(self, temp_project_root):
        return VersionManager(str(temp_project_root))

    def test_manager_initialization(self, version_manager, temp_project_root):
        assert version_manager.project_root == temp_project_root.resolve()
        assert version_manager.version_dir.exists()
        assert version_manager.versions == {}
        assert version_manager.current_version is None

    def test_generate_version_id_increments(self, version_manager):
        id1 = version_manager._generate_version_id()
        id2 = version_manager._generate_version_id()
        assert id1 != id2
        assert version_manager.version_counter == 2

    def test_get_file_hash(self, version_manager, temp_project_root):
        test_file = temp_project_root / "test.py"
        test_file.write_text("print('hello')")
        hash1 = version_manager._get_file_hash(test_file)
        assert len(hash1) == 32

    def test_get_file_hash_empty_for_missing(self, version_manager):
        result = version_manager._get_file_hash(Path("/nonexistent"))
        assert result == ""

    def test_create_version(self, version_manager, temp_project_root):
        test_file = temp_project_root / "app.py"
        test_file.write_text("app = True")
        snapshot = version_manager.create_version("v1", "First version")
        assert snapshot.version_id.startswith("v1_")
        assert snapshot.name == "v1"
        assert version_manager.current_version == snapshot.version_id
        assert len(version_manager.versions) == 1

    def test_create_version_saves_to_disk(self, version_manager, temp_project_root):
        test_file = temp_project_root / "data.txt"
        test_file.write_text("data")
        version_manager.create_version("test", "description")
        assert version_manager.version_db_path.exists()

    def test_switch_version_updates_current(self, version_manager, temp_project_root):
        test_file = temp_project_root / "file.txt"
        test_file.write_text("content")
        v1 = version_manager.create_version("v1", auto_switch=False)
        v2 = version_manager.create_version("v2", auto_switch=False)
        result = version_manager.switch_version(v1.version_id)
        assert result is True
        assert version_manager.current_version == v1.version_id

    def test_switch_version_fails_for_nonexistent(self, version_manager):
        result = version_manager.switch_version("nonexistent_id")
        assert result is False

    def test_delete_version_removes_snapshot(self, version_manager, temp_project_root):
        test_file = temp_project_root / "file.txt"
        test_file.write_text("content")
        snapshot = version_manager.create_version("to_delete")
        snapshot_path = Path(snapshot.snapshot_path)
        version_manager.delete_version(snapshot.version_id)
        assert snapshot.version_id not in version_manager.versions
        assert not snapshot_path.exists()

    def test_list_versions(self, version_manager, temp_project_root):
        test_file = temp_project_root / "f.txt"
        test_file.write_text("x")
        version_manager.create_version("v1", tags=["stable"])
        version_manager.create_version("v2", tags=["beta"])
        versions = version_manager.list_versions()
        assert len(versions) == 2
        assert any(v["tags"] == ["stable"] for v in versions)

    def test_get_version_detail(self, version_manager, temp_project_root):
        test_file = temp_project_root / "f.txt"
        test_file.write_text("x")
        snapshot = version_manager.create_version("detailed")
        detail = version_manager.get_version_detail(snapshot.version_id)
        assert detail is not None
        assert detail["version_id"] == snapshot.version_id
        assert detail["is_current"] is True

    def test_get_version_detail_nonexistent(self, version_manager):
        detail = version_manager.get_version_detail("nonexistent")
        assert detail is None

    def test_tag_version(self, version_manager, temp_project_root):
        test_file = temp_project_root / "f.txt"
        test_file.write_text("x")
        snapshot = version_manager.create_version("tagged")
        result = version_manager.tag_version(snapshot.version_id, "production")
        assert result is True
        assert "production" in version_manager.versions[snapshot.version_id].tags

    def test_untag_version(self, version_manager, temp_project_root):
        test_file = temp_project_root / "f.txt"
        test_file.write_text("x")
        snapshot = version_manager.create_version("untagged", tags=["old"])
        result = version_manager.untag_version(snapshot.version_id, "old")
        assert result is True
        assert "old" not in version_manager.versions[snapshot.version_id].tags

    def test_find_versions_by_tag(self, version_manager, temp_project_root):
        test_file = temp_project_root / "f.txt"
        test_file.write_text("x")
        version_manager.create_version("v1", tags=["stable"])
        version_manager.create_version("v2")
        found = version_manager.find_versions_by_tag("stable")
        assert len(found) == 1

    def test_get_current_version(self, version_manager, temp_project_root):
        test_file = temp_project_root / "f.txt"
        test_file.write_text("x")
        snapshot = version_manager.create_version("current")
        current = version_manager.get_current_version()
        assert current is not None
        assert current["version_id"] == snapshot.version_id

    def test_compare_versions_added_file(self, version_manager, temp_project_root):
        test_file = temp_project_root / "base.py"
        test_file.write_text("initial")
        v1 = version_manager.create_version("base", auto_switch=False)
        (temp_project_root / "new.py").write_text("new file")
        v2 = version_manager.create_version("with_new", auto_switch=False)
        result = version_manager.compare_versions(v1.version_id, v2.version_id)
        assert "new.py" in result.files_added

    def test_compare_versions_deleted_file(self, version_manager, temp_project_root):
        test_file = temp_project_root / "base.py"
        test_file.write_text("initial")
        v1 = version_manager.create_version("base", auto_switch=False)
        test_file.unlink()
        (temp_project_root / "other.py").write_text("x")
        v2 = version_manager.create_version("without_base", auto_switch=False)
        result = version_manager.compare_versions(v1.version_id, v2.version_id)
        assert "base.py" in result.files_deleted

    def test_compare_versions_modified_file(self, version_manager, temp_project_root):
        test_file = temp_project_root / "file.py"
        test_file.write_text("original")
        v1 = version_manager.create_version("original", auto_switch=False)
        test_file.write_text("modified content")
        v2 = version_manager.create_version("modified", auto_switch=False)
        result = version_manager.compare_versions(v1.version_id, v2.version_id)
        assert "file.py" in result.files_modified
        assert len(result.diffs) > 0

    def test_auto_save_version(self, version_manager, temp_project_root):
        test_file = temp_project_root / "f.txt"
        test_file.write_text("x")
        snapshot = version_manager.auto_save_version()
        assert "自动保存" in snapshot.name
        assert snapshot.version_id.startswith("v")
