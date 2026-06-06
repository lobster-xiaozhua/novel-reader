import environ
import secrets
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

CACHE_DIR = BASE_DIR / 'data' / 'cache'
BOOKS_DIR = BASE_DIR / 'data' / 'books'
LOGS_DIR = BASE_DIR / 'data' / 'logs'

env = environ.Env(
    DEBUG=(bool, False),
    SECURE_SSL_REDIRECT=(bool, False),
    SECURE_HSTS_SECONDS=(int, 0),
    CONN_MAX_AGE=(int, 60),
    REDIS_URL=(str, ''),
    CELERY_BROKER_URL=(str, 'redis://localhost:6379/0'),
    CELERY_RESULT_BACKEND=(str, 'redis://localhost:6379/0'),
)
# 读取 .env（处理 BOM：先读取内容去除 BOM 再写入临时文件）
_env_file = BASE_DIR / '.env'
if _env_file.exists():
    _env_content = _env_file.read_text(encoding='utf-8-sig')
    if _env_content != _env_file.read_text(encoding='utf-8'):
        _env_file.write_text(_env_content, encoding='utf-8')
environ.Env.read_env(_env_file)

# SECRET_KEY: 优先从 .env 读取，缺失时自动生成并持久化
_SECRET_KEY = env('SECRET_KEY', default='')
if not _SECRET_KEY:
    _is_debug = env('DEBUG')
    if not _is_debug:
        raise ImproperlyConfigured(
            '生产环境必须通过环境变量 SECRET_KEY 设置密钥。'
            '请在 .env 文件或环境变量中配置 SECRET_KEY。'
        )
    _SECRET_KEY = secrets.token_urlsafe(50)
    # 自动写入 .env 以便持久化（仅开发环境）
    _env_path = BASE_DIR / '.env'
    _env_lines = []
    if _env_path.exists():
        _env_text = _env_path.read_text(encoding='utf-8-sig')  # utf-8-sig 自动去除 BOM
        _env_lines = _env_text.splitlines()
    if not any(l.lstrip('\ufeff').startswith('SECRET_KEY=') for l in _env_lines):
        # 检查 .gitignore 是否包含 .env
        _gitignore = BASE_DIR / '.gitignore'
        if _gitignore.exists() and '.env' not in _gitignore.read_text():
            import logging as _logging
            _logging.getLogger(__name__).warning('[安全] .gitignore 未包含 .env，自动生成的 SECRET_KEY 可能被提交到版本控制')
        _env_lines.append(f'SECRET_KEY={_SECRET_KEY}')
        _env_path.write_text('\n'.join(_env_lines) + '\n', encoding='utf-8')
SECRET_KEY = _SECRET_KEY
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
else:
    # 开发环境也启用基本安全头
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'

INSTALLED_APPS = [
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
    'apps.search',
    'apps.config',
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
    'novel_reader.middleware.LoginRateLimitMiddleware',
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
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('PG_DB', default='novel_reader'),
        'USER': env('PG_USER', default='novel_user'),
        'PASSWORD': env('PG_PASSWORD', default='novel_pass'),
        'HOST': env('PG_HOST', default='localhost'),
        'PORT': env('PG_PORT', default='5432'),
        'CONN_MAX_AGE': env('CONN_MAX_AGE'),
        'OPTIONS': {
            'options': '-c statement_timeout=10000',
        },
    }
}
_db_url_str = env('DATABASE_URL', default='')
if _db_url_str:
    _db_url = env.db_url(default=_db_url_str)
    # 修正非标准后端：sqlite+aiosqlite -> sqlite3
    if 'ENGINE' in _db_url and _db_url['ENGINE'] not in (
        'django.db.backends.postgresql',
        'django.db.backends.mysql',
        'django.db.backends.sqlite3',
        'django.db.backends.oracle',
    ):
        _engine = _db_url['ENGINE']
        if 'sqlite' in _engine:
            _db_url['ENGINE'] = 'django.db.backends.sqlite3'
        elif 'postgres' in _engine:
            _db_url['ENGINE'] = 'django.db.backends.postgresql'
    DATABASES['default'].update(_db_url)

# SQLite3 不支持 PostgreSQL 的 OPTIONS（如 statement_timeout），需要移除
if DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3':
    DATABASES['default'].pop('OPTIONS', None)
    DATABASES['default'].pop('CONN_MAX_AGE', None)

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
# Next.js 构建输出路径（reader 和 admin 都放在 .next 目录，静态文件会被 collectstatic 收集）
STATICFILES_DIRS = [BASE_DIR / 'static']
# 检查不同的构建输出位置
for d in [
    BASE_DIR / 'frontend' / '.next' / 'static',
    BASE_DIR / 'frontend' / 'out' / 'static',
    BASE_DIR / 'frontend' / 'dist' / 'static',
    BASE_DIR / 'frontend' / 'dist',
]:
    if d.is_dir():
        STATICFILES_DIRS.append(d)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'
