"""API 路由入口"""
import logging
import traceback

from ninja import NinjaAPI
from ninja.errors import HttpError, ValidationError

from .auth.routes import router as auth_router
from .reader.routes import router as reader_router
from .admin.routes import router as admin_router
from .schemas import ApiResponse

logger = logging.getLogger(__name__)

api = NinjaAPI(
    title='NovelReader API',
    version='2.0.0',
    description='小说阅读器 API — reader/admin 分离',
    docs_url='/docs/',
    openapi_url='/openapi.json',
)


@api.exception_handler(HttpError)
def http_error_handler(request, exc):
    logger.warning(f'[API {exc.status_code}] {request.method} {request.path}: {exc.message}')
    return api.create_response(request, ApiResponse.fail(exc.message).dict(), status=exc.status_code)


@api.exception_handler(ValidationError)
def validation_error_handler(request, exc):
    logger.warning(f'[API 422] {request.method} {request.path}: {exc.errors}')
    return api.create_response(request, ApiResponse.fail('请求数据验证失败').dict(), status=422)


@api.exception_handler(Exception)
def global_exception_handler(request, exc):
    logger.error(f'[API 500] {request.method} {request.path}: {type(exc).__name__}: {exc}\n{traceback.format_exc()}')
    return api.create_response(request, ApiResponse.fail('服务器内部错误，请稍后重试').dict(), status=500)


api.add_router('/auth/', auth_router)
api.add_router('/reader/', reader_router)
api.add_router('/admin/', admin_router)