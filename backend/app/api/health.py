from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional

from app.database import get_db_no_commit
from app.core.config import get_settings
from app.services.cache_service import cache_service

router = APIRouter(prefix="/health", tags=["健康检查"])
settings = get_settings()

_startup_report = None


def set_startup_report(report):
    global _startup_report
    _startup_report = report


@router.get("")
async def health_check(db: AsyncSession = Depends(get_db_no_commit)):
    checks = {
        "database": False,
        "redis": False,
        "disk": False,
    }

    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        pass

    checks["redis"] = cache_service.available

    try:
        import psutil
        disk = psutil.disk_usage('/')
        checks["disk"] = disk.percent < 90
        checks["disk_usage"] = f"{disk.percent}%"
    except Exception:
        checks["disk"] = True

    healthy = checks["database"] and checks["disk"]

    return {
        "status": "healthy" if healthy else "unhealthy",
        "checks": checks,
    }


@router.get("/startup")
async def startup_report():
    if _startup_report:
        return _startup_report.to_dict()
    return {"message": "启动报告尚未生成"}


@router.get("/detailed")
async def detailed_health(db: AsyncSession = Depends(get_db_no_commit)):
    import platform
    import psutil

    checks = {
        "database": False,
        "redis": False,
        "disk": False,
    }

    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception as e:
        checks["database_error"] = str(e)

    checks["redis"] = cache_service.available

    try:
        disk = psutil.disk_usage('/')
        checks["disk"] = disk.percent < 90
        checks["disk_usage"] = f"{disk.percent}%"
        checks["disk_free_gb"] = round(disk.free / (1024**3), 2)
    except Exception as e:
        checks["disk_error"] = str(e)

    memory = psutil.virtual_memory()

    return {
        "status": "healthy" if all(checks[k] for k in ["database", "disk"]) else "unhealthy",
        "checks": checks,
        "system": {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "memory_percent": f"{memory.percent}%",
            "memory_available_gb": round(memory.available / (1024**3), 2),
        },
        "app": {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "debug": settings.DEBUG,
        },
    }
