import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.core.exceptions import (
    AppException, ValidationError, AuthenticationError, PermissionError,
    NotFoundError, DatabaseError, CrawlerError, RateLimitError,
    register_exception_handlers, _build_error_response
)


class TestExceptionTypes:
    def test_app_exception_basic(self):
        exc = AppException("test message")
        assert exc.message == "test message"
        assert exc.status_code == 500
        assert exc.details == {}

    def test_app_exception_with_status_code(self):
        exc = AppException("not found", status_code=404)
        assert exc.status_code == 404

    def test_app_exception_with_details(self):
        exc = AppException("error", details={"field": "value"})
        assert exc.details == {"field": "value"}

    def test_validation_error(self):
        exc = ValidationError("invalid input")
        assert exc.status_code == 400
        assert exc.message == "invalid input"

    def test_validation_error_with_details(self):
        exc = ValidationError("invalid", details={"field": "email"})
        assert exc.details == {"field": "email"}

    def test_authentication_error(self):
        exc = AuthenticationError()
        assert exc.status_code == 401
        assert exc.message == "认证失败"

    def test_authentication_error_custom_message(self):
        exc = AuthenticationError("token expired")
        assert exc.message == "token expired"

    def test_permission_error(self):
        exc = PermissionError()
        assert exc.status_code == 403
        assert exc.message == "权限不足"

    def test_not_found_error(self):
        exc = NotFoundError("Book", "123")
        assert exc.status_code == 404
        assert "Book" in exc.message
        assert "123" in exc.message

    def test_not_found_error_without_id(self):
        exc = NotFoundError("User")
        assert exc.message == "User 不存在"

    def test_database_error(self):
        exc = DatabaseError()
        assert exc.status_code == 503
        assert exc.message == "数据库错误"

    def test_crawler_error(self):
        exc = CrawlerError("timeout")
        assert exc.status_code == 502
        assert exc.message == "timeout"

    def test_rate_limit_error(self):
        exc = RateLimitError()
        assert exc.status_code == 429
        assert exc.message == "请求频率超限"


class TestErrorResponseBuilder:
    def test_build_error_response_basic(self):
        import json
        response = _build_error_response(400, "bad request", "/api/test")
        assert response.status_code == 400
        data = json.loads(response.body)
        assert data["error"] is True
        assert data["message"] == "bad request"
        assert data["path"] == "/api/test"

    def test_build_error_response_with_details(self):
        import json
        response = _build_error_response(400, "error", "/api/test", details={"field": "value"})
        data = json.loads(response.body)
        assert "details" in data
        assert data["details"] == {"field": "value"}

    def test_build_error_response_with_error_id(self):
        import json
        response = _build_error_response(500, "server error", "/api/test", error_id="abc123")
        data = json.loads(response.body)
        assert "error_id" in data
        assert data["error_id"] == "abc123"


class TestExceptionHandlers:
    @pytest.fixture
    def app(self):
        app = FastAPI()
        register_exception_handlers(app)
        return app

    @pytest.fixture
    def client(self, app):
        return TestClient(app)

    def test_app_exception_handler(self, app, client):
        @app.get("/test-app-exc")
        async def test_route():
            raise AppException("custom error", status_code=418)

        response = client.get("/test-app-exc")
        assert response.status_code == 418
        data = response.json()
        assert data["message"] == "custom error"

    def test_validation_error_handler(self, app, client):
        @app.get("/test-validation-exc")
        async def test_route():
            raise ValidationError("invalid input", details={"field": "email"})

        response = client.get("/test-validation-exc")
        assert response.status_code == 400
        data = response.json()
        assert data["details"] == {"field": "email"}

    def test_authentication_error_handler(self, app, client):
        @app.get("/test-auth-exc")
        async def test_route():
            raise AuthenticationError("token invalid")

        response = client.get("/test-auth-exc")
        assert response.status_code == 401

    def test_permission_error_handler(self, app, client):
        @app.get("/test-permission-exc")
        async def test_route():
            raise PermissionError("admin only")

        response = client.get("/test-permission-exc")
        assert response.status_code == 403

    def test_not_found_error_handler(self, app, client):
        @app.get("/test-not-found-exc")
        async def test_route():
            raise NotFoundError("Book", "999")

        response = client.get("/test-not-found-exc")
        assert response.status_code == 404

    def test_database_error_handler(self, app, client):
        @app.get("/test-db-exc")
        async def test_route():
            raise DatabaseError("connection failed")

        response = client.get("/test-db-exc")
        assert response.status_code == 503
        data = response.json()
        assert "error_id" in data

    def test_crawler_error_handler(self, app, client):
        @app.get("/test-crawler-exc")
        async def test_route():
            raise CrawlerError("timeout")

        response = client.get("/test-crawler-exc")
        assert response.status_code == 502

    def test_rate_limit_error_handler(self, app, client):
        @app.get("/test-rate-limit-exc")
        async def test_route():
            raise RateLimitError("too many requests")

        response = client.get("/test-rate-limit-exc")
        assert response.status_code == 429