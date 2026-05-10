import importlib
import logging
import os
import socket
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from app.core.config import get_settings
from app.core.terminal_compat import terminal_compat
from app.core.safe_logger import get_safe_logger

logger = get_safe_logger(__name__)
settings = get_settings()


@dataclass
class CheckResult:
    name: str
    passed: bool
    message: str
    severity: str = "error"
    skipped: bool = False
    details: Optional[str] = None


@dataclass
class StartupReport:
    checks: List[CheckResult] = field(default_factory=list)
    warnings: int = 0
    errors: int = 0
    skipped: int = 0

    @property
    def healthy(self) -> bool:
        return self.errors == 0

    def add(self, result: CheckResult):
        self.checks.append(result)
        if result.skipped:
            self.skipped += 1
        elif not result.passed:
            if result.severity == "error":
                self.errors += 1
            elif result.severity == "warning":
                self.warnings += 1

    def to_dict(self) -> dict:
        return {
            "healthy": self.healthy,
            "errors": self.errors,
            "warnings": self.warnings,
            "skipped": self.skipped,
            "checks": [
                {
                    "name": c.name,
                    "passed": c.passed,
                    "message": c.message,
                    "severity": c.severity,
                    "skipped": c.skipped,
                }
                for c in self.checks
            ],
        }

    def print_report(self):
        sym = terminal_compat.sym
        tc = terminal_compat

        tc.safe_print(f"\n{'=' * 55}")
        tc.safe_print(f"  {sym('🚀')} Novel Reader 启动自检报告")
        tc.safe_print(f"{'=' * 55}")

        for check in self.checks:
            if check.skipped:
                status = f"{sym('⚠️')} 跳过"
            elif check.passed:
                status = f"{sym('✅')} 通过"
            else:
                status = f"{sym('❌')} 失败" if check.severity == "error" else f"{sym('⚠️')} 警告"

            tc.safe_print(f"  {status}  {check.name}: {check.message}")

        tc.safe_print(f"{'=' * 55}")
        summary_parts = []
        if self.errors:
            summary_parts.append(f"{self.errors} 个错误")
        if self.warnings:
            summary_parts.append(f"{self.warnings} 个警告")
        if self.skipped:
            summary_parts.append(f"{self.skipped} 项跳过")

        if self.healthy:
            tc.safe_print(f"  {sym('✅')} 系统自检通过" + (f" ({', '.join(summary_parts)})" if summary_parts else ""))
        else:
            tc.safe_print(f"  {sym('❌')} 系统自检未通过: {', '.join(summary_parts)}")
        tc.safe_print(f"{'=' * 55}\n")


