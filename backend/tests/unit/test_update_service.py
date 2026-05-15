import pytest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.services.update_service import (
    UpdateEngine,
    AdaptiveUpdater,
    UpdateResult,
)


class TestUpdateResult:
    def test_update_result_to_dict(self):
        result = UpdateResult(
            success=True,
            message="Update completed",
            files_modified=["file1.txt"],
            files_created=["file2.txt"],
            files_deleted=["file3.txt"],
            backup_path="/backup/path",
            errors=[],
        )

        result_dict = result.to_dict()

        assert result_dict["success"] is True
        assert result_dict["message"] == "Update completed"
        assert result_dict["files_modified"] == ["file1.txt"]
        assert result_dict["files_created"] == ["file2.txt"]
        assert result_dict["files_deleted"] == ["file3.txt"]
        assert result_dict["backup_path"] == "/backup/path"

    def test_update_result_errors_default_empty(self):
        result = UpdateResult(
            success=True,
            message="No errors",
            files_modified=[],
            files_created=[],
            files_deleted=[],
        )

        assert result.errors == []


class TestUpdateEngine:
    @pytest.fixture
    def temp_project(self):
        temp_dir = tempfile.mkdtemp()
        project_root = Path(temp_dir) / "project"
        project_root.mkdir()

        (project_root / "existing.txt").write_text("original content")
        (project_root / "data").mkdir()

        yield str(project_root)

        shutil.rmtree(temp_dir)

    def test_engine_initialization(self, temp_project):
        engine = UpdateEngine(temp_project)

        assert engine.project_root == Path(temp_project).resolve()
        assert engine.backup_dir.exists()
        assert "updates" in engine.update_log

    def test_load_update_log_empty(self, temp_project):
        engine = UpdateEngine(temp_project)
        assert engine.update_log == {"updates": []}

    def test_load_update_log_existing(self, temp_project):
        log_path = Path(temp_project) / "data" / "update_log.json"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(json.dumps({
            "updates": [{"timestamp": "2024-01-01", "result": {"success": True}}]
        }))

        engine = UpdateEngine(temp_project)
        assert len(engine.update_log["updates"]) == 1

    def test_get_file_hash_existing(self, temp_project):
        engine = UpdateEngine(temp_project)
        file_path = Path(temp_project) / "existing.txt"

        hash1 = engine._get_file_hash(file_path)
        assert len(hash1) == 32

    def test_get_file_hash_nonexistent(self, temp_project):
        engine = UpdateEngine(temp_project)
        file_path = Path(temp_project) / "nonexistent.txt"

        assert engine._get_file_hash(file_path) == ""

    def test_update_file_create_new(self, temp_project):
        engine = UpdateEngine(temp_project)
        result = engine.update_file("new_file.txt", "new content")

        assert result is True
        assert (Path(temp_project) / "new_file.txt").read_text() == "new content"

    def test_update_file_overwrite_existing(self, temp_project):
        engine = UpdateEngine(temp_project)
        result = engine.update_file("existing.txt", "updated content")

        assert result is True
        assert (Path(temp_project) / "existing.txt").read_text() == "updated content"

    def test_update_file_not_exists_no_create(self, temp_project):
        engine = UpdateEngine(temp_project)
        result = engine.update_file("nonexistent.txt", "content", create_if_missing=False)

        assert result is False
        assert not (Path(temp_project) / "nonexistent.txt").exists()

    def test_patch_file_text_replace(self, temp_project):
        engine = UpdateEngine(temp_project)
        result = engine.patch_file(
            "existing.txt",
            "original",
            "modified"
        )

        assert result is True
        assert (Path(temp_project) / "existing.txt").read_text() == "modified content"

    def test_patch_file_no_match(self, temp_project):
        engine = UpdateEngine(temp_project)
        result = engine.patch_file(
            "existing.txt",
            "nonexistent_pattern",
            "replacement"
        )

        assert result is False
        assert (Path(temp_project) / "existing.txt").read_text() == "original content"

    def test_patch_file_regex(self, temp_project):
        engine = UpdateEngine(temp_project)
        (Path(temp_project) / "test.txt").write_text("item1 item2 item3")

        result = engine.patch_file(
            "test.txt",
            r"item\d",
            "REPLACED",
            is_regex=True
        )

        assert result is True
        content = (Path(temp_project) / "test.txt").read_text()
        assert "REPLACED" in content

    def test_delete_file(self, temp_project):
        engine = UpdateEngine(temp_project)
        result = engine.delete_file("existing.txt")

        assert result is True
        assert not (Path(temp_project) / "existing.txt").exists()

    def test_delete_file_nonexistent(self, temp_project):
        engine = UpdateEngine(temp_project)
        result = engine.delete_file("nonexistent.txt")

        assert result is False

    def test_delete_directory(self, temp_project):
        subdir = Path(temp_project) / "subdir"
        subdir.mkdir()
        (subdir / "file.txt").write_text("content")

        engine = UpdateEngine(temp_project)
        result = engine.delete_file("subdir")

        assert result is True
        assert not subdir.exists()

    def test_find_files_by_pattern(self, temp_project):
        (Path(temp_project) / "test_py.py").write_text("pass")
        (Path(temp_project) / "test_txt.txt").write_text("pass")
        (Path(temp_project) / "other.py").write_text("pass")

        engine = UpdateEngine(temp_project)
        results = engine._find_files_by_pattern("test", ".py")

        assert "test_py.py" in results

    def test_find_content_matches(self, temp_project):
        (Path(temp_project) / "file1.py").write_text("def hello():\n    pass")
        (Path(temp_project) / "file2.py").write_text("def world():\n    pass")

        engine = UpdateEngine(temp_project)
        results = engine._find_content_matches(r"def \w+\(\)")

        assert len(results) >= 1

    def test_create_backup(self, temp_project):
        engine = UpdateEngine(temp_project)
        backup_path = engine._create_backup(["existing.txt"])

        assert Path(backup_path).exists()
        assert (Path(backup_path) / "existing.txt").exists()
        assert (Path(backup_path) / "existing.txt").read_text() == "original content"

    def test_execute_update_plan_create(self, temp_project):
        engine = UpdateEngine(temp_project)
        plan = {
            "actions": [
                {"type": "create", "file": "new.txt", "content": "new content"}
            ]
        }

        result = engine.execute_update_plan(plan)

        assert result.success is True
        assert "new.txt" in result.files_created
        assert (Path(temp_project) / "new.txt").exists()

    def test_execute_update_plan_update(self, temp_project):
        engine = UpdateEngine(temp_project)
        plan = {
            "actions": [
                {"type": "update", "file": "existing.txt", "content": "updated"}
            ]
        }

        result = engine.execute_update_plan(plan)

        assert result.success is True
        assert "existing.txt" in result.files_modified

    def test_execute_update_plan_delete(self, temp_project):
        engine = UpdateEngine(temp_project)
        plan = {
            "actions": [
                {"type": "delete", "file": "existing.txt"}
            ]
        }

        result = engine.execute_update_plan(plan)

        assert result.success is True
        assert "existing.txt" in result.files_deleted

    def test_execute_update_plan_update_action_behavior(self, temp_project):
        engine = UpdateEngine(temp_project)

        result = engine.execute_update_plan({
            "actions": [
                {"type": "update", "file": "nonexistent.txt", "content": "content"}
            ]
        })

        assert result.success is True

    def test_execute_update_plan_with_backup(self, temp_project):
        engine = UpdateEngine(temp_project)
        plan = {
            "backup_files": ["existing.txt"],
            "actions": [
                {"type": "update", "file": "existing.txt", "content": "changed"}
            ]
        }

        result = engine.execute_update_plan(plan)

        assert result.backup_path is not None
        assert Path(result.backup_path).exists()

    def test_get_update_history(self, temp_project):
        engine = UpdateEngine(temp_project)
        engine.update_log["updates"].append({"timestamp": "2024-01-01"})

        history = engine.get_update_history()

        assert len(history) == 1

    def test_rollback_last_update_success(self, temp_project):
        engine = UpdateEngine(temp_project)
        engine.update_log["updates"].append({
            "result": {
                "backup_path": str(engine.backup_dir / "backup_20240101_000000")
            }
        })

        backup = engine.backup_dir / "backup_20240101_000000"
        backup.mkdir(parents=True, exist_ok=True)
        (backup / "existing.txt").write_text("original content")

        result = engine.rollback_last_update()

        assert result.success is True

    def test_rollback_no_updates(self, temp_project):
        engine = UpdateEngine(temp_project)
        result = engine.rollback_last_update()

        assert result.success is False
        assert "没有可回滚" in result.message

    def test_rollback_backup_not_exists(self, temp_project):
        engine = UpdateEngine(temp_project)
        engine.update_log["updates"].append({
            "result": {"backup_path": "/nonexistent/backup"}
        })

        result = engine.rollback_last_update()

        assert result.success is False
        assert "备份文件不存在" in result.message


