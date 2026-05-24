"""
Django 项目配置模块

该模块是小说阅读器项目的核心配置文件，定义了 Django 运行所需的
所有配置项，包括：
- 环境变量管理（基于 django-environ）
- 安全配置（生产环境 HTTPS、HSTS、CSP 等）
- 应用注册与中间件配置
- 数据库、缓存、Session 配置
- 静态文件与白噪声（WhiteNoise）配置
- 日志系统配置（多 handler、多级别、爬虫专用日志）
- Celery 异步任务队列配置
- Django Ninja API 分页配置
- django-unfold 管理后台主题与导航配置
"""

import environ
from pathlib import Path

# 项目根目录：当前文件的父目录的父目录（即包含 manage.py 的目录）
BASE_DIR = Path(__file__).resolve().parent.parent

# 环境变量配置器：定义各环境变量的类型和默认值
env = environ.Env(
    DEBUG=(bool, True),                                    # 调试模式，默认开启
    SECURE_SSL_REDIRECT=(bool, False),                     # 生产环境 HTTPS 重定向
    SECURE_HSTS_SECONDS=(int, 0),                          # HSTS 最大年龄（秒）
    CONN_MAX_AGE=(int, 60),                                # 数据库连接持久化时间
    CACHE_BACKEND=(str, 'django.core.cache.backends.locmem.LocMemCache'),  # 缓存后端
    CACHE_LOCATION=(str, 'novelreader-cache'),             # 缓存位置标识
    CELERY_BROKER_URL=(str, 'redis://localhost:6379/0'),   # Celery 消息代理地址
    CELERY_RESULT_BACKEND=(str, 'redis://localhost:6379/0'),  # Celery 结果存储地址
)
# 从项目根目录的 .env 文件读取环境变量
environ.Env.read_env(BASE_DIR / '.env')

# Django 密钥：用于加密签名和 Session 数据
# 开发环境使用默认值，生产环境必须通过 .env 设置
SECRET_KEY = env('SECRET_KEY', default='django-insecure-dev-key-change-in-production-!@#$%^&*()')
# 调试模式：开启时显示详细错误页面
DEBUG = env('DEBUG')
# 允许访问的主机名列表
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1', '0.0.0.0'])

# ==================== 生产环境安全配置 ====================
# 仅在 DEBUG=False（生产模式）时启用严格的安全策略
if not DEBUG:
    SECURE_SSL_REDIRECT = env('SECURE_SSL_REDIRECT')        # 强制 HTTPS 重定向
    SESSION_COOKIE_SECURE = True                            # Session Cookie 仅通过 HTTPS 传输
    CSRF_COOKIE_SECURE = True                               # CSRF Cookie 仅通过 HTTPS 传输
    SECURE_HSTS_SECONDS = env('SECURE_HSTS_SECONDS')        # HSTS 策略持续时间
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True                   # HSTS 应用于所有子域名
    SECURE_HSTS_PRELOAD = True                              # 允许浏览器预加载 HSTS 策略
    SECURE_CONTENT_TYPE_NOSNIFF = True                      # 阻止浏览器 MIME 类型嗅探
    SECURE_BROWSER_XSS_FILTER = True                        # 启用浏览器 XSS 过滤器
    X_FRAME_OPTIONS = 'DENY'                                # 禁止页面被嵌入 iframe

# ==================== 已安装应用 ====================
INSTALLED_APPS = [
    # django-unfold 管理后台主题（必须在 django.contrib.admin 之前）
    'unfold',
    'unfold.contrib.filters',                               # 后台高级过滤器
    'unfold.contrib.forms',                                 # 后台增强表单
    'unfold.contrib.inlines',                               # 后台内联编辑
    'unfold.contrib.import_export',                         # 后台导入导出功能
    # Django 内置应用
    'django.contrib.admin',                                 # 管理后台
    'django.contrib.auth',                                  # 认证系统
    'django.contrib.contenttypes',                          # 内容类型框架
    'django.contrib.sessions',                              # Session 框架
    'django.contrib.messages',                              # 消息框架
    'django.contrib.staticfiles',                           # 静态文件管理
    # 第三方应用
    'corsheaders',                                          # CORS 跨域支持
    # 项目内部应用
    'apps.accounts',                                        # 用户账户模块
    'apps.books',                                           # 书籍管理模块
    'apps.chapters',                                        # 章节管理模块
    'apps.reader',                                          # 阅读器模块
    'apps.favorites',                                       # 收藏模块
    'apps.crawler',                                         # 爬虫模块
    # Django Ninja API 框架
    'ninja',
]

