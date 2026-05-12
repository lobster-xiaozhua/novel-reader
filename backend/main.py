import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers, ErrorHandlingMiddleware
from app.core.startup_check import startup_check
from app.core.logging_config import setup_logging, get_logger
from app.database import init_database
from app.api import auth, books, chapters, favorites, crawler, search, health, update, version
from app.services.cache_service import cache_service
from app.services.search_service import search_service

settings = get_settings()

setup_logging()
logger = get_logger(__name__)

startup_report = None

FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    global startup_report

    logger.success(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    startup_report = await startup_check.run_all()

    if not startup_report.healthy:
        logger.error(f"Startup check failed: {startup_report.errors} errors")
        if startup_report.errors > 0:
            for check in startup_report.checks:
                if not check.passed and not check.skipped and check.severity == "error":
                    logger.error(f"  {check.name}: {check.message}")
    else:
        logger.success("Startup check passed")

    from app.api.health import set_startup_report
    set_startup_report(startup_report)

    await init_database()
    logger.success("Database initialized")

    await cache_service.connect()
    logger.success("Cache service initialized")

    try:
        await search_service.ensure_fts_table()
        logger.success("FTS5 index ready")
    except Exception as e:
        logger.warning(f"FTS5 init failed (non-fatal): {e}")

    if FRONTEND_DIST.is_dir():
        logger.success(f"Frontend: serving from {FRONTEND_DIST}")
    else:
        logger.warning(f"Frontend dist not found at {FRONTEND_DIST}")

    logger.success("=" * 50)
    logger.success(f"  {settings.APP_NAME} started!")
    logger.success(f"  http://localhost:8000")
    logger.success(f"  API docs: http://localhost:8000/docs")
    logger.success("=" * 50)

    yield

    logger.info("Shutting down...")
    await cache_service.disconnect()
    logger.success("Shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Local novel reader platform",
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
app.include_router(update.router, prefix="/api")
app.include_router(version.router, prefix="/api")

if FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = FRONTEND_DIST / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIST / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
