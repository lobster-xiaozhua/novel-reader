import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from app.services.version_service import (
    VersionManager,
    VersionSnapshot,
    VersionStatus,
    FileDiff,
    VersionCompareResult,
)


class TestVersionStatus:
    def test_version_status_values(self):
        assert VersionStatus.ACTIVE.value == "active"
        assert VersionStatus.ARCHIVED.value == "archived"
        assert VersionStatus.ROLLED_BACK.value == "rolled_back"


class TestVersionSnapshot:
    def test_version_snapshot_creation(self):
        snapshot = VersionSnapshot(
            version_id="v1_20240101",
            name="Test Version",
            description="A test version",
            timestamp="2024-01-01T00:00:00",
            status=VersionStatus.ACTIVE,
            files=["file1.txt", "file2.txt"],
            file_hashes={"file1.txt": "abc123", "file2.txt": "def456"},
            snapshot_path="/versions/v1",
        )

        assert snapshot.version_id == "v1_20240101"
        assert snapshot.status == VersionStatus.ACTIVE
        assert snapshot.tags == []

    def test_version_snapshot_to_dict(self):
        snapshot = VersionSnapshot(
            version_id="v1",
            name="Test",
            description="",
            timestamp="2024-01-01",
            status=VersionStatus.ACTIVE,
            files=[],
            file_hashes={},
            snapshot_path="/test",
        )

        result = snapshot.to_dict()

        assert result["version_id"] == "v1"
        assert result["status"] == "active"
        assert "snapshot_path" in result


class TestFileDiff:
    def test_file_diff_to_dict(self):
        diff = FileDiff(
            file_path="test.txt",
            old_hash="abc",
            new_hash="def",
            old_content="old",
            new_content="new",
            diff_lines=["-old", "+new"],
            change_type="modified",
        )

        result = diff.to_dict()

        assert result["file_path"] == "test.txt"
        assert result["change_type"] == "modified"
        assert "diff_lines" in result


class TestVersionCompareResult:
    def test_version_compare_result_to_dict(self):
        result = VersionCompareResult(
            version_a="v1",
            version_b="v2",
            files_added=["new.txt"],
            files_deleted=["removed.txt"],
            files_modified=["changed.txt"],
            files_unchanged=["same.txt"],
            diffs=[],
        )

        compare_dict = result.to_dict()

        assert compare_dict["version_a"] == "v1"
        assert compare_dict["version_b"] == "v2"
        assert "new.txt" in compare_dict["files_added"]
        assert "removed.txt" in compare_dict["files_deleted"]