# ==================== 中间件配置 ====================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',        # 安全相关 header
    'whitenoise.middleware.WhiteNoiseMiddleware',           # 静态文件服务
    'corsheaders.middleware.CorsMiddleware',                # CORS 跨域处理
    'django.contrib.sessions.middleware.SessionMiddleware', # Session 处理
    'django.middleware.common.CommonMiddleware',            # 通用中间件（URL 规范化等）
    'django.middleware.csrf.CsrfViewMiddleware',            # CSRF 防护
    'django.contrib.auth.middleware.AuthenticationMiddleware',  # 用户认证
    'django.contrib.messages.middleware.MessageMiddleware', # 消息处理
    'django.middleware.clickjacking.XFrameOptionsMiddleware',   # 点击劫持防护
    'novel_reader.middleware.AsyncStreamingMiddleware',     # 自定义：异步流式响应
    'novel_reader.middleware.DisableCSRFForAPI',            # 自定义：API 路径跳过 CSRF
]

# URL 路由配置入口
ROOT_URLCONF = 'novel_reader.urls'

# ==================== 模板配置 ====================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',  # Django 模板引擎
        'DIRS': [BASE_DIR / 'templates'],                  # 项目级模板目录
        'OPTIONS': {
            'loaders': [
                # 启用模板缓存加载器，生产环境提升模板渲染性能
                ('django.template.loaders.cached.Loader', [
                    'django.template.loaders.filesystem.Loader',      # 文件系统模板加载
                    'django.template.loaders.app_directories.Loader', # 应用目录模板加载
                ]),
            ],
            'builtins': [
                'django.templatetags.static',               # 模板中可直接使用 {% static %} 标签
            ],
            'context_processors': [
                'django.template.context_processors.debug', # 注入 debug 变量
                'django.template.context_processors.request',  # 注入 request 对象
                'django.contrib.auth.context_processors.auth',   # 注入 user 和 perms
                'django.contrib.messages.context_processors.messages',  # 注入 messages
            ],
        },
    },
]

# WSGI 应用入口（用于 Gunicorn 等 WSGI 服务器）
WSGI_APPLICATION = 'novel_reader.wsgi.application'
# ASGI 应用入口（用于 Uvicorn、Daphne 等 ASGI 服务器）
ASGI_APPLICATION = 'novel_reader.asgi.application'

# ==================== 数据库配置 ====================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',            # 默认使用 SQLite
        'NAME': BASE_DIR / 'data' / 'db.sqlite3',          # 数据库文件路径
    }
}
# 支持通过 DATABASE_URL 环境变量覆盖默认数据库配置
_db_url_str = env('DATABASE_URL', default='')
if _db_url_str:
    _db_url = env.db_url(default=_db_url_str, engine='django.db.backends.sqlite3')
    DATABASES['default'] = _db_url
    # 确保 SQLite 引擎路径正确
    if DATABASES['default'].get('ENGINE', '').startswith('sqlite'):
        DATABASES['default']['ENGINE'] = 'django.db.backends.sqlite3'
# 数据库连接持久化时间（秒），0 表示每次请求后关闭连接
DATABASES['default']['CONN_MAX_AGE'] = env('CONN_MAX_AGE')

# ==================== 密码验证器 ====================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},  # 密码与用户名相似度检查
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},            # 最小长度检查
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},           # 常见密码检查
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},          # 纯数字密码检查
]

# ==================== 国际化配置 ====================
LANGUAGE_CODE = 'zh-hans'                                  # 默认语言：简体中文
TIME_ZONE = 'Asia/Shanghai'                                # 时区：中国标准时间
USE_I18N = True                                            # 启用国际化
USE_TZ = True                                              # 启用时区支持

