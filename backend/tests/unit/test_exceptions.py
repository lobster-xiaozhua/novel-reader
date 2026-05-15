import pytest
import uuid
from unittest.mock import MagicMock, AsyncMock
from fastapi import Request, HTTPException
from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.core.exceptions import (
    AppException,
    ValidationError,
    AuthenticationError,
    PermissionError,
    NotFoundError,
    DatabaseError,
    CrawlerError,
    RateLimitError,
    register_exception_handlers,
    ErrorHandlingMiddleware,
    _build_error_response,
)


class TestCustomExceptions:
    def test_app_exception_defaults(self):
        exc = AppException("Test error")
        assert exc.message == "Test error"
        assert exc.status_code == 500
        assert exc.details == {}

    def test_app_exception_with_details(self):
        exc = AppException("Error with details", status_code=400, details={"field": "name"})
        assert exc.status_code == 400
        assert exc.details == {"field": "name"}

    def test_validation_error(self):
        exc = ValidationError("Invalid input")
        assert exc.status_code == 400
        assert exc.message == "Invalid input"

    def test_authentication_error_defaults(self):
        exc = AuthenticationError()
        assert exc.status_code == 401
        assert "认证" in exc.message

    def test_authentication_error_custom(self):
        exc = AuthenticationError("Token expired")
        assert exc.status_code == 401
        assert exc.message == "Token expired"

    def test_permission_error_defaults(self):
        exc = PermissionError()
        assert exc.status_code == 403
        assert "权限" in exc.message

    def test_permission_error_custom(self):
        exc = PermissionError("Admin required")
        assert exc.status_code == 403
        assert exc.message == "Admin required"

    def test_not_found_error_resource_only(self):
        exc = NotFoundError("User")
        assert exc.status_code == 404
        assert "User" in exc.message
        assert "不存在" in exc.message

    def test_not_found_error_with_id(self):
        exc = NotFoundError("User", "123")
        assert exc.status_code == 404
        assert "123" in exc.message

    def test_database_error(self):
        exc = DatabaseError()
        assert exc.status_code == 503
        assert "数据库" in exc.message

    def test_crawler_error(self):
        exc = CrawlerError("Failed to parse")
        assert exc.status_code == 502
        assert exc.message == "Failed to parse"

    def test_rate_limit_error(self):
        exc = RateLimitError()
        assert exc.status_code == 429
        assert "频率" in exc.message or "限制" in exc.message


class TestBuildErrorResponse:
    def test_basic_error_response(self):
        response = _build_error_response(
            status_code=400,
            message="Bad request",
            path="/api/test"
        )

        assert response.status_code == 400
        body = response.body.decode("utf-8")
        assert '"error":true' in body.replace(' ', '')
        assert '"message":"Bad request"' in body
        assert '"path":"/api/test"' in body

    def test_error_response_with_details(self):
        response = _build_error_response(
            status_code=422,
            message="Validation failed",
            path="/api/users",
            details={"field": "email", "issue": "invalid format"}
        )

        body = response.body.decode("utf-8")
        assert "details" in body

    def test_error_response_with_error_id(self):
        error_id = "abc12345"
        response = _build_error_response(
            status_code=500,
            message="Server error",
            path="/api/test",
            error_id=error_id
        )

        body = response.body.decode("utf-8")
        assert error_id in body


class TestExceptionHandlers:
    @pytest.fixture
    def test_app(self):
        app = FastAPI()
        register_exception_handlers(app)
        return app

    def test_app_exception_handler(self, test_app):
        @test_app.get("/app-exception")
        async def raise_app_exception():
            raise AppException("Custom error", status_code=400)

        client = TestClient(test_app)
        response = client.get("/app-exception")

        assert response.status_code == 400
        data = response.json()
        assert data["error"] is True
        assert data["message"] == "Custom error"

    def test_validation_error_handler(self, test_app):
        @test_app.get("/validation-error")
        async def raise_validation():
            raise ValidationError("Invalid data", details={"field": "name"})

        client = TestClient(test_app)
        response = client.get("/validation-error")

        assert response.status_code == 400
        data = response.json()
        assert data["error"] is True

    def test_authentication_error_handler(self, test_app):
        @test_app.get("/auth-error")
        async def raise_auth():
            raise AuthenticationError("Invalid token")

        client = TestClient(test_app)
        response = client.get("/auth-error")

        assert response.status_code == 401
        data = response.json()
        assert data["error"] is True

    def test_permission_error_handler(self, test_app):
        @test_app.get("/permission-error")
        async def raise_permission():
            raise PermissionError("Access denied")

        client = TestClient(test_app)
        response = client.get("/permission-error")

        assert response.status_code == 403
        data = response.json()
        assert data["error"] is True

    def test_not_found_error_handler(self, test_app):
        @test_app.get("/not-found-error")
        async def raise_not_found():
            raise NotFoundError("Resource", "42")

        client = TestClient(test_app)
        response = client.get("/not-found-error")

        assert response.status_code == 404
        data = response.json()
        assert data["error"] is True

    def test_database_error_handler(self, test_app):
        @test_app.get("/db-error")
        async def raise_db():
            raise DatabaseError("Connection failed")

        client = TestClient(test_app)
        response = client.get("/db-error")

        assert response.status_code == 503
        data = response.json()
        assert data["error"] is True
        assert "error_id" in data

    def test_global_exception_handler(self, test_app):
        @test_app.get("/unhandled-error")
        async def raise_unhandled():
            raise RuntimeError("Unexpected error")

        client = TestClient(test_app, raise_server_exceptions=False)
        response = client.get("/unhandled-error")

        assert response.status_code == 500
        data = response.json()
        assert data["error"] is True
        assert "error_id" in data


class TestErrorHandlingMiddleware:
    @pytest.fixture
    def middleware_app(self):
        app = FastAPI()
        app.add_middleware(ErrorHandlingMiddleware)

        @app.get("/success")
        async def success():
            return {"message": "ok"}

        @app.get("/error")
        async def error():
            raise ValueError("Test error")

        return app

    def test_middleware_adds_request_id_header(self, middleware_app):
        client = TestClient(middleware_app)
        response = client.get("/success")

        assert "x-request-id" in response.headers

    def test_middleware_adds_response_time_header(self, middleware_app):
        client = TestClient(middleware_app)
        response = client.get("/success")

        assert "x-response-time" in response.headers

    def test_middleware_captures_unhandled_exception(self, middleware_app):
        client = TestClient(middleware_app)
        response = client.get("/error")

        assert response.status_code == 500
        data = response.json()
        assert data["error"] is True
        assert "error_id" in data

    def test_middleware_request_state(self, middleware_app):
        @middleware_app.get("/check-state")
        async def check_state(request: Request):
            return {"request_id": getattr(request.state, "request_id", None)}

        client = TestClient(middleware_app)
        response = client.get("/check-state")

        assert response.status_code == 200
        data = response.json()
        assert data["request_id"] is not None
