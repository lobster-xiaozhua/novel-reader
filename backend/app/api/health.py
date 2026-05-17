from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional

from app.database import get_db
from app.core.config import get_settings
from app.services.cache_service import cache_service

router = APIRouter(prefix="/health", tags=["健康检查"])
settings = get_settings()

_startup_report = None


def set_startup_report(report):
    global _startup_report
    _startup_report = report


@router.get("")
async def health_check(db: AsyncSession = Depends(get_db)):
    checks = {
        "database": False,
        "redis": False,
        "disk": False,
    }

    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception as e:
        logger.warning(f"数据库健康检查失败: {e}")

    checks["redis"] = cache_service.available

    try:
        import os
        stat = os.statvfs('/')
        free_percent = (stat.f_bavail * stat.f_frsize) / (stat.f_blocks * stat.f_frsize) * 100
        checks["disk"] = free_percent > 10
        checks["disk_free_percent"] = f"{free_percent:.1f}%"
    except Exception as e:
        logger.warning(f"磁盘健康检查失败: {e}")
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
async def detailed_health(db: AsyncSession = Depends(get_db)):
    import platform
    import os
    import resource

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
        stat = os.statvfs('/')
        free_percent = (stat.f_bavail * stat.f_frsize) / (stat.f_blocks * stat.f_frsize) * 100
        free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
        checks["disk"] = free_percent > 10
        checks["disk_free_percent"] = f"{free_percent:.1f}%"
        checks["disk_free_gb"] = round(free_gb, 2)
    except Exception as e:
        checks["disk_error"] = str(e)

    try:
        mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if platform.system() != "Darwin":
            mem = mem / 1024
    except Exception:
        mem = 0

    return {
        "status": "healthy" if all(checks[k] for k in ["database", "disk"]) else "unhealthy",
        "checks": checks,
        "system": {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "memory_usage_mb": round(mem, 2),
        },
        "app": {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "debug": settings.DEBUG,
        },
    }