class TestAdaptiveUpdater:
    @pytest.fixture
    def temp_project(self):
        temp_dir = tempfile.mkdtemp()
        project_root = Path(temp_dir) / "project"
        project_root.mkdir()
        (project_root / "backend").mkdir()
        (project_root / "frontend").mkdir()
        (project_root / "docker-compose.yml").write_text("")
        (project_root / "backend" / "requirements.txt").write_text("fastapi\nsqlalchemy")
        (project_root / "frontend" / "package.json").write_text('{"name": "app", "dependencies": {"vue": "^3.0.0"}}')

        yield str(project_root)

        shutil.rmtree(temp_dir)

    def test_detect_project_structure(self, temp_project):
        updater = AdaptiveUpdater(temp_project)
        structure = updater._detect_project_structure()

        assert structure["has_backend"] is True
        assert structure["has_frontend"] is True
        assert structure["has_docker"] is True
        assert structure["backend_framework"] == "fastapi"
        assert structure["frontend_framework"] is not None

    def test_generate_update_plan_add_model(self, temp_project):
        updater = AdaptiveUpdater(temp_project)
        plan = updater.generate_update_plan("添加模型 UserModel")

        assert "actions" in plan
        assert "detected_structure" in plan
        assert len(plan["actions"]) > 0

    def test_generate_update_plan_add_route(self, temp_project):
        updater = AdaptiveUpdater(temp_project)
        plan = updater.generate_update_plan("添加路由 api")

        assert "actions" in plan
        assert plan["actions"][0]["type"] == "create"

    def test_generate_update_plan_update_config(self, temp_project):
        updater = AdaptiveUpdater(temp_project)
        plan = updater.generate_update_plan("修改配置 setting")

        assert "actions" in plan

    def test_generate_update_plan_add_dependency(self, temp_project):
        updater = AdaptiveUpdater(temp_project)
        plan = updater.generate_update_plan("添加依赖 requests, aiohttp")

        assert len(plan["actions"]) > 0

    def test_generate_update_plan_fix_issue(self, temp_project):
        updater = AdaptiveUpdater(temp_project)
        plan = updater.generate_update_plan("修复 登录问题")

        assert "actions" in plan

    def test_generate_update_plan_unknown_instruction(self, temp_project):
        updater = AdaptiveUpdater(temp_project)
        plan = updater.generate_update_plan("do something random")

        assert len(plan["actions"]) == 1
        assert plan["actions"][0]["type"] == "info"

    def test_execute_instruction(self, temp_project):
        updater = AdaptiveUpdater(temp_project)
        result = updater.execute_instruction("添加依赖 pytest")

        assert isinstance(result, UpdateResult)
