import logging
from django.contrib import admin
from django.contrib.auth.models import User
from django.db import connection
from django.core.cache import cache
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.urls import path, include
from django.conf import settings
from backend.api.router import api

logger = logging.getLogger('novel_reader.startup')

@receiver(post_migrate)
def log_startup_info(sender, **kwargs):
    """服务启动时记录系统健康检查"""
    import os, platform, django
    from pathlib import Path

    logger.info('=' * 60)
    logger.info('Novel Reader 启动健康检查')
    logger.info('=' * 60)
    logger.info(f'  Python: {platform.python_version()} | Django: {django.VERSION[:3]}')
    logger.info(f'  模式: {"DEBUG" if settings.DEBUG else "PRODUCTION"}')
    logger.info(f'  数据库: {connection.vendor} ({settings.DATABASES["default"]["ENGINE"].split(".")[-1]})')

    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        logger.info('  数据库连接正常')
    except Exception as e:
        logger.error(f'  数据库连接失败: {e}')

    try:
        cache.set('_health_check', 'ok', 10)
        result = cache.get('_health_check')
        if result == 'ok':
            logger.info(f'  缓存正常: {settings.CACHES["default"]["BACKEND"].split(".")[-1]}')
        else:
            logger.warning('  缓存读写异常')
    except Exception as e:
        logger.warning(f'  缓存不可用: {e}')

    try:
        user_count = User.objects.count()
        from apps.books.models import Book
        book_count = Book.objects.count()
        logger.info(f'  用户数: {user_count} | 书籍数: {book_count}')
    except Exception:
        pass

    try:
        data_dir = Path(settings.BASE_DIR) / 'data'
        if data_dir.exists():
            stat = os.statvfs(data_dir)
            free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
            total_gb = (stat.f_blocks * stat.f_frsize) / (1024**3)
            usage_pct = ((total_gb - free_gb) / total_gb * 100) if total_gb > 0 else 0
            logger.info(f'  磁盘: {free_gb:.1f}GB 可用 / {total_gb:.1f}GB 总计 (使用 {usage_pct:.0f}%)')
    except Exception:
        pass

    logger.info('=' * 60)

urlpatterns = [
    path('sys-admin/', admin.site.urls),
    path('api/', api.urls),
]

if settings.DEBUG:
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += [
        path('__debug__/', include('debug_toolbar.urls')),
    ]
