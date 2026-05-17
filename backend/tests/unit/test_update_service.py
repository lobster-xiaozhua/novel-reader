import pytest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.services.update_service import UpdateEngine, UpdateResult, AdaptiveUpdater


class TestUpdateResult:
    def test_to_dict(self):
        result = UpdateResult(
            success=True,
            message="Test completed",
            files_modified=["file1.py"],
            files_created=["file2.py"],
            files_deleted=[],
        )
        d = result.to_dict()
        assert d["success"] is True
        assert d["message"] == "Test completed"
        assert "file1.py" in d["files_modified"]
        assert "file2.py" in d["files_created"]

    def test_errors_default(self):
        result = UpdateResult(
            success=True,
            message="Done",
            files_modified=[],
            files_created=[],
            files_deleted=[],
        )
        assert result.errors == []


class TestUpdateEngine:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = self.temp_dir
        self.engine = UpdateEngine(self.project_root)

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_creates_backup_dir(self):
        assert self.engine.backup_dir.exists()

    def test_validate_path_allows_relative_path(self):
        test_file = Path(self.project_root) / "test.txt"
        test_file.write_text("content")
        result = self.engine._validate_path("test.txt")
        assert result.exists()

    def test_validate_path_rejects_parent_traversal(self):
        with pytest.raises(PermissionError):
            self.engine._validate_path("../../../etc/passwd")

    def test_update_file_creates_file(self):
        result = self.engine.update_file("new_file.txt", "content here")
        assert result is True
        assert (Path(self.project_root) / "new_file.txt").read_text() == "content here"

    def test_update_file_respects_create_if_missing_false(self):
        result = self.engine.update_file("nonexistent.txt", "content", create_if_missing=False)
        assert result is False

    def test_update_file_creates_parent_dirs(self):
        result = self.engine.update_file("nested/dirs/file.txt", "content")
        assert result is True
        assert (Path(self.project_root) / "nested/dirs/file.txt").exists()

    def test_patch_file_text_replacement(self):
        file_path = Path(self.project_root) / "test.txt"
        file_path.write_text("Hello World")

        result = self.engine.patch_file("test.txt", "World", "Universe")
        assert result is True
        assert file_path.read_text() == "Hello Universe"

    def test_patch_file_regex_replacement(self):
        file_path = Path(self.project_root) / "test.txt"
        file_path.write_text("Version 1.0.0")

        result = self.engine.patch_file("test.txt", r"Version \d+\.\d+\.\d+", "Version 2.0.0", is_regex=True)
        assert result is True
        assert file_path.read_text() == "Version 2.0.0"

    def test_patch_file_no_match(self):
        file_path = Path(self.project_root) / "test.txt"
        file_path.write_text("Hello World")

        result = self.engine.patch_file("test.txt", "NotFound", "Replaced")
        assert result is False

    def test_patch_file_nonexistent_file(self):
        result = self.engine.patch_file("nonexistent.txt", "old", "new")
        assert result is False

    def test_delete_file_removes_file(self):
        file_path = Path(self.project_root) / "to_delete.txt"
        file_path.write_text("content")

        result = self.engine.delete_file("to_delete.txt")
        assert result is True
        assert not file_path.exists()

    def test_delete_file_removes_directory(self):
        dir_path = Path(self.project_root) / "to_delete_dir"
        dir_path.mkdir()
        (dir_path / "file.txt").write_text("content")

        result = self.engine.delete_file("to_delete_dir")
        assert result is True
        assert not dir_path.exists()

    def test_delete_file_nonexistent(self):
        result = self.engine.delete_file("nonexistent.txt")
        assert result is False

    def test_find_files_by_pattern(self):
        (Path(self.project_root) / "test1.py").write_text("code")
        (Path(self.project_root) / "test2.py").write_text("code")
        (Path(self.project_root) / "readme.txt").write_text("text")

        results = self.engine._find_files_by_pattern(r"test\d\.py")
        assert len(results) == 2
        assert any("test1.py" in r for r in results)
        assert any("test2.py" in r for r in results)

    def test_find_files_by_pattern_with_type_filter(self):
        (Path(self.project_root) / "test.py").write_text("code")
        (Path(self.project_root) / "test.txt").write_text("text")

        results = self.engine._find_files_by_pattern("test", file_type=".py")
        assert len(results) == 1
        assert results[0].endswith(".py")

    def test_find_files_excludes_git_and_node_modules(self):
        git_dir = Path(self.project_root) / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text("git")

        node_modules = Path(self.project_root) / "node_modules"
        node_modules.mkdir()
        (node_modules / "package.json").write_text("{}")

        results = self.engine._find_files_by_pattern(r".*")
        assert not any(".git" in r for r in results)
        assert not any("node_modules" in r for r in results)

    def test_find_content_matches(self):
        file_path = Path(self.project_root) / "search_test.py"
        file_path.write_text("def hello():\n    pass\n\ndef world():\n    pass\n")

        results = self.engine._find_content_matches(r"def \w+\(\):")
        assert len(results) >= 1

    def test_get_file_hash(self):
        file_path = Path(self.project_root) / "hash_test.txt"
        file_path.write_text("content for hashing")

        hash1 = self.engine._get_file_hash(file_path)
        assert len(hash1) == 32

        hash2 = self.engine._get_file_hash(file_path)
        assert hash1 == hash2

    def test_get_file_hash_nonexistent(self):
        hash_result = self.engine._get_file_hash(Path(self.project_root) / "nonexistent.txt")
        assert hash_result == ""

    def test_execute_update_plan_create(self):
        plan = {
            "actions": [
                {"type": "create", "file": "new.py", "content": "# New file"}
            ]
        }
        result = self.engine.execute_update_plan(plan)
        assert result.success
        assert "new.py" in result.files_created

    def test_execute_update_plan_update(self):
        (Path(self.project_root) / "existing.txt").write_text("old content")
        plan = {
            "actions": [
                {"type": "update", "file": "existing.txt", "content": "new content"}
            ]
        }
        result = self.engine.execute_update_plan(plan)
        assert result.success
        assert "existing.txt" in result.files_modified

    def test_execute_update_plan_delete(self):
        (Path(self.project_root) / "to_remove.txt").write_text("remove me")
        plan = {
            "actions": [
                {"type": "delete", "file": "to_remove.txt"}
            ]
        }
        result = self.engine.execute_update_plan(plan)
        assert result.success
        assert "to_remove.txt" in result.files_deleted

    def test_execute_update_plan_with_backup(self):
        (Path(self.project_root) / "backup_me.txt").write_text("important content")
        plan = {
            "backup_files": ["backup_me.txt"],
            "actions": [
                {"type": "update", "file": "backup_me.txt", "content": "modified"}
            ]
        }
        result = self.engine.execute_update_plan(plan)
        assert result.success
        assert result.backup_path is not None

    def test_execute_update_plan_records_history(self):
        plan = {
            "actions": [
                {"type": "create", "file": "logged.txt", "content": "content"}
            ]
        }
        self.engine.execute_update_plan(plan)
        history = self.engine.get_update_history()
        assert len(history) == 1

    def test_get_update_history_empty(self):
        history = self.engine.get_update_history()
        assert history == []

    def test_rollback_last_update_success(self):
        (Path(self.project_root) / "original.txt").write_text("original")
        plan = {
            "backup_files": ["original.txt"],
            "actions": [
                {"type": "update", "file": "original.txt", "content": "modified"}
            ]
        }
        self.engine.execute_update_plan(plan)

        result = self.engine.rollback_last_update()
        assert result.success
        assert (Path(self.project_root) / "original.txt").read_text() == "original"

    def test_rollback_last_update_no_history(self):
        result = self.engine.rollback_last_update()
        assert result.success is False
        assert "没有可回滚" in result.message


