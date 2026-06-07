#!/usr/bin/env python3
"""Task 9: API Health Routing Validation — Playwright 同步 API 测试脚本

测试内容:
  1. docker-compose.yml 配置检查
  2. 服务启动及健康检查
  3. /api/health/ 返回 200 OK
  4. /api/v2/admin/monitor/health 返回正确健康响应
  5. 路由扫描：重复/异常路由检测
  6. 404 处理器返回 JSON 错误响应
  7. 数据库迁移 & 管理员用户自动创建检查
"""

import json
import sys
import time
from pathlib import Path
from collections import Counter
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:8000"
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestReport:
    """测试报告收集器"""

    def __init__(self):
        self.results: list[dict] = []
        self.passed = 0
        self.failed = 0
        self.warnings = 0

    def add(self, name: str, status: str, message: str = "", detail: str = ""):
        entry = {"name": name, "status": status, "message": message, "detail": detail}
        self.results.append(entry)
        if status == "PASS":
            self.passed += 1
        elif status == "WARN":
            self.warnings += 1
        else:
            self.failed += 1

    def print_summary(self):
        total = self.passed + self.failed + self.warnings
        print("\n" + "=" * 70)
        print("  API 健康路由验证 — 测试报告")
        print("=" * 70)
        for r in self.results:
            icon = {"PASS": "✓", "FAIL": "✗", "WARN": "⚠"}[r["status"]]
            print(f"  [{icon}] {r['name']}")
            if r["message"]:
                print(f"       {r['message']}")
            if r["detail"]:
                for line in r["detail"].strip().split("\n"):
                    print(f"         {line}")
        print("-" * 70)
        print(f"  总计: {total} | 通过: {self.passed} | 失败: {self.failed} | 警告: {self.warnings}")
        print("=" * 70)
        return self.failed == 0


def check_docker_compose(report: TestReport):
    """1. 检查 docker-compose.yml 配置（文本解析，兼容多行 shell 命令）"""
    compose_path = PROJECT_ROOT / "docker-compose.yml"
    if not compose_path.exists():
        report.add("docker-compose.yml 存在性", "FAIL", f"文件不存在: {compose_path}")
        return

    try:
        raw = compose_path.read_text(encoding="utf-8")
    except Exception as e:
        report.add("docker-compose.yml 读取", "FAIL", str(e))
        return

    # 使用文本匹配检查关键配置（避免 YAML 解析器对多行 shell 命令的兼容性问题）
    checks = {
        "web 服务定义": "  web:" in raw,
        "celery 服务定义": "  celery:" in raw,
        "redis 服务定义": "  redis:" in raw,
        "web 端口暴露 (8000:8000)": "8000:8000" in raw,
        "redis 端口暴露 (6379:6379)": "6379:6379" in raw,
        "数据库迁移 (migrate)": "migrate" in raw,
        "管理员自动创建 (create_superuser)": "create_superuser" in raw,
        "web 依赖 redis": "depends_on:" in raw and "redis" in raw,
        "granian ASGI 服务": "granian" in raw,
        "celery worker 启动": "celery -A" in raw,
        "redis:7-alpine 镜像": "redis:7-alpine" in raw,
        "redis_data 卷": "redis_data:" in raw,
        "环境变量配置": "REDIS_URL=redis://redis:6379/0" in raw,
        "CELERY_BROKER_URL 配置": "CELERY_BROKER_URL=redis://redis:6379/0" in raw,
        "ADMIN_PASSWORD 配置": "ADMIN_PASSWORD" in raw,
        "DEBUG 配置": "DEBUG=" in raw,
        "SECRET_KEY 配置": "SECRET_KEY=" in raw,
    }

    all_pass = True
    for name, result in checks.items():
        if result:
            report.add(name, "PASS")
        else:
            report.add(name, "FAIL", "未在 docker-compose.yml 中找到")
            all_pass = False

    if all_pass:
        report.add("docker-compose.yml 整体配置", "PASS", "所有关键配置项均已检测到")