class TestVersionManager:
    @pytest.fixture
    def temp_project(self):
        temp_dir = tempfile.mkdtemp()
        project_root = Path(temp_dir) / "project"
        project_root.mkdir()

        (project_root / "main.py").write_text("print('hello')")
        (project_root / "README.md").write_text("# Project")
        (project_root / "data").mkdir()

        yield str(project_root)

        shutil.rmtree(temp_dir)

    def test_manager_initialization(self, temp_project):
        manager = VersionManager(temp_project)

        assert manager.project_root == Path(temp_project).resolve()
        assert manager.version_dir.exists()
        assert manager.versions == {}
        assert manager.current_version is None

    def test_generate_version_id(self, temp_project):
        manager = VersionManager(temp_project)

        version_id1 = manager._generate_version_id()
        version_id2 = manager._generate_version_id()

        assert version_id1.startswith("v1_")
        assert version_id2.startswith("v2_")
        assert version_id1 != version_id2

    def test_collect_project_files(self, temp_project):
        manager = VersionManager(temp_project)

        files = manager._collect_project_files()

        file_names = [f.name for f in files]
        assert "main.py" in file_names
        assert "README.md" in file_names

    def test_collect_project_files_excludes_patterns(self, temp_project):
        (Path(temp_project) / ".git").mkdir()
        (Path(temp_project) / "node_modules").mkdir()

        manager = VersionManager(temp_project)
        files = manager._collect_project_files()

        paths = [str(f) for f in files]
        assert not any(".git" in p for p in paths)
        assert not any("node_modules" in p for p in paths)

    def test_create_version(self, temp_project):
        manager = VersionManager(temp_project)

        snapshot = manager.create_version(
            name="Initial Version",
            description="First snapshot",
            tags=["stable"]
        )

        assert snapshot.name == "Initial Version"
        assert snapshot.status == VersionStatus.ACTIVE
        assert manager.current_version == snapshot.version_id
        assert "stable" in snapshot.tags

    def test_create_version_without_auto_switch(self, temp_project):
        manager = VersionManager(temp_project)

        v1 = manager.create_version(name="V1", auto_switch=True)
        v2 = manager.create_version(name="V2", auto_switch=False)

        assert manager.current_version == v1.version_id

    def test_create_version_multiple(self, temp_project):
        manager = VersionManager(temp_project)

        v1 = manager.create_version(name="Version 1")
        v2 = manager.create_version(name="Version 2")

        assert len(manager.versions) == 2
        assert v1.version_id in manager.versions
        assert v2.version_id in manager.versions

    def test_switch_version(self, temp_project):
        manager = VersionManager(temp_project)

        v1 = manager.create_version(name="Version 1")
        v2 = manager.create_version(name="Version 2")

        result = manager.switch_version(v1.version_id)

        assert result is True
        assert manager.current_version == v1.version_id

    def test_switch_version_not_found(self, temp_project):
        manager = VersionManager(temp_project)

        result = manager.switch_version("nonexistent_version")

        assert result is False

    def test_switch_version_snapshot_missing(self, temp_project):
        manager = VersionManager(temp_project)

        v1 = manager.create_version(name="Version 1")

        shutil.rmtree(manager.version_dir / v1.version_id)

        result = manager.switch_version(v1.version_id)

        assert result is False

    def test_delete_version(self, temp_project):
        manager = VersionManager(temp_project)

        v1 = manager.create_version(name="Version 1")

        result = manager.delete_version(v1.version_id)

        assert result is True
        assert v1.version_id not in manager.versions

    def test_delete_current_version(self, temp_project):
        manager = VersionManager(temp_project)

        v1 = manager.create_version(name="Version 1")

        manager.delete_version(v1.version_id)

        assert manager.current_version is None

    def test_delete_version_not_found(self, temp_project):
        manager = VersionManager(temp_project)

        result = manager.delete_version("nonexistent")

        assert result is False

    def test_list_versions(self, temp_project):
        manager = VersionManager(temp_project)

        v1 = manager.create_version(name="Version 1")
        v2 = manager.create_version(name="Version 2")

        versions = manager.list_versions()

        assert len(versions) == 2
        assert all(v["version_id"] in [v1.version_id, v2.version_id] for v in versions)

    def test_get_version_detail(self, temp_project):
        manager = VersionManager(temp_project)

        v1 = manager.create_version(name="Version 1")

        detail = manager.get_version_detail(v1.version_id)

        assert detail is not None
        assert detail["version_id"] == v1.version_id
        assert detail["is_current"] is True

    def test_get_version_detail_not_found(self, temp_project):
        manager = VersionManager(temp_project)

        detail = manager.get_version_detail("nonexistent")

        assert detail is None

    def test_compare_versions(self, temp_project):
        manager = VersionManager(temp_project)

        v1 = manager.create_version(name="Version 1")

        (Path(temp_project) / "new_file.txt").write_text("new content")
        v2 = manager.create_version(name="Version 2")

        result = manager.compare_versions(v1.version_id, v2.version_id)

        assert result.version_a == v1.version_id
        assert result.version_b == v2.version_id
        assert "new_file.txt" in result.files_added

    def test_compare_versions_deleted_file(self, temp_project):
        manager = VersionManager(temp_project)

        v1 = manager.create_version(name="Version 1")

        (Path(temp_project) / "main.py").unlink()
        v2 = manager.create_version(name="Version 2")

        result = manager.compare_versions(v1.version_id, v2.version_id)

        assert "main.py" in result.files_deleted

    def test_compare_versions_invalid_version(self, temp_project):
        manager = VersionManager(temp_project)

        manager.create_version(name="Version 1")

        with pytest.raises(ValueError):
            manager.compare_versions("v1", "nonexistent")

    def test_tag_version(self, temp_project):
        manager = VersionManager(temp_project)

        v1 = manager.create_version(name="Version 1")

        result = manager.tag_version(v1.version_id, "release")

        assert result is True
        assert "release" in manager.versions[v1.version_id].tags

    def test_tag_version_already_tagged(self, temp_project):
        manager = VersionManager(temp_project)

        v1 = manager.create_version(name="Version 1")
        manager.tag_version(v1.version_id, "release")

        result = manager.tag_version(v1.version_id, "release")

        assert result is True

    def test_untag_version(self, temp_project):
        manager = VersionManager(temp_project)

        v1 = manager.create_version(name="Version 1")
        manager.tag_version(v1.version_id, "release")

        result = manager.untag_version(v1.version_id, "release")

        assert result is True
        assert "release" not in manager.versions[v1.version_id].tags

    def test_find_versions_by_tag(self, temp_project):
        manager = VersionManager(temp_project)

        v1 = manager.create_version(name="Version 1")
        v2 = manager.create_version(name="Version 2")

        manager.tag_version(v1.version_id, "stable")

        results = manager.find_versions_by_tag("stable")

        assert len(results) == 1
        assert results[0]["version_id"] == v1.version_id

    def test_get_current_version(self, temp_project):
        manager = VersionManager(temp_project)

        v1 = manager.create_version(name="Version 1")
        v2 = manager.create_version(name="Version 2", auto_switch=False)

        current = manager.get_current_version()

        assert current is not None
        assert current["version_id"] == v1.version_id

    def test_get_current_version_none(self, temp_project):
        manager = VersionManager(temp_project)

        current = manager.get_current_version()

        assert current is None

    def test_auto_save_version(self, temp_project):
        manager = VersionManager(temp_project)

        snapshot = manager.auto_save_version(description="Auto save")

        assert snapshot is not None
        assert "自动保存" in snapshot.name

    def test_get_file_hash(self, temp_project):
        manager = VersionManager(temp_project)

        file_path = Path(temp_project) / "main.py"
        hash_value = manager._get_file_hash(file_path)

        assert len(hash_value) == 32

    def test_get_file_hash_nonexistent(self, temp_project):
        manager = VersionManager(temp_project)

        hash_value = manager._get_file_hash(Path(temp_project) / "nonexistent.txt")

        assert hash_value == ""

    def test_read_snapshot_file(self, temp_project):
        manager = VersionManager(temp_project)

        v1 = manager.create_version(name="Version 1")
        snapshot = manager.versions[v1.version_id]

        content = manager._read_snapshot_file(snapshot, "main.py")

        assert content is not None
        assert "hello" in content

    def test_read_snapshot_file_not_found(self, temp_project):
        manager = VersionManager(temp_project)

        v1 = manager.create_version(name="Version 1")
        snapshot = manager.versions[v1.version_id]

        content = manager._read_snapshot_file(snapshot, "nonexistent.txt")

        assert content is None

    def test_compute_diff(self, temp_project):
        manager = VersionManager(temp_project)

        diff_lines = manager._compute_diff("old content", "new content", "file.txt")

        assert len(diff_lines) > 0
        assert any("---" in line or "+++" in line for line in diff_lines)

    def test_persistence_across_instances(self, temp_project):
        manager1 = VersionManager(temp_project)
        manager1.create_version(name="Version 1")

        manager2 = VersionManager(temp_project)

        assert len(manager2.versions) == 1
        assert manager2.version_counter == 1
