import os
import re
import json
import shutil
import hashlib
import difflib
import logging
import fnmatch
from pathlib import PurePosixPath, Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class VersionStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    ROLLED_BACK = "rolled_back"


@dataclass
class VersionSnapshot:
    version_id: str
    name: str
    description: str
    timestamp: str
    status: VersionStatus
    files: List[str]
    file_hashes: Dict[str, str]
    snapshot_path: str
    parent_version: Optional[str] = None
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []

    def to_dict(self) -> Dict:
        return {
            "version_id": self.version_id,
            "name": self.name,
            "description": self.description,
            "timestamp": self.timestamp,
            "status": self.status.value,
            "files": self.files,
            "file_hashes": self.file_hashes,
            "snapshot_path": self.snapshot_path,
            "parent_version": self.parent_version,
            "tags": self.tags,
        }


@dataclass
class FileDiff:
    file_path: str
    old_hash: str
    new_hash: str
    old_content: Optional[str]
    new_content: Optional[str]
    diff_lines: List[str]
    change_type: str  # added, modified, deleted, unchanged

    def to_dict(self) -> Dict:
        return {
            "file_path": self.file_path,
            "old_hash": self.old_hash,
            "new_hash": self.new_hash,
            "diff_lines": self.diff_lines,
            "change_type": self.change_type,
        }


@dataclass
class VersionCompareResult:
    version_a: str
    version_b: str
    files_added: List[str]
    files_deleted: List[str]
    files_modified: List[str]
    files_unchanged: List[str]
    diffs: List[FileDiff]

    def to_dict(self) -> Dict:
        return {
            "version_a": self.version_a,
            "version_b": self.version_b,
            "files_added": self.files_added,
            "files_deleted": self.files_deleted,
            "files_modified": self.files_modified,
            "files_unchanged": self.files_unchanged,
            "diffs": [d.to_dict() for d in self.diffs],
        }


