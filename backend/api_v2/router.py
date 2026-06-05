"""API v2 路由入口"""
import logging
import traceback

from ninja import NinjaAPI
from ninja.errors import HttpError, ValidationError

from .auth.routes import router as auth_router
from .reader.routes import router as reader_router
from .admin.routes import router as admin_router
from .schemas import ApiResponse

logger = logging.getLogger(__name__)

api_v2 = NinjaAPI(
    title='NovelReader API v2',
    version='2.0.0',
    description='小说阅读器 API v2 — reader/admin 分离',
    docs_url='/docs/',
    openapi_url='/openapi.json',
)


@api_v2.exception_handler(HttpError)
def http_error_handler(request, exc):
    logger.warning(f'[API v2 {exc.status_code}] {request.method} {request.path}: {exc.message}')
    return api_v2.create_response(request, ApiResponse.fail(exc.message).dict(), status=exc.status_code)


@api_v2.exception_handler(ValidationError)
def validation_error_handler(request, exc):
    logger.warning(f'[API v2 422] {request.method} {request.path}: {exc.errors}')
    return api_v2.create_response(request, ApiResponse.fail('请求数据验证失败').dict(), status=422)


@api_v2.exception_handler(Exception)
def global_exception_handler(request, exc):
    logger.error(f'[API v2 500] {request.method} {request.path}: {type(exc).__name__}: {exc}\n{traceback.format_exc()}')
    return api_v2.create_response(request, ApiResponse.fail('服务器内部错误，请稍后重试').dict(), status=500)


api_v2.add_router('/auth/', auth_router)
api_v2.add_router('/reader/', reader_router)
api_v2.add_router('/admin/', admin_router)