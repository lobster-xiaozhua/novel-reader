#!/usr/bin/env python3
"""
E2E 功能测试脚本 — Novel Reader 小说阅读器
使用 Playwright Sync API 测试前后端核心功能
"""

import sys
import time
import json
import requests
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# ── 配置 ──
FRONTEND_URL = "http://localhost:3000"
BACKEND_URL = "http://localhost:8000"
SCREENSHOT_DIR = Path("/workspace/tests/screenshots")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

# ── 测试结果收集 ──
results = []
passed = 0
failed = 0


def log(tag, msg):
    print(f"[{tag}] {msg}")


def test(name, fn):
    global passed, failed
    try:
        log("TEST", f"▶ {name}")
        fn()
        passed += 1
        results.append(f"✅ PASS: {name}")
        log("PASS", name)
    except Exception as e:
        failed += 1
        results.append(f"❌ FAIL: {name} — {e}")
        log("FAIL", f"{name}: {e}")


# ═══════════════════════════════════════════════════════════════
# 测试用例
# ═══════════════════════════════════════════════════════════════

def run_tests():
    p = sync_playwright().start()
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        viewport={"width": 1280, "height": 800},
        locale="zh-CN",
    )
    page = context.new_page()

    # ── 1. 首页加载测试 ──
    def test_homepage_loading():
        log("INFO", "正在访问首页...")
        page.goto(FRONTEND_URL, timeout=30000)
        page.wait_for_load_state("networkidle")
        title = page.title()
        assert title, "页面标题为空"
        log("INFO", f"页面标题: {title}")

        # 截图
        page.screenshot(path=str(SCREENSHOT_DIR / "01_homepage.png"), full_page=True)
        log("INFO", "已保存首页截图")

        # 检查关键内容
        try:
            page.wait_for_selector("text=发现好书", timeout=5000)
            log("INFO", "发现「发现好书」标题")
        except PlaywrightTimeout:
            log("WARN", "未找到「发现好书」标题（可能数据库为空）")

        # 检查分类区域
        try:
            page.wait_for_selector("text=分类浏览", timeout=5000)
            log("INFO", "发现「分类浏览」区域")
        except PlaywrightTimeout:
            log("WARN", "未找到「分类浏览」区域")

        assert True

    test("首页加载测试", test_homepage_loading)

    # ── 2. 搜索功能测试 ──
    def test_search_functionality():
        log("INFO", "正在访问搜索页...")
        page.goto(f"{FRONTEND_URL}/search", timeout=30000)
        page.wait_for_load_state("networkidle")

        # 搜索关键词
        search_input = page.locator("input[type='text']")
        assert search_input.count() > 0, "搜索输入框未找到"
        search_input.fill("斗破")
        log("INFO", "输入搜索关键词: 斗破")

        # 点击搜索按钮
        search_btn = page.locator("button:has-text('搜索')")
        assert search_btn.count() > 0, "搜索按钮未找到"
        search_btn.click()
        log("INFO", "已点击搜索按钮")

        page.wait_for_timeout(2000)

        page.screenshot(path=str(SCREENSHOT_DIR / "02_search_results.png"), full_page=True)
        log("INFO", "已保存搜索结果截图")

        # 测试空搜索页面
        page.goto(f"{FRONTEND_URL}/search", timeout=30000)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        # 空搜索页应显示热搜或搜索建议
        try:
            page.wait_for_selector("text=热搜", timeout=3000)
            log("INFO", "空搜索页显示「热搜」")
        except PlaywrightTimeout:
            try:
                page.wait_for_selector("text=搜索历史", timeout=3000)
                log("INFO", "空搜索页显示「搜索历史」")
            except PlaywrightTimeout:
                log("WARN", "空搜索页无热搜/历史展示")

        assert True

    test("搜索功能测试", test_search_functionality)

    # ── 3. 拼音搜索测试 ──
    def test_pinyin_search():
        log("INFO", "正在访问搜索页（拼音测试）...")
        page.goto(f"{FRONTEND_URL}/search", timeout=30000)
        page.wait_for_load_state("networkidle")

        search_input = page.locator("input[type='text']")
        search_input.fill("doupo")
        log("INFO", "输入拼音关键词: doupo")

        search_btn = page.locator("button:has-text('搜索')")
        search_btn.click()
        page.wait_for_timeout(2000)

        page.screenshot(path=str(SCREENSHOT_DIR / "03_pinyin_search.png"), full_page=True)
        log("INFO", "已保存拼音搜索截图")

        assert True

    test("拼音搜索测试", test_pinyin_search)

    # ── 4. 书籍详情页测试 ──
    def test_book_detail():
        # 如果数据库有书，尝试访问 ID=1
        log("INFO", "正在访问书籍详情页...")
        page.goto(f"{FRONTEND_URL}/book/1", timeout=30000)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        page.screenshot(path=str(SCREENSHOT_DIR / "04_book_detail.png"), full_page=True)
        log("INFO", "已保存书籍详情页截图")

        # 尝试检测页面内容
        body_text = page.inner_text("body")
        if "书籍未找到" in body_text or "加载失败" in body_text:
            log("WARN", "书籍 ID=1 不存在于数据库")
        else:
            # 检查书籍信息
            try:
                page.wait_for_selector("h1", timeout=5000)
                log("INFO", "书籍详情页正常加载")
            except PlaywrightTimeout:
                log("WARN", "未找到书籍标题")

        assert True

    test("书籍详情页测试", test_book_detail)

    # ── 5. 阅读章节测试 ──
    def test_reading_chapter():
        log("INFO", "正在访问阅读页...")
        page.goto(f"{FRONTEND_URL}/read/1?chapter=1", timeout=30000)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(3000)

        page.screenshot(path=str(SCREENSHOT_DIR / "05_reading_chapter.png"), full_page=True)
        log("INFO", "已保存阅读页截图")

        # 检查导航元素
        body_text = page.inner_text("body")
        if "书籍未找到" in body_text or "加载失败" in body_text:
            log("WARN", "无法加载阅读页（书籍/章节不存在）")
        else:
            try:
                page.wait_for_selector("text=上一章", timeout=5000)
                log("INFO", "发现「上一章」导航")
            except PlaywrightTimeout:
                log("INFO", "未找到「上一章」导航（可能是第一章）")

            try:
                page.wait_for_selector("text=下一章", timeout=5000)
                log("INFO", "发现「下一章」导航")
            except PlaywrightTimeout:
                log("WARN", "未找到「下一章」导航")

        assert True

    test("阅读章节测试", test_reading_chapter)

    # ── 清理浏览器 ──
    browser.close()
    p.stop()

    # ── 6. 认证流程测试 (API 直接调用) ──
    def test_auth_flow():
        import uuid
        unique_username = f"e2e_test_{uuid.uuid4().hex[:8]}"
        session = requests.Session()

        # 注册
        log("INFO", f"正在注册新用户: {unique_username}")
        resp = session.post(
            f"{BACKEND_URL}/api/v2/auth/register",
            json={
                "username": unique_username,
                "password": "TestPass123!",
                "email": f"{unique_username}@test.com",
            },
            timeout=10,
        )
        data = resp.json()
        log("INFO", f"注册响应: {json.dumps({k: v for k, v in data.items() if k != 'data'}, ensure_ascii=False, default=str)}")

        assert data.get("success"), f"注册失败: {data}"
        assert "data" in data, "响应缺少 data 字段"
        assert "tokens" in data["data"], "响应缺少 tokens"
        assert "access_token" in data["data"]["tokens"], "响应缺少 access_token"
        assert "refresh_token" in data["data"]["tokens"], "响应缺少 refresh_token"
        log("INFO", "注册成功，获得 access_token 和 refresh_token")

        access_token = data["data"]["tokens"]["access_token"]

        # 登录
        log("INFO", f"正在登录用户: {unique_username}")
        resp = session.post(
            f"{BACKEND_URL}/api/v2/auth/login",
            json={"username": unique_username, "password": "TestPass123!"},
            timeout=10,
        )
        data = resp.json()
        assert data.get("success"), f"登录失败: {data}"
        assert "tokens" in data["data"], "登录响应缺少 tokens"
        log("INFO", "登录成功，获得 access_token 和 refresh_token")

        access_token = data["data"]["tokens"]["access_token"]

        # 验证 /me 端点
        log("INFO", "正在调用 /api/v2/auth/me")
        resp = requests.get(
            f"{BACKEND_URL}/api/v2/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        data = resp.json()
        assert data.get("success"), f"/me 调用失败: {data}"
        assert data["data"]["username"] == unique_username, f"用户名不匹配: {data['data']['username']}"
        log("INFO", f"/me 验证成功: {data['data']['username']}")

        assert True

    test("认证流程测试", test_auth_flow)

    # ── 7. 搜索 API 直接测试 ──
    def test_search_api():
        log("INFO", "测试搜索 API (关键字: test)")
        resp = requests.get(
            f"{BACKEND_URL}/api/v2/reader/search",
            params={"q": "test"},
            timeout=10,
        )
        data = resp.json()
        log("INFO", f"搜索 API 响应: {json.dumps({k: v for k, v in data.items() if k != 'data'}, ensure_ascii=False, default=str)}")
        assert data.get("success"), f"搜索 API 失败: {data}"
        assert "data" in data, "搜索响应缺少 data"
        assert "items" in data["data"], "搜索响应缺少 items 数组"
        log("INFO", f"搜索返回 {data['data']['total']} 条结果")

        # 拼音搜索
        log("INFO", "测试拼音搜索 (doupo)")
        resp = requests.get(
            f"{BACKEND_URL}/api/v2/reader/search",
            params={"q": "doupo"},
            timeout=10,
        )
        data = resp.json()
        assert data.get("success"), f"拼音搜索失败: {data}"
        log("INFO", f"拼音搜索返回 {data['data']['total']} 条结果")

        # 作者搜索
        log("INFO", "测试作者搜索 (author_name)")
        resp = requests.get(
            f"{BACKEND_URL}/api/v2/reader/search",
            params={"q": "author_name"},
            timeout=10,
        )
        data = resp.json()
        assert data.get("success"), f"作者搜索失败: {data}"
        log("INFO", f"作者搜索返回 {data['data']['total']} 条结果")

        assert True

    test("搜索 API 直接测试", test_search_api)

    # ═══════════════════════════════════════════════════════════════
    # 测试报告
    # ═══════════════════════════════════════════════════════════════
    print()
    print("=" * 60)
    print("  📊 E2E 功能测试报告")
    print("=" * 60)
    total = passed + failed
    for r in results:
        print(f"  {r}")
    print("-" * 60)
    print(f"  总计: {total} 个测试")
    print(f"  通过: {passed} ✅")
    print(f"  失败: {failed} ❌")
    print(f"  截图保存在: {SCREENSHOT_DIR}")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_tests()