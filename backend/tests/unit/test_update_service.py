import pytest
import json
import tempfile
import shutil
from pathlib import Path

from app.services.update_service import UpdateEngine, UpdateResult, AdaptiveUpdater


class TestUpdateResult:
    def test_update_result_to_dict(self):
        result = UpdateResult(
            success=True,
            message="Test completed",
            files_modified=["file1.py"],
            files_created=["file2.py"],
            files_deleted=[],
            backup_path="/tmp/backup",
            errors=[]
        )
        d = result.to_dict()
        assert d["success"] is True
        assert d["message"] == "Test completed"
        assert "file1.py" in d["files_modified"]

    def test_update_result_errors_default_empty(self):
        result = UpdateResult(
            success=True,
            message="Done",
            files_modified=[],
            files_created=[],
            files_deleted=[]
        )
        assert result.errors == []


class TestUpdateEngine:
    @pytest.fixture
    def temp_project_root(self):
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def update_engine(self, temp_project_root):
        return UpdateEngine(str(temp_project_root))

    def test_engine_initialization(self, update_engine, temp_project_root):
        assert update_engine.project_root == temp_project_root.resolve()
        assert update_engine.backup_dir.exists()
        assert "updates" in update_engine.update_log

    def test_update_file_creates_file(self, update_engine, temp_project_root):
        result = update_engine.update_file("new_file.txt", "Hello World")
        assert result is True
        assert (temp_project_root / "new_file.txt").exists()
        assert (temp_project_root / "new_file.txt").read_text() == "Hello World"

    def test_update_file_skips_when_missing_and_flag_off(self, update_engine):
        result = update_engine.update_file("missing.txt", "content", create_if_missing=False)
        assert result is False

    def test_patch_file_with_simple_replace(self, update_engine, temp_project_root):
        test_file = temp_project_root / "test.txt"
        test_file.write_text("old content here")
        result = update_engine.patch_file("test.txt", "old content", "new content")
        assert result is True
        assert "new content" in test_file.read_text()
        assert "old content" not in test_file.read_text()

    def test_patch_file_with_regex(self, update_engine, temp_project_root):
        test_file = temp_project_root / "test.txt"
        test_file.write_text("item_1\nitem_2\nitem_3")
        result = update_engine.patch_file("test.txt", r"item_\d+", "NEW_ITEM", is_regex=True)
        assert result is True
        content = test_file.read_text()
        assert "NEW_ITEM" in content
        assert "item_1" not in content

    def test_patch_file_no_match_returns_false(self, update_engine, temp_project_root):
        test_file = temp_project_root / "test.txt"
        test_file.write_text("unchanged content")
        result = update_engine.patch_file("test.txt", "nonexistent", "replacement")
        assert result is False

    def test_delete_file_removes_file(self, update_engine, temp_project_root):
        test_file = temp_project_root / "to_delete.txt"
        test_file.write_text("content")
        assert test_file.exists()
        result = update_engine.delete_file("to_delete.txt")
        assert result is True
        assert not test_file.exists()

    def test_delete_file_returns_false_for_missing(self, update_engine):
        result = update_engine.delete_file("nonexistent.txt")
        assert result is False

    def test_create_backup_preserves_structure(self, update_engine, temp_project_root):
        test_file = temp_project_root / "subdir" / "file.txt"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("important content")
        backup_path = update_engine._create_backup(["subdir/file.txt"])
        assert Path(backup_path).exists()
        assert (Path(backup_path) / "subdir/file.txt").exists()

    def test_get_file_hash(self, update_engine, temp_project_root):
        test_file = temp_project_root / "hashme.txt"
        test_file.write_text("content for hashing")
        hash1 = update_engine._get_file_hash(test_file)
        assert len(hash1) == 32
        assert hash1 == update_engine._get_file_hash(test_file)

    def test_get_file_hash_empty_for_missing(self, update_engine):
        result = update_engine._get_file_hash(Path("/nonexistent/file.txt"))
        assert result == ""

    def test_find_files_by_pattern(self, update_engine, temp_project_root):
        (temp_project_root / "main.py").write_text("code")
        (temp_project_root / "utils.py").write_text("code")
        (temp_project_root / "data.txt").write_text("data")
        results = update_engine._find_files_by_pattern(r"\.py$", file_type=".py")
        assert len(results) == 2
        assert any("main.py" in r for r in results)

    def test_execute_update_plan_with_create_action(self, update_engine, temp_project_root):
        plan = {
            "backup_files": [],
            "actions": [
                {"type": "create", "file": "new_feature.py", "content": "# New feature"}
            ]
        }
        result = update_engine.execute_update_plan(plan)
        assert result.success is True
        assert "new_feature.py" in result.files_created
        assert (temp_project_root / "new_feature.py").exists()

    def test_execute_update_plan_with_update_action(self, update_engine, temp_project_root):
        existing = temp_project_root / "existing.txt"
        existing.write_text("old content")
        plan = {
            "backup_files": [],
            "actions": [
                {"type": "update", "file": "existing.txt", "content": "new content"}
            ]
        }
        result = update_engine.execute_update_plan(plan)
        assert result.success is True
        assert existing.read_text() == "new content"

    def test_execute_update_plan_with_delete_action(self, update_engine, temp_project_root):
        to_delete = temp_project_root / "delete_me.txt"
        to_delete.write_text("remove this")
        plan = {
            "backup_files": [],
            "actions": [
                {"type": "delete", "file": "delete_me.txt"}
            ]
        }
        result = update_engine.execute_update_plan(plan)
        assert result.success is True
        assert not to_delete.exists()

    def test_execute_update_plan_records_in_log(self, update_engine, temp_project_root):
        plan = {
            "backup_files": [],
            "actions": [
                {"type": "create", "file": "logged.txt", "content": "data"}
            ]
        }
        update_engine.execute_update_plan(plan)
        assert len(update_engine.update_log["updates"]) == 1
        assert update_engine.update_log_path.exists()

    def test_rollback_last_update_restores_files(self, update_engine, temp_project_root):
        original = temp_project_root / "original.txt"
        original.write_text("version 1")
        plan = {
            "backup_files": ["original.txt"],
            "actions": [
                {"type": "update", "file": "original.txt", "content": "version 2"}
            ]
        }
        update_engine.execute_update_plan(plan)
        result = update_engine.rollback_last_update()
        assert result.success is True
        assert original.read_text() == "version 1"

    def test_rollback_with_no_updates_returns_error(self, update_engine):
        result = update_engine.rollback_last_update()
        assert result.success is False
        assert "没有可回滚" in result.message

    def test_get_update_history(self, update_engine, temp_project_root):
        for i in range(3):
            plan = {"backup_files": [], "actions": [{"type": "create", "file": f"f{i}.txt", "content": ""}]}
            update_engine.execute_update_plan(plan)
        history = update_engine.get_update_history()
        assert len(history) == 3


