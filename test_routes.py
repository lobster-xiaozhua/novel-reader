#!/usr/bin/env python3
"""全路由测试脚本"""
import requests
import json
import sys

BASE = "http://localhost:8000"
RESULTS = []
PASS = 0
FAIL = 0


def test(method, path, data=None, expected_code=200, auth=None, desc="", cookies=None):
    global PASS, FAIL
    url = f"{BASE}{path}"
    headers = {"Content-Type": "application/json"}
    try:
        if method == "GET":
            r = requests.get(url, params=data, headers=headers, cookies=cookies, timeout=5)
        elif method == "POST":
            r = requests.post(url, json=data, headers=headers, cookies=cookies, timeout=5)
        elif method == "DELETE":
            r = requests.delete(url, headers=headers, cookies=cookies, timeout=5)
        else:
            r = requests.request(method, url, json=data, headers=headers, cookies=cookies, timeout=5)

        code = r.status_code
        body = r.text[:150] if r.text else ""

        if code == expected_code:
            status = "✅ PASS"
            PASS += 1
        else:
            status = "❌ FAIL"
            FAIL += 1

        print(f"  {status} [{code}] {method} {path}")
        print(f"         期望: {expected_code} | 实际: {code} | {desc}")
        if code != expected_code:
            print(f"         Body: {body}")
        RESULTS.append({"path": path, "method": method, "expected": expected_code, "actual": code, "ok": code == expected_code})
    except requests.exceptions.ConnectionError:
        print(f"  ❌ FAIL [连接失败] {method} {path} - 服务未启动")
        FAIL += 1
        RESULTS.append({"path": path, "method": method, "expected": expected_code, "actual": "CONN_ERR", "ok": False})
    except Exception as e:
        print(f"  ❌ FAIL [异常] {method} {path} - {e}")
        FAIL += 1
        RESULTS.append({"path": path, "method": method, "expected": expected_code, "actual": str(e), "ok": False})


def section(name):
    print(f"\n{'━' * 50}")
    print(f"  {name}")
    print('━' * 50)