class StartupCheck:
    REQUIRED_PACKAGES = [
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
        ("sqlalchemy", "sqlalchemy"),
        ("aiosqlite", "aiosqlite"),
        ("redis", "redis"),
        ("pydantic", "pydantic"),
        ("pydantic_settings", "pydantic-settings"),
        ("jose", "python-jose"),
        ("passlib", "passlib"),
        ("aiohttp", "aiohttp"),
        ("bs4", "beautifulsoup4"),
        ("tenacity", "tenacity"),
    ]

    OPTIONAL_PACKAGES = [
        ("psutil", "psutil"),
        ("magic", "python-magic"),
    ]

    def __init__(self):
        self.report = StartupReport()
        self._is_container = terminal_compat.is_container
        self._is_ci = terminal_compat.is_ci

    async def run_all(self) -> StartupReport:
        self._check_encoding()
        self._check_dependencies()
        self._check_config()
        await self._check_database()
        await self._check_redis()
        self._check_directories()
        self._check_port()
        self._check_secret_key()

        self.report.print_report()
        return self.report

    def _check_encoding(self):
        tc = terminal_compat
        try:
            encoding = tc.encoding
            utf8 = tc.supports_utf8
            emoji = tc.supports_emoji

            if utf8:
                self.report.add(CheckResult(
                    name="终端编码",
                    passed=True,
                    message=f"编码: {encoding}, UTF-8: 是, Emoji: {'是' if emoji else '否'}",
                ))
            else:
                self.report.add(CheckResult(
                    name="终端编码",
                    passed=True,
                    message=f"编码: {encoding}, UTF-8: 否 (已启用兼容模式)",
                    severity="warning",
                ))
        except Exception as e:
            self.report.add(CheckResult(
                name="终端编码",
                passed=True,
                message=f"编码检测失败: {e}, 使用兼容模式",
                severity="warning",
            ))

    def _check_dependencies(self):
        missing_required = []
        missing_optional = []

        for module_name, package_name in self.REQUIRED_PACKAGES:
            try:
                importlib.import_module(module_name)
            except ImportError:
                missing_required.append(package_name)

        for module_name, package_name in self.OPTIONAL_PACKAGES:
            try:
                importlib.import_module(module_name)
            except ImportError:
                missing_optional.append(package_name)

        if missing_required:
            self.report.add(CheckResult(
                name="依赖完整性",
                passed=False,
                message=f"缺少必需依赖: {', '.join(missing_required)}",
                severity="error",
            ))
        else:
            msg = "所有必需依赖已安装"
            if missing_optional:
                msg += f" (可选依赖缺失: {', '.join(missing_optional)})"
                self.report.add(CheckResult(name="依赖完整性", passed=True, message=msg, severity="warning"))
            else:
                self.report.add(CheckResult(name="依赖完整性", passed=True, message=msg))

    def _check_config(self):
        try:
            s = get_settings()
            issues = []

            if s.SECRET_KEY == "your-secret-key-here-change-in-production":
                issues.append("SECRET_KEY 使用默认值")

            if not s.DATABASE_URL:
                issues.append("DATABASE_URL 未配置")

            if issues:
                self.report.add(CheckResult(
                    name="配置文件",
                    passed=len(issues) == 0 or all("默认值" in i for i in issues),
                    message="; ".join(issues),
                    severity="warning" if any("默认值" in i for i in issues) else "error",
                ))
            else:
                self.report.add(CheckResult(
                    name="配置文件",
                    passed=True,
                    message="配置文件有效",
                ))
        except Exception as e:
            self.report.add(CheckResult(
                name="配置文件",
                passed=False,
                message=f"配置加载失败: {e}",
                severity="error",
            ))

    async def _check_database(self):
        try:
            from app.database import engine
            from sqlalchemy import text

            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))

            db_path = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "")
            self.report.add(CheckResult(
                name="数据库连接",
                passed=True,
                message=f"SQLite 连接正常 ({db_path})",
            ))
        except Exception as e:
            self.report.add(CheckResult(
                name="数据库连接",
                passed=False,
                message=f"数据库连接失败: {e}",
                severity="error",
                details=str(e),
            ))

    async def _check_redis(self):
        if self._is_container or self._is_ci:
            try:
                import redis.asyncio as redis
                r = redis.from_url(settings.REDIS_URL, socket_connect_timeout=3)
                await r.ping()
                await r.close()
                self.report.add(CheckResult(
                    name="Redis连接",
                    passed=True,
                    message=f"Redis 连接正常 ({settings.REDIS_URL})",
                ))
            except Exception:
                self.report.add(CheckResult(
                    name="Redis连接",
                    passed=True,
                    message="Redis 不可用，将降级为无缓存模式",
                    severity="warning",
                    skipped=True,
                ))
        else:
            try:
                import redis.asyncio as redis
                r = redis.from_url(settings.REDIS_URL, socket_connect_timeout=5)
                await r.ping()
                await r.close()
                self.report.add(CheckResult(
                    name="Redis连接",
                    passed=True,
                    message=f"Redis 连接正常 ({settings.REDIS_URL})",
                ))
            except Exception as e:
                self.report.add(CheckResult(
                    name="Redis连接",
                    passed=True,
                    message=f"Redis 连接失败，将降级为无缓存模式: {e}",
                    severity="warning",
                ))

    def _check_directories(self):
        dirs_to_check = {
            "BOOKS_DIR": settings.BOOKS_DIR,
            "LOGS_DIR": settings.LOGS_DIR,
            "INDEX_DIR": settings.INDEX_DIR,
            "STATIC_DIR": settings.STATIC_DIR,
        }

        for name, dir_path in dirs_to_check.items():
            path = Path(dir_path)

            if not path.exists():
                try:
                    path.mkdir(parents=True, exist_ok=True)
                    self.report.add(CheckResult(
                        name=f"目录权限({name})",
                        passed=True,
                        message=f"已自动创建: {dir_path}",
                    ))
                except OSError as e:
                    self.report.add(CheckResult(
                        name=f"目录权限({name})",
                        passed=False,
                        message=f"无法创建目录 {dir_path}: {e}",
                        severity="error",
                    ))
                continue

            if not os.access(dir_path, os.W_OK):
                self.report.add(CheckResult(
                    name=f"目录权限({name})",
                    passed=False,
                    message=f"目录无写入权限: {dir_path}",
                    severity="error",
                ))
            else:
                test_file = path / ".write_test"
                try:
                    test_file.write_text("test", encoding="utf-8")
                    test_file.unlink()
                    self.report.add(CheckResult(
                        name=f"目录权限({name})",
                        passed=True,
                        message=f"可读写: {dir_path}",
                    ))
                except OSError as e:
                    self.report.add(CheckResult(
                        name=f"目录权限({name})",
                        passed=False,
                        message=f"写入测试失败 {dir_path}: {e}",
                        severity="error",
                    ))

    def _check_port(self):
        if self._is_ci:
            self.report.add(CheckResult(
                name="端口检查",
                passed=True,
                message="CI 环境跳过端口检查",
                skipped=True,
            ))
            return

        host = "0.0.0.0"
        port = 8000

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2)
                result = s.connect_ex((host, port))
                if result == 0:
                    self.report.add(CheckResult(
                        name="端口检查",
                        passed=False,
                        message=f"端口 {port} 已被占用",
                        severity="warning",
                    ))
                else:
                    self.report.add(CheckResult(
                        name="端口检查",
                        passed=True,
                        message=f"端口 {port} 可用",
                    ))
        except OSError as e:
            self.report.add(CheckResult(
                name="端口检查",
                passed=True,
                message=f"端口检查跳过: {e}",
                skipped=True,
            ))

    def _check_secret_key(self):
        key = settings.SECRET_KEY
        insecure_defaults = {
            "your-secret-key-here-change-in-production",
            "change-me-in-production",
            "",
        }
        if key in insecure_defaults:
            import secrets
            new_key = secrets.token_urlsafe(32)
            settings.SECRET_KEY = new_key
            self.report.add(CheckResult(
                name="安全密钥",
                passed=False,
                message="SECRET_KEY 未配置或使用默认值，已自动生成安全密钥（建议通过环境变量显式设置）",
                severity="error",
            ))
        elif len(key) < 32:
            self.report.add(CheckResult(
                name="安全密钥",
                passed=True,
                message=f"SECRET_KEY 长度不足 ({len(key)} 字符)，建议至少 32 位",
                severity="warning",
            ))
        else:
            self.report.add(CheckResult(
                name="安全密钥",
                passed=True,
                message="SECRET_KEY 配置正常",
            ))


startup_check = StartupCheck()
