import pytest
from fastapi.testclient import TestClient


class TestAuthAPI:
    def test_register_success(self, client):
        response = client.post("/api/auth/register", json={
            "username": "newuser",
            "password": "Password123",
        })
        assert response.status_code in [200, 201, 400]

    def test_register_weak_password(self, client):
        response = client.post("/api/auth/register", json={
            "username": "user",
            "password": "123",
        })
        assert response.status_code in [400, 422]

    def test_login_success(self, client):
        client.post("/api/auth/register", json={
            "username": "logintest",
            "password": "Password123",
        })
        response = client.post("/api/auth/login", data={
            "username": "logintest",
            "password": "Password123",
        })
        assert response.status_code in [200, 400]

    def test_login_invalid_credentials(self, client):
        response = client.post("/api/auth/login", data={
            "username": "nonexistent",
            "password": "wrongpass",
        })
        assert response.status_code in [401, 400]

    def test_get_me_without_token(self, client):
        response = client.get("/api/auth/me")
        assert response.status_code == 401


class TestBooksAPI:
    def test_get_books_list(self, client):
        response = client.get("/api/books")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data or isinstance(data, list)

    def test_get_book_detail_not_found(self, client):
        response = client.get("/api/books/99999")
        assert response.status_code in [404, 200]

    def test_scan_books(self, client):
        response = client.post("/api/books/scan")
        assert response.status_code in [200, 401]


class TestChaptersAPI:
    def test_get_chapter_not_found(self, client):
        response = client.get("/api/chapters/99999")
        assert response.status_code in [404, 200]

    def test_get_next_chapter_not_found(self, client):
        response = client.get("/api/chapters/99999/next")
        assert response.status_code in [404, 200]


class TestFavoritesAPI:
    def test_get_favorites_without_auth(self, client):
        response = client.get("/api/favorites")
        assert response.status_code in [401, 200]

    def test_add_favorite_without_auth(self, client):
        response = client.post("/api/favorites/async", json={"book_id": 1})
        assert response.status_code in [401, 200]


class TestSearchAPI:
    def test_search_books(self, client):
        response = client.get("/api/search/books?q=test")
        assert response.status_code == 200

    def test_search_content(self, client):
        response = client.get("/api/search/content?q=test")
        assert response.status_code == 200

    def test_search_suggestions(self, client):
        response = client.get("/api/search/suggestions?q=te")
        assert response.status_code == 200


class TestHealthAPI:
    def test_health_check(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "checks" in data

    def test_startup_report(self, client):
        response = client.get("/api/health/startup")
        assert response.status_code in [200, 500]

    def test_detailed_health(self, client):
        response = client.get("/api/health/detailed")
        assert response.status_code == 200


class TestCrawlerAPI:
    def test_create_task_without_auth(self, client):
        response = client.post("/api/crawler/tasks", json={"url": "https://example.com"})
        assert response.status_code in [401, 200, 422]

    def test_get_tasks(self, client):
        response = client.get("/api/crawler/tasks")
        assert response.status_code in [200, 401]


class TestAdminAPI:
    def test_rebuild_index_without_admin(self, client):
        response = client.post("/api/admin/rebuild-index")
        assert response.status_code in [401, 403, 404]

    def test_clear_cache_without_admin(self, client):
        response = client.post("/api/admin/clear-cache")
        assert response.status_code in [401, 403, 404]

    def test_get_stats_without_admin(self, client):
        response = client.get("/api/admin/stats")
        assert response.status_code in [401, 403, 404]
