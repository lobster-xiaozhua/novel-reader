import logging
import traceback

from ninja import NinjaAPI
from ninja.errors import HttpError, ValidationError

from .routes_auth import router as auth_router
from .routes_books import router as books_router
from .routes_crawler import router as crawler_router
from .routes_favorites import router as favorites_router
from .routes_health import router as health_router
from .routes_progress import router as progress_router
from .routes_stats import router as stats_router
from .routes_tags import router as tags_router
from .routes_users import router as users_router

logger = logging.getLogger(__name__)

api = NinjaAPI(
    title='NovelReader API',
    version='1.0.0',
    description='高性能小说阅读器 API',
    docs_url='/docs/',
    openapi_url='/openapi.json',
)


@api.exception_handler(HttpError)
def http_error_handler(request, exc):
    logger.warning(f'[API {exc.status_code}] {request.method} {request.path}: {exc.message}')
    return api.create_response(request, {'error': exc.message}, status=exc.status_code)


@api.exception_handler(ValidationError)
def validation_error_handler(request, exc):
    logger.warning(f'[API 422] {request.method} {request.path}: {exc.errors}')
    return api.create_response(request, {'error': '请求数据验证失败', 'details': str(exc.errors)}, status=422)


@api.exception_handler(Exception)
def global_exception_handler(request, exc):
    logger.error(f'[API 500] {request.method} {request.path}: {type(exc).__name__}: {exc}\n{traceback.format_exc()}')
    return api.create_response(request, {'error': '服务器内部错误，请稍后重试'}, status=500)


api.add_router('', health_router)
api.add_router('', auth_router)
api.add_router('', books_router)
api.add_router('', progress_router)
api.add_router('', crawler_router)
api.add_router('', tags_router)
api.add_router('', favorites_router)
api.add_router('', users_router)
api.add_router('', stats_router)