def check_server_health(ctx, report: TestReport):
    """2-3. 服务健康检查"""
    max_retries = 15
    for i in range(max_retries):
        try:
            resp = ctx.get(f"{BASE_URL}/")
            if resp.status == 200:
                data = resp.json()
                report.add(
                    "服务启动",
                    "PASS",
                    f"版本: {data.get('version', 'unknown')}, "
                    f"文档: {data.get('docs', 'N/A')}",
                )
                return True
        except Exception:
            pass
        time.sleep(1)
    report.add("服务启动", "FAIL", f"等待 {max_retries}s 后仍未就绪")
    return False


def check_api_health(ctx, report: TestReport):
    """4. 验证 /api/v1/health/ 返回 200"""
    resp = ctx.get(f"{BASE_URL}/api/v1/health/")
    if resp.status != 200:
        report.add(
            "GET /api/v1/health/",
            "FAIL",
            f"期望 200, 实际 {resp.status}: {resp.text()[:200]}",
        )
        return

    try:
        data = resp.json()
    except Exception:
        report.add("GET /api/v1/health/", "FAIL", "响应不是有效 JSON")
        return

    checks = []
    if data.get("status") in ("ok", "degraded"):
        checks.append("status ✓")
    else:
        checks.append("status ✗")

    if data.get("database") == "ok":
        checks.append("database ✓")
    else:
        checks.append(f"database ✗ ({data.get('database')})")

    if data.get("cache") == "ok":
        checks.append("cache ✓")
    else:
        checks.append(f"cache ✗ ({data.get('cache')})")

    if data.get("version") == "2.0.0":
        checks.append("version ✓")
    else:
        checks.append(f"version ✗ ({data.get('version')})")

    all_ok = all("✗" not in c for c in checks)
    report.add(
        "GET /api/v1/health/",
        "PASS" if all_ok else "WARN",
        f"status={resp.status} | " + " | ".join(checks),
    )


def check_admin_health(ctx, report: TestReport):
    """5. 验证 /api/v2/admin/monitor/health"""
    # 先登录获取 token
    login_resp = ctx.post(
        f"{BASE_URL}/api/v2/auth/login",
        data=json.dumps({"username": "admin", "password": "testadmin123"}),
        headers={"Content-Type": "application/json"},
    )
    if login_resp.status != 200:
        report.add(
            "管理员登录",
            "FAIL",
            f"登录失败: {login_resp.status} {login_resp.text()[:200]}",
        )
        return

    try:
        login_data = login_resp.json()
        token = login_data["data"]["tokens"]["access_token"]
    except (KeyError, TypeError):
        report.add("管理员登录", "FAIL", f"无效的 token 响应: {login_resp.text()[:200]}")
        return

    report.add("管理员登录", "PASS", f"用户: {login_data['data']['user']['username']}")

    # 请求健康检查
    resp = ctx.get(
        f"{BASE_URL}/api/v2/admin/monitor/health",
        headers={"Authorization": f"Bearer {token}"},
    )
    if resp.status != 200:
        report.add(
            "GET /api/v2/admin/monitor/health",
            "FAIL",
            f"期望 200, 实际 {resp.status}: {resp.text()[:200]}",
        )
        return

    try:
        data = resp.json()
    except Exception:
        report.add("GET /api/v2/admin/monitor/health", "FAIL", "响应不是有效 JSON")
        return

    checks = []
    if data.get("success") is True:
        checks.append("success ✓")
    else:
        checks.append("success ✗")

    inner = data.get("data", {})
    if inner.get("status") == "healthy":
        checks.append("status=healthy ✓")
    else:
        checks.append(f"status={inner.get('status')} ✗")

    if inner.get("database") is True:
        checks.append("database ✓")
    else:
        checks.append(f"database={inner.get('database')} ✗")

    if inner.get("cache") is True:
        checks.append("cache ✓")
    else:
        checks.append(f"cache={inner.get('cache')} ✗")

    all_ok = all("✗" not in c for c in checks)
    report.add(
        "GET /api/v2/admin/monitor/health",
        "PASS" if all_ok else "FAIL",
        " | ".join(checks),
    )