class TestAdaptiveUpdater:
    @pytest.fixture
    def temp_project_root(self):
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def adaptive_updater(self, temp_project_root):
        updater = AdaptiveUpdater(str(temp_project_root))
        updater.project_root = temp_project_root
        return updater

    def test_detect_project_structure_fastapi(self, adaptive_updater, temp_project_root):
        backend_dir = temp_project_root / "backend"
        backend_dir.mkdir()
        req_file = backend_dir / "requirements.txt"
        req_file.write_text("fastapi\nuvicorn")
        structure = adaptive_updater._detect_project_structure()
        assert structure["has_backend"] is True
        assert structure["backend_framework"] == "fastapi"

    def test_detect_project_structure_no_backend(self, adaptive_updater, temp_project_root):
        structure = adaptive_updater._detect_project_structure()
        assert structure["has_backend"] is False
        assert structure["backend_framework"] is None

    def test_extract_entity_name_from_chinese(self, adaptive_updater):
        name = adaptive_updater._extract_entity_name("添加模型 User")
        assert name == "User"

    def test_extract_entity_name_from_english(self, adaptive_updater):
        name = adaptive_updater._extract_entity_name("add model Book")
        assert name == "Book"

    def test_extract_package_names(self, adaptive_updater):
        packages = adaptive_updater._extract_package_names("添加依赖 requests, pandas")
        assert "requests" in packages
        assert "pandas" in packages

    def test_generate_update_plan_for_add_model(self, adaptive_updater, temp_project_root):
        (temp_project_root / "backend").mkdir()
        plan = adaptive_updater.generate_update_plan("添加模型 Book")
        assert "actions" in plan
        assert len(plan["actions"]) > 0

    def test_generate_update_plan_unrecognized_instruction(self, adaptive_updater, temp_project_root):
        (temp_project_root / "backend").mkdir()
        plan = adaptive_updater.generate_update_plan("do something random")
        assert any(a.get("type") == "info" for a in plan["actions"])

    def test_execute_instruction_creates_plan_and_executes(self, adaptive_updater, temp_project_root):
        (temp_project_root / "backend").mkdir()
        (temp_project_root / "backend" / "app").mkdir()
        (temp_project_root / "backend" / "app" / "models").mkdir()
        init_file = temp_project_root / "backend" / "app" / "models" / "__init__.py"
        init_file.write_text("")
        result = adaptive_updater.execute_instruction("添加模型 TestModel")
        assert isinstance(result, UpdateResult)