WHITENOISE_MAX_AGE = 31536000
WHITENOISE_INDEX_FILE = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ─── Layered Cache System ───
# Tier 1: Redis for hot data (fast, low-latency)
# Tier 2: DiskCache for large objects (embedding vectors, full search results)
_REDIS_AVAILABLE = False
_REDIS_URL = env('REDIS_URL', default='redis://127.0.0.1:6379/1')

# Check if Redis is actually running AND django-redis is installed
try:
    import redis as _redis_client
    _r = _redis_client.Redis.from_url(_REDIS_URL, socket_timeout=2, socket_connect_timeout=2)
    _r.ping()
    _r.close()
    # Also verify django-redis is importable
    import django_redis  # noqa: F401
    _REDIS_AVAILABLE = True
except Exception:
    pass

if _REDIS_AVAILABLE:
    CACHES = {
        # Tier 1: Redis — hot data, short TTL
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': _REDIS_URL,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'CONNECTION_POOL_CLASS': 'redis.BlockingConnectionPool',
                'CONNECTION_POOL_CLASS_KWARGS': {'max_connections': 50, 'timeout': 5},
                'SOCKET_TIMEOUT': 5,
                'SOCKET_CONNECT_TIMEOUT': 2,
                'RETRY_ON_TIMEOUT': True,
                'HEALTH_CHECK_INTERVAL': 30,
            },
            'KEY_PREFIX': 'novelreader',
            'TIMEOUT': 300,  # 5 minutes
        },
        # Tier 2: DiskCache — large objects, long TTL
        'disk': {
            'BACKEND': 'diskcache.DjangoCache',
            'LOCATION': str(CACHE_DIR / 'diskcache'),
            'TIMEOUT': 86400,  # 24 hours
            'OPTIONS': {
                'SHARDS': 8,
                'SIZE_LIMIT': 2**30,  # 1GB
                'EVICTION_POLICY': 'least-frequently-used',
                'STATISTICS': True,
            },
        },
    }
else:
    # Fallback: DiskCache only (Redis not available)
    CACHES = {
        'default': {
            'BACKEND': 'diskcache.DjangoCache',
            'LOCATION': str(CACHE_DIR / 'diskcache'),
            'TIMEOUT': 3600,  # 1 hour
            'OPTIONS': {
                'SHARDS': 4,
                'SIZE_LIMIT': 2**29,  # 512MB
                'EVICTION_POLICY': 'least-frequently-used',
            },
        },
        'disk': {
            'BACKEND': 'diskcache.DjangoCache',
            'LOCATION': str(CACHE_DIR / 'diskcache'),
            'TIMEOUT': 86400,
        },
    }

# Celery uses Redis as broker
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://127.0.0.1:6379/0')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='redis://127.0.0.1:6379/0')

SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 1209600
SESSION_SAVE_EVERY_REQUEST = True

# 始终使用白名单，不再根据 DEBUG 开放所有来源
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])
# 开发环境自动添加 localhost 来源
if DEBUG:
    CORS_ALLOWED_ORIGINS += [
        'http://localhost:5173',
        'http://localhost:3000',  # Next.js dev
        'http://localhost:3001',  # Next.js production
        'http://127.0.0.1:5173',
        'http://127.0.0.1:3000',
    ]

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

# 外挂书籍目录：通过 BOOKS_EXTRA_DIRS 环境变量配置，多个目录用冒号分隔
# 例: BOOKS_EXTRA_DIRS=/mnt/novels:/sdcard/books
_BOOKS_EXTRA = env('BOOKS_EXTRA_DIRS', default='')
BOOKS_EXTRA_DIRS = [Path(d) for d in _BOOKS_EXTRA.split(':') if d.strip()]

# 所有允许的书籍根目录（用于路径安全检查）
BOOKS_ROOTS = [BOOKS_DIR] + BOOKS_EXTRA_DIRS

# 启动时加载 book_dirs.json 中保存的外挂目录
_BOOKS_DIRS_JSON = BASE_DIR / 'data' / 'book_dirs.json'
if _BOOKS_DIRS_JSON.exists():
    try:
        import json as _json
        _saved = _json.loads(_BOOKS_DIRS_JSON.read_text(encoding='utf-8'))
        for _p in _saved.get('extra_dirs', []):
            _dp = Path(_p)
            if _dp not in BOOKS_ROOTS:
                BOOKS_ROOTS.append(_dp)
    except Exception:
        pass

for _d in [BOOKS_DIR, LOGS_DIR, CACHE_DIR] + BOOKS_EXTRA_DIRS:
    _d.mkdir(parents=True, exist_ok=True)

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