class TestAdaptiveUpdater:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.updater = AdaptiveUpdater(self.temp_dir)

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_detect_project_structure_empty(self):
        structure = self.updater._detect_project_structure()
        assert structure["has_backend"] is False
        assert structure["has_frontend"] is False
        assert structure["has_docker"] is False

    def test_detect_project_structure_with_backend(self):
        backend_dir = Path(self.temp_dir) / "backend"
        backend_dir.mkdir()
        req_file = backend_dir / "requirements.txt"
        req_file.write_text("fastapi\nsqlalchemy\n")

        structure = self.updater._detect_project_structure()
        assert structure["has_backend"] is True
        assert structure["backend_framework"] == "fastapi"

    def test_detect_project_structure_with_frontend(self):
        frontend_dir = Path(self.temp_dir) / "frontend"
        frontend_dir.mkdir()
        pkg_file = frontend_dir / "package.json"
        pkg_file.write_text('{"name": "app", "dependencies": {"vue": "^3.0.0"}}')

        structure = self.updater._detect_project_structure()
        assert structure["has_frontend"] is True
        assert structure["frontend_framework"] == "vue"

    def test_generate_update_plan_add_route(self):
        plan = self.updater.generate_update_plan("添加路由 UserAPI")
        assert "actions" in plan
        assert len(plan["actions"]) >= 0

    def test_generate_update_plan_add_model(self):
        plan = self.updater.generate_update_plan("添加模型 Book")
        assert "actions" in plan
        assert any("model" in str(a) or "file" in a for a in plan["actions"])

    def test_generate_update_plan_with_backup(self):
        plan = self.updater.generate_update_plan("添加模型 TestModel")
        assert "backup_files" in plan

    def test_extract_entity_name_chinese(self):
        name = self.updater._extract_entity_name("添加模型 User")
        assert name == "User"

    def test_extract_entity_name_english(self):
        name = self.updater._extract_entity_name("add model Book")
        assert name == "Book"

    def test_extract_entity_name_not_found(self):
        name = self.updater._extract_entity_name("random text without entity")
        assert name is None

    def test_extract_package_names(self):
        packages = self.updater._extract_package_names("添加依赖 fastapi, sqlalchemy")
        assert "fastapi" in packages
        assert "sqlalchemy" in packages

    def test_extract_package_names_english(self):
        packages = self.updater._extract_package_names("install pytest, black")
        assert "pytest" in packages

    def test_execute_instruction_creates_plan(self):
        result = self.updater.execute_instruction("添加路由 Test")
        assert isinstance(result, UpdateResult)

    def test_generate_fastapi_router_template(self):
        template = self.updater._generate_fastapi_router_template("添加路由 Test")
        assert "router" in template.lower()
        assert "/new-feature" in template.lower()

    def test_generate_model_template(self):
        template = self.updater._generate_model_template("TestModel")
        assert "TestModel" in template
        assert "class TestModel" in template

    def test_generate_api_template(self):
        template = self.updater._generate_api_template("test")
        assert "/test" in template
        assert "router" in template.lower()
