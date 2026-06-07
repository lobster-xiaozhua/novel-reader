try:
    from .celery import app as celery_app
    __all__ = ('celery_app',)
except ImportError:
    # celery 未安装时跳过，不影响 Django 核心功能
    __all__ = ()