class VersionManager:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root).resolve()
        self.version_dir = self.project_root / "data" / "versions"
        self.version_db_path = self.project_root / "data" / "version_db.json"
        self.version_dir.mkdir(parents=True, exist_ok=True)
        self._load_version_db()

    def _load_version_db(self):
        if self.version_db_path.exists():
            try:
                with open(self.version_db_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.versions = {}
                    for vid, vdata in data.get("versions", {}).items():
                        vdata["status"] = VersionStatus(vdata["status"])
                        self.versions[vid] = VersionSnapshot(**vdata)
                    self.current_version = data.get("current_version")
                    self.version_counter = data.get("version_counter", 0)
            except Exception as e:
                logger.warning(f"版本数据库加载失败: {e}")
                self.versions = {}
                self.current_version = None
                self.version_counter = 0
        else:
            self.versions = {}
            self.current_version = None
            self.version_counter = 0

    def _save_version_db(self):
        self.version_db_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "versions": {vid: v.to_dict() for vid, v in self.versions.items()},
            "current_version": self.current_version,
            "version_counter": self.version_counter,
        }
        with open(self.version_db_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _generate_version_id(self) -> str:
        self.version_counter += 1
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"v{self.version_counter}_{timestamp}"

    def _get_file_hash(self, file_path: Path) -> str:
        if not file_path.exists():
            return ""
        with open(file_path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()

    def _collect_project_files(self, exclude_patterns: List[str] = None) -> List[Path]:
        if exclude_patterns is None:
            exclude_patterns = [
                ".git", "node_modules", "__pycache__", ".pytest_cache",
                "data/backups", "data/versions", "data/cache",
                "*.pyc", "*.pyo", ".DS_Store", "*.map"
            ]

        files = []
        for item in self.project_root.rglob("*"):
            if item.is_file():
                relative = str(PurePosixPath(item.relative_to(self.project_root)))
                should_exclude = False
                for pattern in exclude_patterns:
                    if fnmatch.fnmatch(relative, pattern) or fnmatch.fnmatch(item.name, pattern):
                        should_exclude = True
                        break
                    parts = Path(relative).parts
                    for part in parts:
                        if fnmatch.fnmatch(part, pattern):
                            should_exclude = True
                            break
                    if should_exclude:
                        break
                if not should_exclude:
                    files.append(item)
        return sorted(files)

    def create_version(
        self,
        name: str,
        description: str = "",
        tags: List[str] = None,
        auto_switch: bool = True,
    ) -> VersionSnapshot:
        version_id = self._generate_version_id()
        snapshot_path = self.version_dir / version_id
        snapshot_path.mkdir(parents=True, exist_ok=True)

        files = self._collect_project_files()
        file_hashes = {}
        copied_files = []

        for file_path in files:
            relative = str(file_path.relative_to(self.project_root))
            dst = snapshot_path / relative
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, dst)
            file_hashes[relative] = self._get_file_hash(file_path)
            copied_files.append(relative)

        snapshot = VersionSnapshot(
            version_id=version_id,
            name=name,
            description=description,
            timestamp=datetime.now().isoformat(),
            status=VersionStatus.ACTIVE,
            files=copied_files,
            file_hashes=file_hashes,
            snapshot_path=str(snapshot_path),
            parent_version=self.current_version,
            tags=tags or [],
        )

        self.versions[version_id] = snapshot

        if auto_switch:
            self.current_version = version_id

        self._save_version_db()

        logger.info(f"创建版本: {version_id} - {name}")
        return snapshot

    def switch_version(self, version_id: str) -> bool:
        if version_id not in self.versions:
            return False

        snapshot = self.versions[version_id]
        snapshot_path = Path(snapshot.snapshot_path)

        if not snapshot_path.exists():
            return False

        # 先创建当前状态的备份（防止丢失未保存的更改）
        current_backup = self.version_dir / f"_temp_before_switch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        current_files = self._collect_project_files()
        for file_path in current_files:
            relative = str(file_path.relative_to(self.project_root))
            dst = current_backup / relative
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, dst)

        # 恢复目标版本
        for relative_path in snapshot.files:
            src = snapshot_path / relative_path
            dst = self.project_root / relative_path
            if src.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)

        # 标记旧版本状态
        if self.current_version and self.current_version in self.versions:
            self.versions[self.current_version].status = VersionStatus.ARCHIVED

        self.current_version = version_id
        snapshot.status = VersionStatus.ACTIVE
        self._save_version_db()

        logger.info(f"切换到版本: {version_id}")
        return True

    def delete_version(self, version_id: str) -> bool:
        if version_id not in self.versions:
            return False

        snapshot = self.versions[version_id]
        snapshot_path = Path(snapshot.snapshot_path)

        if snapshot_path.exists():
            shutil.rmtree(snapshot_path)

        del self.versions[version_id]

        if self.current_version == version_id:
            self.current_version = None

        self._save_version_db()
        logger.info(f"删除版本: {version_id}")
        return True

    def list_versions(self) -> List[Dict]:
        result = []
        for vid in sorted(self.versions.keys(), reverse=True):
            v = self.versions[vid]
            result.append({
                "version_id": v.version_id,
                "name": v.name,
                "description": v.description,
                "timestamp": v.timestamp,
                "status": v.status.value,
                "is_current": vid == self.current_version,
                "file_count": len(v.files),
                "tags": v.tags,
            })
        return result

    def get_version_detail(self, version_id: str) -> Optional[Dict]:
        if version_id not in self.versions:
            return None
        v = self.versions[version_id]
        return {
            **v.to_dict(),
            "is_current": version_id == self.current_version,
        }

    def compare_versions(self, version_a: str, version_b: str) -> VersionCompareResult:
        if version_a not in self.versions or version_b not in self.versions:
            raise ValueError("版本不存在")

        va = self.versions[version_a]
        vb = self.versions[version_b]

        all_files = set(va.files) | set(vb.files)
        files_added = []
        files_deleted = []
        files_modified = []
        files_unchanged = []
        diffs = []

        for relative_path in sorted(all_files):
            in_a = relative_path in va.file_hashes
            in_b = relative_path in vb.file_hashes

            if in_a and not in_b:
                files_deleted.append(relative_path)
                diffs.append(FileDiff(
                    file_path=relative_path,
                    old_hash=va.file_hashes[relative_path],
                    new_hash="",
                    old_content=self._read_snapshot_file(va, relative_path),
                    new_content=None,
                    diff_lines=["文件已删除"],
                    change_type="deleted",
                ))
            elif not in_a and in_b:
                files_added.append(relative_path)
                diffs.append(FileDiff(
                    file_path=relative_path,
                    old_hash="",
                    new_hash=vb.file_hashes[relative_path],
                    old_content=None,
                    new_content=self._read_snapshot_file(vb, relative_path),
                    diff_lines=["文件已添加"],
                    change_type="added",
                ))
            elif va.file_hashes[relative_path] != vb.file_hashes[relative_path]:
                files_modified.append(relative_path)
                old_content = self._read_snapshot_file(va, relative_path) or ""
                new_content = self._read_snapshot_file(vb, relative_path) or ""
                diff_lines = self._compute_diff(old_content, new_content, relative_path)
                diffs.append(FileDiff(
                    file_path=relative_path,
                    old_hash=va.file_hashes[relative_path],
                    new_hash=vb.file_hashes[relative_path],
                    old_content=old_content,
                    new_content=new_content,
                    diff_lines=diff_lines,
                    change_type="modified",
                ))
            else:
                files_unchanged.append(relative_path)
                diffs.append(FileDiff(
                    file_path=relative_path,
                    old_hash=va.file_hashes[relative_path],
                    new_hash=vb.file_hashes[relative_path],
                    old_content=None,
                    new_content=None,
                    diff_lines=[],
                    change_type="unchanged",
                ))

        return VersionCompareResult(
            version_a=version_a,
            version_b=version_b,
            files_added=files_added,
            files_deleted=files_deleted,
            files_modified=files_modified,
            files_unchanged=files_unchanged,
            diffs=diffs,
        )

    def _read_snapshot_file(self, snapshot: VersionSnapshot, relative_path: str) -> Optional[str]:
        file_path = Path(snapshot.snapshot_path) / relative_path
        if not file_path.exists():
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return None

    def _compute_diff(self, old_content: str, new_content: str, file_path: str) -> List[str]:
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        if not old_lines:
            old_lines = [""]
        if not new_lines:
            new_lines = [""]

        diff = list(difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            lineterm="",
        ))

        return diff if diff else ["内容相同但哈希不同（可能是换行符差异）"]

    def tag_version(self, version_id: str, tag: str) -> bool:
        if version_id not in self.versions:
            return False
        if tag not in self.versions[version_id].tags:
            self.versions[version_id].tags.append(tag)
            self._save_version_db()
        return True

    def untag_version(self, version_id: str, tag: str) -> bool:
        if version_id not in self.versions:
            return False
        if tag in self.versions[version_id].tags:
            self.versions[version_id].tags.remove(tag)
            self._save_version_db()
        return True

    def find_versions_by_tag(self, tag: str) -> List[Dict]:
        result = []
        for vid, v in self.versions.items():
            if tag in v.tags:
                result.append({
                    "version_id": v.version_id,
                    "name": v.name,
                    "timestamp": v.timestamp,
                    "is_current": vid == self.current_version,
                })
        return result

    def get_current_version(self) -> Optional[Dict]:
        if not self.current_version or self.current_version not in self.versions:
            return None
        return self.get_version_detail(self.current_version)

    def auto_save_version(self, name: str = None, description: str = "") -> VersionSnapshot:
        if name is None:
            name = f"自动保存_{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        return self.create_version(name=name, description=description, auto_switch=True)


_project_root = os.environ.get("PROJECT_ROOT", "/workspace/novel-reader")
version_manager = VersionManager(_project_root)