# ==================== 静态文件配置 ====================
STATIC_URL = 'static/'                                     # 静态文件 URL 前缀
STATIC_ROOT = BASE_DIR / 'staticfiles'                     # collectstatic 收集目标
# 静态文件搜索目录：项目 static 目录 + 前端构建输出目录（如存在）
STATICFILES_DIRS = [BASE_DIR / 'static'] + [d for d in [BASE_DIR / 'frontend' / 'dist' / 'static', BASE_DIR / 'frontend' / 'dist'] if d.is_dir()]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'  # WhiteNoise 压缩存储
WHITENOISE_MAX_AGE = 31536000                              # 静态文件浏览器缓存时间（1 年，秒）
WHITENOISE_INDEX_FILE = True                               # 自动为目录提供 index.html

# 默认主键字段类型
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ==================== 缓存配置 ====================
CACHES = {
    'default': {
        'BACKEND': env('CACHE_BACKEND'),                   # 缓存后端
        'LOCATION': env('CACHE_LOCATION'),                 # 缓存位置
        'OPTIONS': {
            # LocMemCache 专属配置：最大条目数和淘汰频率
            'MAX_ENTRIES': 5000,                           # 内存缓存最大条目数
            'CULL_FREQUENCY': 3,                           # 缓存满时淘汰 1/3 条目
        } if env('CACHE_BACKEND') == 'django.core.cache.backends.locmem.LocMemCache' else {},
    }
}

# ==================== Session 配置 ====================
SESSION_ENGINE = 'django.contrib.sessions.backends.db'     # 使用数据库存储 Session
SESSION_COOKIE_AGE = 1209600                               # Session 过期时间：2 周（秒）
SESSION_SAVE_EVERY_REQUEST = True                          # 每次请求刷新 Session 过期时间

# ==================== CORS 跨域配置 ====================
CORS_ALLOW_ALL_ORIGINS = DEBUG                             # 开发环境允许所有源
CORS_ALLOW_CREDENTIALS = True                              # 允许携带 Cookie
# 生产环境需明确指定允许的源
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[]) if not DEBUG else []