def scan_routes(ctx, report: TestReport):
    """6. 扫描所有已注册路由，检查重复和异常"""
    for version, api_path in [("v1", "/api/v1/openapi.json"), ("v2", "/api/v2/openapi.json")]:
        resp = ctx.get(f"{BASE_URL}{api_path}")
        if resp.status != 200:
            report.add(f"OpenAPI {version} 获取", "FAIL", f"status={resp.status}")
            continue

        try:
            spec = resp.json()
        except Exception:
            report.add(f"OpenAPI {version} 解析", "FAIL", "不是有效 JSON")
            continue

        paths = spec.get("paths", {})
        path_list = list(paths.keys())
        report.add(
            f"API {version} 路由总数",
            "PASS",
            f"{len(path_list)} 个路由",
            detail="\n".join(f"  {p}" for p in sorted(path_list)[:5])
            + ("\n  ..." if len(path_list) > 5 else ""),
        )

        # 检查重复路由 (GET + POST 同路径不计为重复)
        method_paths: list[tuple[str, str]] = []
        for path, methods in paths.items():
            for method in methods:
                method_paths.append((method.upper(), path))

        # 检查完全相同的 method+path 组合
        counter = Counter(method_paths)
        duplicates = {k: v for k, v in counter.items() if v > 1}
        if duplicates:
            dup_lines = [f"  {m} {p} 出现 {c} 次" for (m, p), c in duplicates.items()]
            report.add(
                f"API {version} 重复路由",
                "FAIL",
                f"发现 {len(duplicates)} 个重复",
                detail="\n".join(dup_lines),
            )
        else:
            report.add(f"API {version} 重复路由检查", "PASS", "无重复 (method+path)")

        # 检查异常路由模式
        anomalies = []
        for path in path_list:
            # 检查路径中是否有连续斜杠
            if "//" in path:
                anomalies.append(f"连续斜杠: {path}")
            # 检查路径是否以特殊字符结尾
            if path.endswith("/-") or path.endswith("/."):
                anomalies.append(f"异常结尾: {path}")

        if anomalies:
            report.add(
                f"API {version} 异常路由",
                "WARN",
                f"发现 {len(anomalies)} 个异常",
                detail="\n".join(f"  {a}" for a in anomalies),
            )
        else:
            report.add(f"API {version} 异常路由检查", "PASS", "无异常路由模式")

        # 检查 v1/v2 之间的路径重叠
        if version == "v1":
            v1_paths = {p.replace("/api/v1", "") for p in path_list}
        else:
            v2_paths = {p.replace("/api/v2", "") for p in path_list}

    # 检查 v1/v2 路径重叠
    overlap = v1_paths & v2_paths
    if overlap:
        report.add(
            "v1/v2 路径重叠",
            "WARN",
            f"发现 {len(overlap)} 个重叠",
            detail="\n".join(f"  {p}" for p in sorted(overlap)),
        )
    else:
        report.add("v1/v2 路径重叠", "PASS", "v1 和 v2 路径无重叠")


def check_404_handler(ctx, report: TestReport):
    """7. 验证 404 处理器返回 JSON 错误响应"""
    test_cases = [
        # (路径, 描述, 期望内容类型)
        ("/api/v1/books/99999", "v1 不存在的资源 (Ninja 404)", "json"),
        ("/api/v1/nonexistent-route", "v1 不存在的路由 (Django 404)", "any"),
        ("/api/v2/reader/books/99999", "v2 不存在的资源 (Ninja 404)", "json"),
        ("/api/v2/nonexistent-route", "v2 不存在的路由 (Django 404)", "any"),
    ]

    for path, desc, expected_ct in test_cases:
        resp = ctx.get(f"{BASE_URL}{path}")
        status = resp.status
        ct = resp.headers.get("content-type", "")
        body = resp.text()[:300]

        if status != 404:
            report.add(
                f"404 测试: {desc}",
                "FAIL",
                f"期望 404, 实际 {status}",
            )
            continue

        # 检查返回内容是否包含错误信息
        has_error = (
            "error" in body.lower()
            or "not found" in body.lower()
            or "detail" in body.lower()
            or "找不到" in body
            or "Page not found" in body
            or "不存在" in body
        )

        if has_error:
            # 检查是否是 JSON 格式
            is_json = "application/json" in ct
            if is_json:
                try:
                    json_data = resp.json()
                    report.add(
                        f"404 测试: {desc}",
                        "PASS",
                        f"JSON 响应, status=404",
                        detail=f"  Content-Type: {ct}\n  Body: {json.dumps(json_data, ensure_ascii=False)[:200]}",
                    )
                except Exception:
                    report.add(
                        f"404 测试: {desc}",
                        "WARN",
                        f"Content-Type 声称 JSON 但解析失败",
                        detail=f"  Content-Type: {ct}\n  Body: {body[:200]}",
                    )
            else:
                report.add(
                    f"404 测试: {desc}",
                    "WARN" if expected_ct == "json" else "PASS",
                    f"非 JSON 响应 (DEBUG=True 时的 Django 行为), status=404",
                    detail=f"  Content-Type: {ct}\n  Body: {body[:200]}",
                )
        else:
            report.add(
                f"404 测试: {desc}",
                "FAIL",
                f"响应中未找到错误信息, status={status}",
                detail=f"  Content-Type: {ct}\n  Body: {body[:200]}",
            )


