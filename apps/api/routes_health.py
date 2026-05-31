import logging
import shutil
import os
from pathlib import Path
from datetime import datetime

from django.core.cache import cache
from django.conf import settings
from django.db import connection
from django.contrib.auth.models import User
from ninja import Router

from .schemas import HealthSchema

logger = logging.getLogger('novel_reader.health')
router = Router()


@router.get('/health/', response=HealthSchema, auth=None)
def health_check(request) -> dict:
    checks: dict = {'status': 'ok', 'database': 'ok', 'cache': 'ok', 'disk_usage': 'ok', 'version': '2.0.0'}
    try:
        connection.ensure_connection()
    except Exception as exc:
        logger.warning(f'数据库检查失败: {exc}')
        checks['database'] = 'error'
        checks['status'] = 'degraded'
    try:
        cache.set('_health', '1', 5)
        if cache.get('_health') != '1':
            raise RuntimeError('cache readback failed')
    except Exception as exc:
        logger.warning(f'缓存检查失败: {exc}')
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
        logger.warning(f'磁盘检查失败: {exc}')
        checks['disk_usage'] = 'unknown'
    return checks


@router.get('/health/detail/', auth=None)
def health_detail(request) -> dict:
    """详细健康检查，用于运维监控"""
    from apps.books.models import Book
    from apps.crawler.models import CrawlerTask
    
    # 数据库
    db_status = 'ok'
    db_query_time = 0
    try:
        import time
        start = time.monotonic()
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        db_query_time = time.monotonic() - start
    except Exception as e:
        db_status = 'error'
        db_query_time = -1

    # 缓存
    cache_status = 'ok'
    try:
        cache.set('_health_detail', 'ok', 10)
        if cache.get('_health_detail') != 'ok':
            cache_status = 'error'
    except Exception:
        cache_status = 'error'

    # 统计
    user_count = User.objects.count()
    book_count = Book.objects.count()
    crawler_count = CrawlerTask.objects.count()
    active_crawlers = CrawlerTask.objects.filter(status='running').count()

    # 磁盘
    disk_info = {'total_gb': 0, 'free_gb': 0, 'used_pct': 0}
    try:
        usage = shutil.disk_usage('/')
        disk_info['total_gb'] = round(usage.total / (1024**3), 2)
        disk_info['free_gb'] = round(usage.free / (1024**3), 2)
        disk_info['used_pct'] = round((usage.used / usage.total) * 100, 1)
    except Exception:
        pass

    # 日志文件状态
    log_files = {}
    log_dir = settings.BASE_DIR / 'data' / 'logs'
    for fname in ['app.log', 'requests.log', 'auth.log', 'errors.log', 'crawler.log']:
        fpath = log_dir / fname
        if fpath.exists():
            log_files[fname] = {
                'size_mb': round(fpath.stat().st_size / (1024*1024), 2),
                'exists': True,
            }
        else:
            log_files[fname] = {'exists': False}

    # 进程信息
    process_info = {
        'pid': os.getpid(),
        'start_time': datetime.fromtimestamp(os.path.getmtime(__file__)).isoformat(),
        'timezone': settings.TIME_ZONE,
        'debug': settings.DEBUG,
    }

    overall = 'ok' if db_status == 'ok' and cache_status == 'ok' else 'degraded'

    logger.info(f'健康检查: status={overall} | db={db_status}({db_query_time:.3f}s) | cache={cache_status} | users={user_count} | books={book_count}')

    return {
        'status': overall,
        'timestamp': datetime.now().isoformat(),
        'database': {
            'status': db_status,
            'vendor': connection.vendor,
            'query_time_ms': round(db_query_time * 1000, 2),
        },
        'cache': {
            'status': cache_status,
            'backend': settings.CACHES['default']['BACKEND'].split('.')[-1],
        },
        'disk': disk_info,
        'stats': {
            'users': user_count,
            'books': book_count,
            'crawler_tasks': crawler_count,
            'active_crawlers': active_crawlers,
        },
        'logs': log_files,
        'process': process_info,
    }