# ==================== 日志配置 ====================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,                     # 保留 Django 内置日志
    'filters': {
        'suppress_bad_auth': {
            '()': 'novel_reader.middleware.SuppressBadAuthLog',  # 恶意请求日志过滤器
        },
    },
    'formatters': {
        'simple': {'format': '[%(levelname)s] %(name)s: %(message)s'},  # 简单格式
        'verbose': {'format': '[%(asctime)s] [%(levelname)s] %(name)s:%(lineno)d: %(message)s'},  # 详细格式
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',              # 控制台输出
            'formatter': 'verbose',                        # 使用详细格式
            'level': 'DEBUG' if DEBUG else 'INFO',         # 开发环境输出 DEBUG，生产环境输出 INFO
            'filters': ['suppress_bad_auth'],              # 应用恶意请求过滤
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',  # 轮转文件输出
            'filename': BASE_DIR / 'data' / 'logs' / 'app.log',  # 日志文件路径
            'maxBytes': 5 * 1024 * 1024,                   # 单文件最大 5MB
            'backupCount': 10,                             # 保留 10 个备份文件
            'formatter': 'verbose',
            'level': 'INFO',
        },
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',  # 错误专用文件
            'filename': BASE_DIR / 'data' / 'logs' / 'errors.log',
            'maxBytes': 5 * 1024 * 1024,
            'backupCount': 5,                              # 保留 5 个备份
            'formatter': 'verbose',
            'level': 'ERROR',                              # 仅记录 ERROR 及以上级别
        },
        'crawler_file': {
            'class': 'logging.handlers.RotatingFileHandler',  # 爬虫专用日志文件
            'filename': BASE_DIR / 'data' / 'logs' / 'crawler.log',
            'maxBytes': 10 * 1024 * 1024,                  # 爬虫日志允许更大（10MB）
            'backupCount': 10,
            'formatter': 'verbose',
            'level': 'INFO',
        },
    },
    'root': {
        'handlers': ['console', 'file', 'error_file'],     # 根日志处理器
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],               # Django 框架日志
            'level': 'INFO',
            'propagate': False,                            # 不向根日志传播
        },
        'django.request': {
            'handlers': ['console', 'error_file'],         # 请求错误日志
            'level': 'ERROR',
            'propagate': False,
        },
        'apps.crawler': {
            'handlers': ['console', 'crawler_file', 'error_file'],  # 爬虫模块日志
            'level': 'DEBUG',                              # 爬虫日志输出所有级别
            'propagate': False,
        },
        'utils.crawler_engine': {
            'handlers': ['console', 'crawler_file', 'error_file'],  # 爬虫引擎工具日志
            'level': 'DEBUG',
            'propagate': False,
        },
        'ninja': {
            'handlers': ['console', 'file'],               # Django Ninja API 日志
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# ==================== 认证 URL 配置 ====================
LOGIN_URL = '/login'                                       # 登录页面 URL
LOGIN_REDIRECT_URL = '/'                                   # 登录后跳转页面
LOGOUT_REDIRECT_URL = '/login'                             # 登出后跳转页面

# ==================== 项目数据目录 ====================
BOOKS_DIR = BASE_DIR / 'data' / 'books'                    # 书籍文件存储目录
LOGS_DIR = BASE_DIR / 'data' / 'logs'                      # 日志文件存储目录
CACHE_DIR = BASE_DIR / 'data' / 'cache'                    # 缓存文件存储目录

# 确保数据目录存在
for _d in [BOOKS_DIR, LOGS_DIR, CACHE_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

# ==================== Celery 异步任务配置 ====================
CELERY_BROKER_URL = env('CELERY_BROKER_URL')               # 消息代理地址（Redis）
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND')       # 任务结果存储地址（Redis）
CELERY_ACCEPT_CONTENT = ['json']                           # 允许的内容类型
CELERY_TASK_SERIALIZER = 'json'                            # 任务序列化格式
CELERY_RESULT_SERIALIZER = 'json'                          # 结果序列化格式
CELERY_TIMEZONE = TIME_ZONE                                # 时区与项目一致
CELERY_TASK_TRACK_STARTED = True                           # 追踪任务开始状态
CELERY_TASK_TIME_LIMIT = 30 * 60                           # 任务超时限制：30 分钟
CELERY_WORKER_PREFETCH_MULTIPLIER = 1                      # 工作进程预取倍数（1 表示不预取）
CELERY_ACKS_LATE = True                                    # 任务完成后确认，保证任务不丢失

# ==================== Django Ninja API 分页配置 ====================
NINJA_PAGINATION_PER_PAGE = 20                             # 默认每页条数
NINJA_PAGINATION_MAX_LIMIT = 100                           # 最大每页条数

# ==================== django-unfold 管理后台配置 ====================
UNFOLD = {
    "SITE_TITLE": "小说阅读器管理后台",                    # 浏览器标题
    "SITE_HEADER": "📖 小说阅读器",                        # 后台顶部标题
    "SITE_SYMBOL": "menu_book",                            # Material Icons 站点图标
    "DASHBOARD_CALLBACK": "apps.books.admin.dashboard_callback",  # Dashboard 数据回调
    "THEME": "dark",                                       # 深色主题
    "COLORS": {
        "primary": {                                       # 主色调：琥珀色系（50-950）
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
        "show_search": True,                               # 显示侧边栏搜索
        "show_all_applications": True,                     # 显示所有应用入口
        "navigation": [
            {
                "title": "数据概览",
                "separator": True,                         # 显示分割线
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

# ==================== 开发环境调试工具配置 ====================
if DEBUG:
    INSTALLED_APPS.insert(0, 'debug_toolbar')              # 在最前面注册调试工具栏应用
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')  # 在最前面注册中间件
    INTERNAL_IPS = ['127.0.0.1', '10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16']  # 内网 IP 段
    DEBUG_TOOLBAR_CONFIG = {
        'SHOW_TOOLBAR_CALLBACK': lambda request: True,     # 始终显示调试工具栏
        'DISABLE_PANELS': {
            'debug_toolbar.panels.redirects.RedirectsPanel',  # 禁用重定向面板（干扰重定向测试）
        },
    }
