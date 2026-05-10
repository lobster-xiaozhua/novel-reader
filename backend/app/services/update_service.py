import os
import re
import json
import shutil
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class UpdateResult:
    success: bool
    message: str
    files_modified: List[str]
    files_created: List[str]
    files_deleted: List[str]
    backup_path: Optional[str] = None
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []

    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "message": self.message,
            "files_modified": self.files_modified,
            "files_created": self.files_created,
            "files_deleted": self.files_deleted,
            "backup_path": self.backup_path,
            "errors": self.errors,
        }


class UpdateEngine:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root).resolve()
        self.backup_dir = self.project_root / "data" / "backups"
        self.update_log_path = self.project_root / "data" / "update_log.json"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self._load_update_log()

    def _load_update_log(self):
        if self.update_log_path.exists():
            try:
                with open(self.update_log_path, "r", encoding="utf-8") as f:
                    self.update_log = json.load(f)
            except Exception:
                self.update_log = {"updates": []}
        else:
            self.update_log = {"updates": []}

    def _save_update_log(self):
        self.update_log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.update_log_path, "w", encoding="utf-8") as f:
            json.dump(self.update_log, f, ensure_ascii=False, indent=2)

    def _create_backup(self, files_to_backup: List[str]) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"backup_{timestamp}"
        backup_path.mkdir(parents=True, exist_ok=True)

        for file_path in files_to_backup:
            src = self.project_root / file_path
            if src.exists():
                dst = backup_path / file_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                if src.is_file():
                    shutil.copy2(src, dst)
                elif src.is_dir():
                    shutil.copytree(src, dst, dirs_exist_ok=True)

        return str(backup_path)

    def _restore_backup(self, backup_path: str):
        backup = Path(backup_path)
        if not backup.exists():
            raise FileNotFoundError(f"备份不存在: {backup_path}")

        for item in backup.rglob("*"):
            if item.is_file():
                relative_path = item.relative_to(backup)
                dst = self.project_root / relative_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dst)

    def _get_file_hash(self, file_path: Path) -> str:
        if not file_path.exists():
            return ""
        with open(file_path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()

    def _find_files_by_pattern(self, pattern: str, file_type: Optional[str] = None) -> List[str]:
        results = []
        regex = re.compile(pattern, re.IGNORECASE)

        for root, _, files in os.walk(self.project_root):
            root_path = Path(root)
            if ".git" in str(root_path) or "node_modules" in str(root_path) or "__pycache__" in str(root_path):
                continue

            for file in files:
                if file_type and not file.endswith(file_type):
                    continue
                file_path = root_path / file
                relative_path = str(file_path.relative_to(self.project_root))
                if regex.search(relative_path) or regex.search(file):
                    results.append(relative_path)

        return results

    def _find_content_matches(self, pattern: str, file_type: Optional[str] = None) -> List[Tuple[str, List[int]]]:
        results = []
        regex = re.compile(pattern, re.MULTILINE | re.DOTALL)

        for root, _, files in os.walk(self.project_root):
            root_path = Path(root)
            if ".git" in str(root_path) or "node_modules" in str(root_path) or "__pycache__" in str(root_path):
                continue

            for file in files:
                if file_type and not file.endswith(file_type):
                    continue
                file_path = root_path / file
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    matches = list(regex.finditer(content))
                    if matches:
                        lines = [content[:m.start()].count("\n") + 1 for m in matches]
                        relative_path = str(file_path.relative_to(self.project_root))
                        results.append((relative_path, lines))
                except Exception:
                    continue

        return results

    def update_file(self, file_path: str, new_content: str, create_if_missing: bool = True) -> bool:
        target = self.project_root / file_path
        if not target.exists() and not create_if_missing:
            return False

        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(new_content)
        return True

    def patch_file(self, file_path: str, old_pattern: str, new_content: str, is_regex: bool = False) -> bool:
        target = self.project_root / file_path
        if not target.exists():
            return False

        with open(target, "r", encoding="utf-8") as f:
            content = f.read()

        if is_regex:
            new_text = re.sub(old_pattern, new_content, content, flags=re.MULTILINE | re.DOTALL)
        else:
            new_text = content.replace(old_pattern, new_content)

        if new_text == content:
            return False

        with open(target, "w", encoding="utf-8") as f:
            f.write(new_text)
        return True

    def delete_file(self, file_path: str) -> bool:
        target = self.project_root / file_path
        if target.exists():
            if target.is_file():
                target.unlink()
            elif target.is_dir():
                shutil.rmtree(target)
            return True
        return False

    def execute_update_plan(self, plan: Dict[str, Any]) -> UpdateResult:
        files_modified = []
        files_created = []
        files_deleted = []
        errors = []

        files_to_backup = plan.get("backup_files", [])
        backup_path = None

        try:
            if files_to_backup:
                backup_path = self._create_backup(files_to_backup)

            for action in plan.get("actions", []):
                action_type = action.get("type")
                file_path = action.get("file")

                try:
                    if action_type == "create":
                        content = action.get("content", "")
                        if self.update_file(file_path, content, create_if_missing=True):
                            files_created.append(file_path)

                    elif action_type == "update":
                        content = action.get("content")
                        if content is not None:
                            if self.update_file(file_path, content, create_if_missing=False):
                                files_modified.append(file_path)

                    elif action_type == "patch":
                        old_pattern = action.get("old")
                        new_content = action.get("new", "")
                        is_regex = action.get("regex", False)
                        if self.patch_file(file_path, old_pattern, new_content, is_regex):
                            files_modified.append(file_path)

                    elif action_type == "delete":
                        if self.delete_file(file_path):
                            files_deleted.append(file_path)

                    elif action_type == "append":
                        target = self.project_root / file_path
                        if target.exists():
                            content = action.get("content", "")
                            with open(target, "a", encoding="utf-8") as f:
                                f.write(content)
                            files_modified.append(file_path)

                except Exception as e:
                    errors.append(f"{file_path}: {str(e)}")

            result = UpdateResult(
                success=len(errors) == 0,
                message="更新完成" if not errors else f"更新完成，但有 {len(errors)} 个错误",
                files_modified=files_modified,
                files_created=files_created,
                files_deleted=files_deleted,
                backup_path=backup_path,
                errors=errors,
            )

            self.update_log["updates"].append({
                "timestamp": datetime.now().isoformat(),
                "result": result.to_dict(),
                "plan": plan,
            })
            self._save_update_log()

            return result

        except Exception as e:
            if backup_path:
                try:
                    self._restore_backup(backup_path)
                    errors.append(f"更新失败，已恢复备份: {str(e)}")
                except Exception as restore_error:
                    errors.append(f"更新失败，备份恢复也失败: {str(e)}, 恢复错误: {str(restore_error)}")

            return UpdateResult(
                success=False,
                message=f"更新失败: {str(e)}",
                files_modified=[],
                files_created=[],
                files_deleted=[],
                backup_path=backup_path,
                errors=errors,
            )

    def get_update_history(self) -> List[Dict]:
        return self.update_log.get("updates", [])

    def rollback_last_update(self) -> UpdateResult:
        if not self.update_log["updates"]:
            return UpdateResult(
                success=False,
                message="没有可回滚的更新",
                files_modified=[],
                files_created=[],
                files_deleted=[],
            )

        last_update = self.update_log["updates"][-1]
        backup_path = last_update.get("result", {}).get("backup_path")

        if not backup_path or not Path(backup_path).exists():
            return UpdateResult(
                success=False,
                message="备份文件不存在，无法回滚",
                files_modified=[],
                files_created=[],
                files_deleted=[],
            )

        try:
            self._restore_backup(backup_path)
            self.update_log["updates"].pop()
            self._save_update_log()

            return UpdateResult(
                success=True,
                message="已回滚到上一个版本",
                files_modified=[],
                files_created=[],
                files_deleted=[],
            )
        except Exception as e:
            return UpdateResult(
                success=False,
                message=f"回滚失败: {str(e)}",
                files_modified=[],
                files_created=[],
                files_deleted=[],
            )


class AdaptiveUpdater:
    def __init__(self, project_root: str):
        self.engine = UpdateEngine(project_root)
        self.project_root = Path(project_root)

    def _detect_project_structure(self) -> Dict[str, Any]:
        structure = {
            "has_backend": (self.project_root / "backend").exists(),
            "has_frontend": (self.project_root / "frontend").exists(),
            "has_docker": (self.project_root / "docker-compose.yml").exists(),
            "backend_framework": None,
            "frontend_framework": None,
            "python_version": None,
            "node_version": None,
        }

        if structure["has_backend"]:
            req_file = self.project_root / "backend" / "requirements.txt"
            if req_file.exists():
                content = req_file.read_text(encoding="utf-8")
                if "fastapi" in content.lower():
                    structure["backend_framework"] = "fastapi"
                elif "flask" in content.lower():
                    structure["backend_framework"] = "flask"
                elif "django" in content.lower():
                    structure["backend_framework"] = "django"

        if structure["has_frontend"]:
            pkg_file = self.project_root / "frontend" / "package.json"
            if pkg_file.exists():
                content = pkg_file.read_text(encoding="utf-8")
                if "vue" in content.lower():
                    structure["frontend_framework"] = "vue"
                elif "react" in content.lower():
                    structure["frontend_framework"] = "react"
                elif "angular" in content.lower():
                    structure["frontend_framework"] = "angular"

        return structure

    def generate_update_plan(self, instruction: str) -> Dict[str, Any]:
        structure = self._detect_project_structure()
        plan = {
            "instruction": instruction,
            "detected_structure": structure,
            "backup_files": [],
            "actions": [],
        }

        instruction_lower = instruction.lower()

        if "添加模型" in instruction_lower or "add model" in instruction_lower:
            plan["actions"].extend(self._plan_add_model(instruction, structure))

        elif "添加api" in instruction_lower or "add api" in instruction_lower:
            plan["actions"].extend(self._plan_add_api(instruction, structure))

        elif "添加路由" in instruction_lower or "add route" in instruction_lower:
            plan["actions"].extend(self._plan_add_route(instruction, structure))

        elif "修改配置" in instruction_lower or "update config" in instruction_lower:
            plan["actions"].extend(self._plan_update_config(instruction, structure))

        elif "添加依赖" in instruction_lower or "add dependency" in instruction_lower:
            plan["actions"].extend(self._plan_add_dependency(instruction, structure))

        elif "修复" in instruction_lower or "fix" in instruction_lower:
            plan["actions"].extend(self._plan_fix_issue(instruction, structure))

        else:
            plan["actions"].append({
                "type": "info",
                "message": f"未识别的指令类型: {instruction}。请使用更具体的描述。"
            })

        auto_backup = self._determine_backup_files(plan["actions"])
        plan["backup_files"] = auto_backup

        return plan

    def _determine_backup_files(self, actions: List[Dict]) -> List[str]:
        files = set()
        for action in actions:
            if "file" in action:
                files.add(action["file"])
        return list(files)

    def _plan_add_route(self, instruction: str, structure: Dict) -> List[Dict]:
        actions = []
        framework = structure.get("backend_framework")

        if framework == "fastapi":
            router_file = "backend/app/api/new_feature.py"
            actions.append({
                "type": "create",
                "file": router_file,
                "content": self._generate_fastapi_router_template(instruction),
            })
            actions.append({
                "type": "patch",
                "file": "backend/main.py",
                "old": "from app.api import auth, books",
                "new": "from app.api import auth, books, new_feature",
            })

        return actions

    def _plan_add_model(self, instruction: str, structure: Dict) -> List[Dict]:
        actions = []
        model_name = self._extract_entity_name(instruction) or "NewModel"

        actions.append({
            "type": "create",
            "file": f"backend/app/models/{model_name.lower()}.py",
            "content": self._generate_model_template(model_name),
        })

        init_file = "backend/app/models/__init__.py"
        if (self.project_root / init_file).exists():
            actions.append({
                "type": "append",
                "file": init_file,
                "content": f"\nfrom .{model_name.lower()} import {model_name}\n",
            })

        return actions

    def _plan_add_api(self, instruction: str, structure: Dict) -> List[Dict]:
        actions = []
        api_name = self._extract_entity_name(instruction) or "new"

        actions.append({
            "type": "create",
            "file": f"backend/app/api/{api_name.lower()}.py",
            "content": self._generate_api_template(api_name),
        })

        return actions

    def _plan_update_config(self, instruction: str, structure: Dict) -> List[Dict]:
        actions = []

        if structure.get("has_backend"):
            actions.append({
                "type": "patch",
                "file": "backend/app/core/config.py",
                "old": "    # 性能配置",
                "new": "    # 新增配置\n    NEW_FEATURE_ENABLED: bool = True\n\n    # 性能配置",
            })

        return actions

    def _plan_add_dependency(self, instruction: str, structure: Dict) -> List[Dict]:
        actions = []
        packages = self._extract_package_names(instruction)

        for pkg in packages:
            actions.append({
                "type": "append",
                "file": "backend/requirements.txt",
                "content": f"{pkg}\n",
            })

        return actions

    def _plan_fix_issue(self, instruction: str, structure: Dict) -> List[Dict]:
        actions = []

        matches = self.engine._find_content_matches(r"TODO|FIXME|XXX", ".py")
        for file_path, lines in matches[:3]:
            actions.append({
                "type": "info",
                "message": f"发现待修复代码: {file_path} 第 {lines} 行",
            })

        return actions

    def _extract_entity_name(self, instruction: str) -> Optional[str]:
        patterns = [
            r"添加(?:模型|model|API|api|路由|route)\s+(\w+)",
            r"add\s+(?:model|api|route)\s+(\w+)",
            r"create\s+(\w+)\s+(?:model|api|route)",
        ]
        for pattern in patterns:
            match = re.search(pattern, instruction, re.IGNORECASE)
            if match:
                return match.group(1).capitalize()
        return None

    def _extract_package_names(self, instruction: str) -> List[str]:
        patterns = [
            r"添加依赖\s+(.+)",
            r"add\s+dependenc(?:y|ies)\s+(.+)",
            r"install\s+(.+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, instruction, re.IGNORECASE)
            if match:
                return [p.strip() for p in match.group(1).split(",")]
        return []

    def _generate_fastapi_router_template(self, instruction: str) -> str:
        return '''from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.security import get_current_user

router = APIRouter(prefix="/new-feature", tags=["新功能"])


@router.get("")
async def list_items(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """获取列表"""
    return {"message": "功能开发中"}


@router.post("")
async def create_item(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """创建项目"""
    return {"message": "功能开发中"}
'''

    def _generate_model_template(self, model_name: str) -> str:
        return f'''from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class {model_name}(Base):
    __tablename__ = "{model_name.lower()}s"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<{model_name}(id={{self.id}}, name={{self.name}})>"
'''

    def _generate_api_template(self, api_name: str) -> str:
        return f'''from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.database import get_db
from app.core.security import get_current_user

router = APIRouter(prefix="/{api_name.lower()}", tags=["{api_name}"])


@router.get("")
async def get_{api_name.lower()}_list(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """获取{{api_name}}列表"""
    return {{"items": [], "total": 0, "skip": skip, "limit": limit}}


@router.get("/{{item_id}}")
async def get_{api_name.lower()}_detail(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """获取{{api_name}}详情"""
    return {{"id": item_id, "message": "功能开发中"}}


@router.post("")
async def create_{api_name.lower()}(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """创建{{api_name}}"""
    return {{"message": "功能开发中"}}


@router.put("/{{item_id}}")
async def update_{api_name.lower()}(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """更新{{api_name}}"""
    return {{"id": item_id, "message": "功能开发中"}}


@router.delete("/{{item_id}}")
async def delete_{api_name.lower()}(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """删除{{api_name}}"""
    return {{"id": item_id, "message": "已删除"}}
'''

    def execute_instruction(self, instruction: str) -> UpdateResult:
        plan = self.generate_update_plan(instruction)
        return self.engine.execute_update_plan(plan)


_project_root = os.environ.get("PROJECT_ROOT", "/workspace/novel-reader")
update_service = AdaptiveUpdater(_project_root)
