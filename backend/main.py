import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers, ErrorHandlingMiddleware
from app.core.startup_check import startup_check
from app.core.safe_logger import get_safe_logger
from app.database import init_database
from app.api import auth, books, chapters, favorites, crawler, search, health
from app.services.cache_service import cache_service
from app.services.search_service import search_service

settings = get_settings()

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = get_safe_logger(__name__)

startup_report = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global startup_report

    logger.info(f"正在启动 {settings.APP_NAME} v{settings.APP_VERSION}")

    startup_report = await startup_check.run_all()

    if not startup_report.healthy:
        logger.error(f"启动自检未通过: {startup_report.errors} 个错误")
        if startup_report.errors > 0:
            for check in startup_report.checks:
                if not check.passed and not check.skipped and check.severity == "error":
                    logger.error(f"  - {check.name}: {check.message}")

    from app.api.health import set_startup_report
    set_startup_report(startup_report)

    await init_database()
    logger.info("数据库初始化完成")

    await cache_service.connect()
    logger.info("缓存服务初始化完成")

    try:
        await search_service.ensure_fts_table()
        logger.info("FTS5 索引表已就绪")
    except Exception as e:
        logger.warning(f"FTS5 索引表初始化失败（非致命）: {e}")

    yield

    await cache_service.disconnect()
    logger.info("应用正在关闭")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="本地小说阅读与分享平台",
    lifespan=lifespan
)

register_exception_handlers(app)

app.add_middleware(ErrorHandlingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(books.router, prefix="/api")
app.include_router(chapters.router, prefix="/api")
app.include_router(favorites.router, prefix="/api")
app.include_router(crawler.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(health.router, prefix="/api")


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