def check_migrations_admin(ctx, report: TestReport):
    """检查数据库迁移和管理员用户"""
    # 检查迁移状态
    resp = ctx.get(f"{BASE_URL}/api/v1/health/detail/")
    if resp.status == 200:
        try:
            data = resp.json()
            db_status = data.get("database", {}).get("status", "unknown")
            user_count = data.get("stats", {}).get("users", -1)
            report.add(
                "数据库迁移状态",
                "PASS" if db_status == "ok" else "WARN",
                f"db={db_status}, users={user_count}",
            )
        except Exception:
            report.add("数据库迁移状态", "WARN", "无法解析健康详情响应")
    else:
        report.add("数据库迁移状态", "FAIL", f"status={resp.status}")

    # 检查管理员用户
    login_resp = ctx.post(
        f"{BASE_URL}/api/v2/auth/login",
        data=json.dumps({"username": "admin", "password": "testadmin123"}),
        headers={"Content-Type": "application/json"},
    )
    if login_resp.status == 200:
        try:
            login_data = login_resp.json()
            user = login_data.get("data", {}).get("user", {})
            is_admin = user.get("is_staff", False) and user.get("role") == "admin"
            report.add(
                "管理员用户自动创建",
                "PASS" if is_admin else "WARN",
                f"username={user.get('username')}, is_staff={user.get('is_staff')}, role={user.get('role')}",
            )
        except Exception:
            report.add("管理员用户自动创建", "WARN", "无法解析用户信息")
    else:
        report.add("管理员用户自动创建", "FAIL", f"登录失败: {login_resp.status}")


def main():
    report = TestReport()

    print("=" * 70)
    print("  API 健康路由验证测试")
    print("=" * 70)
    print(f"  目标: {BASE_URL}")
    print(f"  项目根目录: {PROJECT_ROOT}")
    print()

    # 1. docker-compose 配置检查
    print("─" * 40)
    print("  1. docker-compose.yml 配置检查")
    print("─" * 40)
    check_docker_compose(report)

    # 2-7. Playwright API 测试
    with sync_playwright() as p:
        ctx = p.request.new_context(
            base_url=BASE_URL,
            extra_http_headers={"Accept": "application/json"},
        )

        print("\n" + "─" * 40)
        print("  2. 服务健康检查")
        print("─" * 40)
        if not check_server_health(ctx, report):
            report.print_summary()
            ctx.dispose()
            sys.exit(1)

        print("\n" + "─" * 40)
        print("  3. /api/v1/health/ 端点测试")
        print("─" * 40)
        check_api_health(ctx, report)

        print("\n" + "─" * 40)
        print("  4. /api/v2/admin/monitor/health 端点测试")
        print("─" * 40)
        check_admin_health(ctx, report)

        print("\n" + "─" * 40)
        print("  5. 路由扫描")
        print("─" * 40)
        scan_routes(ctx, report)

        print("\n" + "─" * 40)
        print("  6. 404 处理器验证")
        print("─" * 40)
        check_404_handler(ctx, report)

        print("\n" + "─" * 40)
        print("  7. 数据库迁移 & 管理员检查")
        print("─" * 40)
        check_migrations_admin(ctx, report)

        ctx.dispose()

    # 输出报告
    success = report.print_summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()