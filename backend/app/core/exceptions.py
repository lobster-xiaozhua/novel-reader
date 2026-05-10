import traceback
import time
import uuid
from typing import Callable

from fastapi import Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.safe_logger import get_safe_logger

logger = get_safe_logger(__name__)


class AppException(Exception):
    def __init__(self, message: str, status_code: int = 500, details: dict = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class ValidationError(AppException):
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, status_code=400, details=details)


class AuthenticationError(AppException):
    def __init__(self, message: str = "认证失败"):
        super().__init__(message, status_code=401)


class PermissionError(AppException):
    def __init__(self, message: str = "权限不足"):
        super().__init__(message, status_code=403)


class NotFoundError(AppException):
    def __init__(self, resource: str, id: str = None):
        message = f"{resource} 不存在"
        if id:
            message += f": {id}"
        super().__init__(message, status_code=404)


class DatabaseError(AppException):
    def __init__(self, message: str = "数据库错误"):
        super().__init__(message, status_code=503)


class CrawlerError(AppException):
    def __init__(self, message: str = "爬虫错误"):
        super().__init__(message, status_code=502)


class RateLimitError(AppException):
    def __init__(self, message: str = "请求频率超限"):
        super().__init__(message, status_code=429)


def _build_error_response(
    status_code: int,
    message: str,
    path: str,
    details: dict = None,
    error_id: str = None,
) -> JSONResponse:
    body = {
        "error": True,
        "message": message,
        "path": path,
    }
    if details:
        body["details"] = details
    if error_id:
        body["error_id"] = error_id
    return JSONResponse(status_code=status_code, content=body)


def register_exception_handlers(app):
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        logger.warning(
            f"业务异常 [{exc.status_code}] {request.method} {request.url.path}: {exc.message}"
        )
        return _build_error_response(
            status_code=exc.status_code,
            message=exc.message,
            path=request.url.path,
            details=exc.details,
        )

    @app.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, exc: ValidationError):
        logger.warning(f"参数验证失败 {request.method} {request.url.path}: {exc.message}")
        return _build_error_response(
            status_code=400,
            message=exc.message,
            path=request.url.path,
            details=exc.details,
        )

    @app.exception_handler(AuthenticationError)
    async def auth_error_handler(request: Request, exc: AuthenticationError):
        logger.info(f"认证失败 {request.method} {request.url.path}")
        return _build_error_response(
            status_code=401,
            message=exc.message,
            path=request.url.path,
        )

    @app.exception_handler(PermissionError)
    async def permission_error_handler(request: Request, exc: PermissionError):
        logger.warning(f"权限不足 {request.method} {request.url.path}")
        return _build_error_response(
            status_code=403,
            message=exc.message,
            path=request.url.path,
        )

    @app.exception_handler(NotFoundError)
    async def not_found_error_handler(request: Request, exc: NotFoundError):
        logger.info(f"资源不存在 {request.method} {request.url.path}: {exc.message}")
        return _build_error_response(
            status_code=404,
            message=exc.message,
            path=request.url.path,
        )

    @app.exception_handler(DatabaseError)
    async def database_error_handler(request: Request, exc: DatabaseError):
        error_id = str(uuid.uuid4())[:8]
        logger.error(f"数据库错误 [{error_id}] {request.method} {request.url.path}: {exc.message}")
        return _build_error_response(
            status_code=503,
            message="服务暂时不可用，请稍后重试",
            path=request.url.path,
            error_id=error_id,
        )

    @app.exception_handler(CrawlerError)
    async def crawler_error_handler(request: Request, exc: CrawlerError):
        logger.error(f"爬虫错误 {request.method} {request.url.path}: {exc.message}")
        return _build_error_response(
            status_code=502,
            message=exc.message,
            path=request.url.path,
        )

    @app.exception_handler(RateLimitError)
    async def rate_limit_error_handler(request: Request, exc: RateLimitError):
        logger.warning(f"频率限制 {request.method} {request.url.path}")
        return _build_error_response(
            status_code=429,
            message=exc.message,
            path=request.url.path,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        errors = exc.errors()
        details = []
        for error in errors:
            field = ".".join(str(x) for x in error.get("loc", []))
            msg = error.get("msg", "")
            details.append({"field": field, "message": msg})
        logger.warning(f"请求验证失败 {request.method} {request.url.path}: {details}")
        return _build_error_response(
            status_code=422,
            message="请求参数验证失败",
            path=request.url.path,
            details={"errors": details},
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
        error_id = str(uuid.uuid4())[:8]
        logger.error(f"数据库异常 [{error_id}] {request.method} {request.url.path}: {exc}")
        return _build_error_response(
            status_code=503,
            message="数据库服务暂时不可用，请稍后重试",
            path=request.url.path,
            error_id=error_id,
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        error_id = str(uuid.uuid4())[:8]
        tb = traceback.format_exc()
        logger.error(
            f"未处理异常 [{error_id}] {request.method} {request.url.path}: {exc}\n{tb}"
        )
        return _build_error_response(
            status_code=500,
            message="服务器内部错误，请稍后重试",
            path=request.url.path,
            error_id=error_id,
        )


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        start_time = time.time()

        try:
            response = await call_next(request)
        except Exception as exc:
            error_id = str(uuid.uuid4())[:8]
            tb = traceback.format_exc()
            logger.error(
                f"中间件捕获异常 [{error_id}] {request.method} {request.url.path}: {exc}\n{tb}"
            )
            return _build_error_response(
                status_code=500,
                message="服务器内部错误，请稍后重试",
                path=request.url.path,
                error_id=error_id,
            )

        elapsed = time.time() - start_time
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{elapsed:.3f}s"

        if response.status_code >= 500:
            logger.error(
                f"[{request_id}] {request.method} {request.url.path} -> {response.status_code} ({elapsed:.3f}s)"
            )
        elif response.status_code >= 400:
            logger.warning(
                f"[{request_id}] {request.method} {request.url.path} -> {response.status_code} ({elapsed:.3f}s)"
            )

        return response