def main():
    global PASS, FAIL

    print("=" * 50)
    print("  Novel Reader 全路由测试")
    print("=" * 50)

    # Test 1: Health
    section("[1] Health Check (无需认证)")
    test("GET", "/api/v1/health/", desc="健康检查", expected_code=200)

    # Test 2: Auth (no auth needed)
    section("[2] 认证 API (无需认证)")
    test("POST", "/api/v1/auth/login/", {"username": "admin", "password": "wrong"}, desc="登录-错误密码→返回success:false", expected_code=200)
    test("POST", "/api/v1/auth/login/", {"username": "notexist", "password": "test"}, desc="登录-不存在的用户", expected_code=200)
    test("POST", "/api/v1/auth/register/", {"username": "testuser99", "password": "Test123!@#"}, desc="注册新用户", expected_code=200)
    test("POST", "/api/v1/auth/register/", {"username": "testuser99", "password": "Test123!@#"}, desc="注册-重复用户名", expected_code=200)

    # Test 3: Books (optional auth)
    section("[3] 书籍 API (可选认证)")
    test("GET", "/api/v1/books/", desc="书籍列表", expected_code=200)
    test("GET", "/api/v1/books/?search=小说", desc="书籍搜索", expected_code=200)
    test("GET", "/api/v1/books/?page=1", desc="书籍分页", expected_code=200)
    test("GET", "/api/v1/books/?page=999", desc="书籍分页-超出范围", expected_code=200)
    test("GET", "/api/v1/books/99999/", desc="书籍详情-不存在", expected_code=404)
    test("GET", "/api/v1/books/?category=玄幻", desc="书籍-按分类筛选", expected_code=200)

    # Test 4: Chapters (optional auth)
    section("[4] 章节 API (可选认证)")
    test("GET", "/api/v1/books/99999/chapters/", desc="章节列表-不存在的书", expected_code=404)
    # 注: 书籍章节测试需在创建书籍后进行，见认证流程测试

    # Test 5: Search (optional auth)
    section("[5] 搜索 API (可选认证)")
    test("GET", "/api/v1/search/", desc="空搜索", expected_code=200)
    test("GET", "/api/v1/search/?q=test", desc="英文关键词搜索", expected_code=200)
    test("GET", "/api/v1/search/?q=小", desc="中文单字搜索", expected_code=200)

    # Test 6: Tags (optional auth for GET)
    section("[6] 标签 API (可选认证)")
    test("GET", "/api/v1/tags/", desc="标签列表", expected_code=200)
    test("GET", "/api/v1/tags/?page=1", desc="标签分页", expected_code=200)

    # Test 7: Unauthenticated → 401
    section("[7] 需要认证 (未登录 → 401)")
    test("POST", "/api/v1/auth/logout/", {}, desc="登出-未登录", expected_code=401)

    test("GET", "/api/v1/progress/", desc="阅读进度列表-未登录", expected_code=401)
    test("POST", "/api/v1/progress/", {}, desc="保存进度-未登录", expected_code=401)
    test("POST", "/api/v1/progress/track-stats/", {}, desc="追踪统计-未登录", expected_code=401)
    test("GET", "/api/v1/crawler/", desc="爬虫任务列表-未登录", expected_code=401)
    test("POST", "/api/v1/crawler/", {}, desc="创建爬虫任务-未登录", expected_code=401)
    test("GET", "/api/v1/crawler/1/", desc="爬虫任务详情-未登录", expected_code=401)
    test("POST", "/api/v1/tags/", {}, desc="创建标签-未登录", expected_code=401)
    test("DELETE", "/api/v1/tags/1/", desc="删除标签-未登录", expected_code=401)
    test("GET", "/api/v1/favorites/", desc="收藏列表-未登录", expected_code=401)
    test("POST", "/api/v1/favorites/toggle/", {}, desc="切换收藏-未登录", expected_code=401)
    test("GET", "/api/v1/users/", desc="用户列表-未登录", expected_code=401)
    test("GET", "/api/v1/stats/", desc="统计数据-未登录", expected_code=401)

    # Test 8: Authenticated flow
    section("[8] 认证流程测试 (需要登录)")

    # Login to get session
    session = requests.Session()
    r = session.post(f"{BASE}/api/v1/auth/login/", json={"username": "testuser99", "password": "Test123!@#"})
    login_ok = r.status_code == 200 and r.json().get("success") == True
    print(f"  {'✅' if login_ok else '❌'} 登录 testuser99: {r.json()}")

    if login_ok:
        cookies = session.cookies

        # Test batch-import with multipart (files only, no json body)
        # 未登录测试
        r_raw = requests.post(f"{BASE}/api/v1/books/import/", files={"files": ("test.txt", "test content", "text/plain")})
        print(f"  {'✅' if r_raw.status_code == 401 else '❌'} 批量导入-未登录: {r_raw.status_code}")

        # 已登录测试
        r = session.post(f"{BASE}/api/v1/books/import/", files={"files": ("测试书.txt", "第一章\n这是第一章的内容。\n\n第二章\n这是第二章的内容。", "text/plain")})
        if r.status_code == 200:
            resp = r.json()
            print(f"  {'✅' if r.status_code == 200 else '❌'} 批量导入-已登录: {resp.get('imported', 0)} 本")
        else:
            print(f"  ❌ 批量导入失败: {r.status_code} {r.text[:100]}")

        # 章节测试 - 获取已导入的书籍
        r2 = session.get(f"{BASE}/api/v1/books/")
        books_data = r2.json()
        if books_data.get("items"):
            first_book = books_data["items"][0]
            first_book_id = first_book["id"]
            print(f"\n  📚 测试书籍ID={first_book_id}: {first_book.get('title', 'N/A')}")

            # 章节列表
            r3 = session.get(f"{BASE}/api/v1/books/{first_book_id}/chapters/")
            print(f"  {'✅' if r3.status_code == 200 else '❌'} 章节列表: {r3.status_code}")
            if r3.status_code == 200:
                chapters = r3.json()
                if chapters:
                    ch = chapters[0]
                    print(f"     → 找到 {len(chapters)} 章")

                    # 章节详情
                    r4 = session.get(f"{BASE}/api/v1/books/{first_book_id}/chapters/{ch['id']}/")
                    print(f"  {'✅' if r4.status_code == 200 else '❌'} 章节内容(章ID={ch['id']}): {r4.status_code}")

                    # 阅读进度测试
                    r5 = session.post(f"{BASE}/api/v1/progress/", json={"book_id": first_book_id, "chapter_id": ch['id'], "position": 100})
                    print(f"  {'✅' if r5.status_code == 200 else '❌'} 保存阅读进度: {r5.status_code}")

                    # 收藏测试
                    r6 = session.post(f"{BASE}/api/v1/favorites/toggle/", json={"book_id": first_book_id})
                    print(f"  {'✅' if r6.status_code == 200 else '❌'} 切换收藏: {r6.status_code} (is_favorited={r6.json().get('is_favorited', 'N/A')})")
                else:
                    print(f"     → 无章节数据")
            else:
                print(f"     → 获取章节列表失败")

            # 不存在的章节
            r7 = session.get(f"{BASE}/api/v1/books/{first_book_id}/chapters/99999/")
            print(f"  {'✅' if r7.status_code == 404 else '❌'} 不存在的章节: {r7.status_code}")
        else:
            print(f"\n  ⚠️  未找到书籍，跳过章节测试")

        # Tags CRUD
        test("GET", "/api/v1/tags/", desc="标签列表-已登录", expected_code=200, cookies=cookies)
        r2 = session.post(f"{BASE}/api/v1/tags/", json={"name": "测试标签", "color": "#ff0000"})
        print(f"  {'✅' if r2.status_code == 200 else '❌'} 创建标签: {r2.json()}")
        tag_id = r2.json().get("id") if r2.status_code == 200 else None

        if tag_id:
            test("DELETE", f"/api/v1/tags/{tag_id}/", desc=f"删除标签ID={tag_id}", expected_code=200, cookies=cookies)

        # Progress
        test("GET", "/api/v1/progress/", desc="阅读进度列表-已登录", expected_code=200, cookies=cookies)
        test("POST", "/api/v1/progress/", {"book_id": 99999, "chapter_id": None, "position": 1}, desc="保存进度-不存在的书", expected_code=404, cookies=cookies)

        # Stats
        test("GET", "/api/v1/stats/", desc="统计数据-已登录", expected_code=200, cookies=cookies)
        test("GET", "/api/v1/stats/?days=30", desc="统计数据-30天", expected_code=200, cookies=cookies)

        # Favorites
        test("GET", "/api/v1/favorites/", desc="收藏列表-已登录", expected_code=200, cookies=cookies)
        test("POST", "/api/v1/favorites/toggle/", {"book_id": 99999}, desc="切换收藏-不存在的书", expected_code=404, cookies=cookies)

        # Crawler
        test("GET", "/api/v1/crawler/", desc="爬虫任务列表-已登录", expected_code=200, cookies=cookies)

        # Users
        test("GET", "/api/v1/users/", desc="用户列表-已登录", expected_code=200, cookies=cookies)

        # Logout
        test("POST", "/api/v1/auth/logout/", {}, desc="登出-已登录", expected_code=200, cookies=cookies)

    # Test 9: API Docs
    section("[9] API 文档")
    test("GET", "/api/v1/docs/", desc="Swagger UI", expected_code=200)
    test("GET", "/api/v1/openapi.json", desc="OpenAPI Schema", expected_code=200)

    # Summary
    section("测试总结")
    total = PASS + FAIL
    pct = f"{PASS / total * 100:.1f}%" if total > 0 else "0%"
    print(f"\n  总计: {total} | ✅ 通过: {PASS} | ❌ 失败: {FAIL} ({pct})")
    print(f"\n  失败列表:")
    for r in RESULTS:
        if not r["ok"]:
            print(f"  - {r['method']} {r['path']} 期望 {r['expected']} 实际 {r['actual']}")
    print()
    return FAIL == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
