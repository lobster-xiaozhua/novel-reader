import django
from django.conf import settings


def pytest_configure():
    settings.DEBUG = False
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        settings.INSTALLED_APPS.remove('debug_toolbar')
    if 'debug_toolbar.middleware.DebugToolbarMiddleware' in settings.MIDDLEWARE:
        settings.MIDDLEWARE.remove('debug_toolbar.middleware.DebugToolbarMiddleware')
