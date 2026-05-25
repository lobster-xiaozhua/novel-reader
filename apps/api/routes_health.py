import logging
import shutil

from django.core.cache import cache
from django.db import connection
from ninja import Router

from .schemas import HealthSchema

logger = logging.getLogger(__name__)
router = Router()


@router.get('/health/', response=HealthSchema, auth=None)
def health_check(request) -> dict:
    checks: dict = {'status': 'ok', 'database': 'ok', 'cache': 'ok', 'disk_usage': 'ok', 'version': '2.0.0'}
    try:
        connection.ensure_connection()
    except Exception as exc:
        logger.warning(f'[Health] 数据库检查失败: {exc}')
        checks['database'] = 'error'
        checks['status'] = 'degraded'
    try:
        cache.set('_health', '1', 5)
        if cache.get('_health') != '1':
            raise RuntimeError('cache readback failed')
    except Exception as exc:
        logger.warning(f'[Health] 缓存检查失败: {exc}')
        checks['cache'] = 'error'
        checks['status'] = 'degraded'
    try:
        usage = shutil.disk_usage('/')
        used_pct = (usage.used / usage.total) * 100
        if used_pct > 95:
            checks['disk_usage'] = f'critical ({used_pct:.0f}%)'
            checks['status'] = 'degraded'
        elif used_pct > 85:
            checks['disk_usage'] = f'warning ({used_pct:.0f}%)'
    except Exception as exc:
        logger.warning(f'[Health] 磁盘检查失败: {exc}')
        checks['disk_usage'] = 'unknown'
    return checks
