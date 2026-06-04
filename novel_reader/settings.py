import environ
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    SECURE_SSL_REDIRECT=(bool, False),
    SECURE_HSTS_SECONDS=(int, 0),
    CONN_MAX_AGE=(int, 60),
    REDIS_URL=(str, ''),
    CELERY_BROKER_URL=(str, 'redis://localhost:6379/0'),
    CELERY_RESULT_BACKEND=(str, 'redis://localhost:6379/0'),
)
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY', default='django-insecure-dev-key-change-in-production-!@#$%^&*()')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1', '0.0.0.0'])

if not DEBUG:
    SECURE_SSL_REDIRECT = env('SECURE_SSL_REDIRECT')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = env('SECURE_HSTS_SECONDS')
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'

INSTALLED_APPS = [
    'unfold',
    'unfold.contrib.filters',
    'unfold.contrib.forms',
    'unfold.contrib.inlines',
    'unfold.contrib.import_export',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'apps.api',
    'apps.accounts',
    'apps.books',
    'apps.chapters',
    'apps.reader',
    'apps.favorites',
    'apps.crawler',
    'apps.recommender',
    'ninja',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'novel_reader.middleware.APIMonitorMiddleware',
    'novel_reader.middleware.RequestTimingMiddleware',
    'novel_reader.middleware.JWTAuthMiddleware',
]

ROOT_URLCONF = 'novel_reader.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'OPTIONS': {
            'loaders': [
                ('django.template.loaders.cached.Loader', [
                    'django.template.loaders.filesystem.Loader',
                    'django.template.loaders.app_directories.Loader',
                ]),
            ],
            'builtins': [
                'django.templatetags.static',
            ],
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'novel_reader.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'data' / 'db.sqlite3',
    }
}
_db_url_str = env('DATABASE_URL', default='')
if _db_url_str:
    _db_url = env.db_url(default=_db_url_str, engine='django.db.backends.sqlite3')
    DATABASES['default'] = _db_url
    if DATABASES['default'].get('ENGINE', '').startswith('sqlite'):
        DATABASES['default']['ENGINE'] = 'django.db.backends.sqlite3'
DATABASES['default']['CONN_MAX_AGE'] = env('CONN_MAX_AGE')

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static'] + [d for d in [BASE_DIR / 'frontend' / 'dist' / 'static', BASE_DIR / 'frontend' / 'dist'] if d.is_dir()]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'
WHITENOISE_MAX_AGE = 31536000
WHITENOISE_INDEX_FILE = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

_REDIS_URL = env('REDIS_URL', default='')
if _REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': _REDIS_URL,
            'KEY_PREFIX': 'novelreader',
            'TIMEOUT': 300,
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'novelreader-cache',
            'OPTIONS': {
                'MAX_ENTRIES': 5000,
                'CULL_FREQUENCY': 3,
            },
        }
    }

SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 1209600
SESSION_SAVE_EVERY_REQUEST = True

CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[]) if not DEBUG else []

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'suppress_bad_auth': {
            '()': 'novel_reader.middleware.SuppressBadAuthLog',
        },
    },
    'formatters': {
        'simple': {'format': '[%(levelname)s] %(name)s: %(message)s'},
        'verbose': {'format': '[%(asctime)s] [%(levelname)s] %(name)s:%(lineno)d: %(message)s'},
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'level': 'DEBUG' if DEBUG else 'INFO',
            'filters': ['suppress_bad_auth'],
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'data' / 'logs' / 'app.log',
            'maxBytes': 5 * 1024 * 1024,
            'backupCount': 10,
            'formatter': 'verbose',
            'level': 'INFO',
        },
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'data' / 'logs' / 'errors.log',
            'maxBytes': 5 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'verbose',
            'level': 'ERROR',
        },
        'request_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'data' / 'logs' / 'requests.log',
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 10,
            'formatter': 'verbose',
            'level': 'INFO',
        },
        'auth_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'data' / 'logs' / 'auth.log',
            'maxBytes': 5 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'verbose',
            'level': 'INFO',
        },
        'crawler_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'data' / 'logs' / 'crawler.log',
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 10,
            'formatter': 'verbose',
            'level': 'INFO',
        },
    },
    'root': {
        'handlers': ['console', 'file', 'error_file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'error_file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'novel_reader.request': {
            'handlers': ['console', 'request_file', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'novel_reader.auth': {
            'handlers': ['console', 'auth_file', 'file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps.crawler': {
            'handlers': ['console', 'crawler_file', 'error_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'utils.crawler_engine': {
            'handlers': ['console', 'crawler_file', 'error_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'ninja': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

LOGIN_URL = '/login'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login'

BOOKS_DIR = BASE_DIR / 'data' / 'books'
LOGS_DIR = BASE_DIR / 'data' / 'logs'
CACHE_DIR = BASE_DIR / 'data' / 'cache'

for _d in [BOOKS_DIR, LOGS_DIR, CACHE_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

CELERY_BROKER_URL = env('CELERY_BROKER_URL')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_ACKS_LATE = True

NINJA_PAGINATION_PER_PAGE = 20
NINJA_PAGINATION_MAX_LIMIT = 100

JWT_SECRET = env('JWT_SECRET', default=SECRET_KEY)
JWT_ACCESS_LIFETIME_MINUTES = env.int('JWT_ACCESS_LIFETIME_MINUTES', default=15)
JWT_REFRESH_LIFETIME_DAYS = env.int('JWT_REFRESH_LIFETIME_DAYS', default=7)

UNFOLD = {
    "SITE_TITLE": "小说阅读器管理后台",
    "SITE_HEADER": "📖 小说阅读器",
    "SITE_SYMBOL": "menu_book",
    "DASHBOARD_CALLBACK": "apps.books.admin.dashboard_callback",
    "THEME": "dark",
    "COLORS": {
        "primary": {
            "50": "255 251 235",
            "100": "254 243 199",
            "200": "253 230 138",
            "300": "252 211 77",
            "400": "251 191 36",
            "500": "245 158 11",
            "600": "217 119 6",
            "700": "180 83 9",
            "800": "146 64 14",
            "900": "120 53 15",
            "950": "69 26 3",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": "数据概览",
                "separator": True,
                "items": [
                    {
                        "title": "Dashboard",
                        "icon": "dashboard",
                        "link": "/admin/",
                    },
                ],
            },
            {
                "title": "内容管理",
                "separator": True,
                "items": [
                    {
                        "title": "书籍",
                        "icon": "menu_book",
                        "link": "/admin/books/book/",
                    },
                    {
                        "title": "章节",
                        "icon": "article",
                        "link": "/admin/chapters/chapter/",
                    },
                    {
                        "title": "标签",
                        "icon": "label",
                        "link": "/admin/books/tag/",
                    },
                ],
            },
            {
                "title": "用户与阅读",
                "separator": True,
                "items": [
                    {
                        "title": "用户",
                        "icon": "people",
                        "link": "/admin/auth/user/",
                    },
                    {
                        "title": "阅读进度",
                        "icon": "bookmark",
                        "link": "/admin/reader/readingprogress/",
                    },
                    {
                        "title": "阅读统计",
                        "icon": "analytics",
                        "link": "/admin/reader/readingstats/",
                    },
                    {
                        "title": "收藏",
                        "icon": "favorite",
                        "link": "/admin/favorites/favorite/",
                    },
                ],
            },
            {
                "title": "系统",
                "separator": True,
                "items": [
                    {
                        "title": "爬虫任务",
                        "icon": "spider",
                        "link": "/admin/crawler/crawlertask/",
                    },
                ],
            },
        ],
    },
}

if DEBUG:
    INSTALLED_APPS.insert(0, 'debug_toolbar')
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
    INTERNAL_IPS = ['127.0.0.1', '10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16']
    DEBUG_TOOLBAR_CONFIG = {
        'SHOW_TOOLBAR_CALLBACK': lambda request: True,
        'DISABLE_PANELS': {
            'debug_toolbar.panels.redirects.RedirectsPanel',
        },
    }
