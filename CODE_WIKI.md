# Novel Reader - Code Wiki

> 基于 Django 5.2 + Next.js 16 的高性能本地小说阅读平台

---

## 目录

1. [项目概述](#1-项目概述)
2. [整体架构](#2-整体架构)
3. [技术栈与依赖](#3-技术栈与依赖)
4. [后端模块详解](#4-后端模块详解)
5. [前端模块详解](#5-前端模块详解)
6. [数据模型与关系](#6-数据模型与关系)
7. [API 接口文档](#7-API-接口文档)
8. [爬虫系统](#8-爬虫系统)
9. [认证与安全](#9-认证与安全)
10. [配置与部署](#10-配置与部署)
11. [日志体系](#11-日志体系)
12. [项目运行方式](#12-项目运行方式)

---

## 1. 项目概述

Novel Reader 是一个全栈小说阅读平台，支持：

- 用户注册 / 登录 / 登出（Session + JWT 双认证）
- 书籍管理（本地目录、批量导入 TXT）
- 章节阅读（字体调节、键盘翻页、进度保存）
- 收藏功能
- 阅读统计（每日阅读时长、章节数、字数追踪）
- 全文搜索
- 网页爬虫（自动抓取小说章节，支持可配置解析规则，Celery 异步执行）
- 推荐系统
- 深色主题 + 响应式布局
- Docker 一键部署
- 多层缓存系统（Redis + DiskCache）
- API 性能监控
- 速率限制

---

## 2. 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        浏览器 (Next.js SPA)                      │
│              React 19 + Next.js 16 + Tailwind CSS + Zustand      │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTP (REST API)
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Granian (ASGI Server)                         │
│                    Django 5.2 + Django Ninja                     │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ Middleware Stack                                           │ │
│  │ ├─ Debug Toolbar (Dev)                                    │ │
│  │ ├─ Security Middleware                                    │ │
│  │ ├─ WhiteNoise (Static Files)                              │ │
│  │ ├─ CORS Headers                                           │ │
│  │ ├─ Session Management                                     │ │
│  │ ├─ APIMonitorMiddleware (性能监控)                         │ │
│  │ ├─ RequestTimingMiddleware (请求计时)                      │ │
│  │ ├─ JWTAuthMiddleware (JWT认证)                              │ │
│  │ └─ LoginRateLimitMiddleware (登录限流)                      │ │
│  └───────────────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                         APIs                                │ │
│  │  ┌──────────────┐  ┌───────────────────────────────────┐  │ │
│  │  │  API v1      │  │          API v2 (新)               │  │ │
│  │  │ (旧版，兼容)  │  │  ├─ /auth/ (认证)                  │  │ │
│  │  └──────────────┘  │  ├─ /reader/ (读者功能)            │  │ │
│  │                     │  └─ /admin/ (管理功能)             │  │ │
│  │                     └───────────────────────────────────┘  │ │
│  └───────────────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                      业务模块                               │ │
│  │  accounts  books  chapters  reader  favorites  crawler     │ │
│  │  search  recommender  config                               │ │
│  └───────────────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                        工具层                                │ │
│  │  crawler_engine  crawler_config  book_gradient             │ │
│  └───────────────────────────────────────────────────────────┘ │
└───────────────┬────────────────────┬───────────────────────────┘
                │                    │
         ┌──────▼──────┐     ┌───────▼────────┐
         │ PostgreSQL  │     │     Redis      │
         │ (主数据库)   │     │ (缓存 + Celery)│
         └─────────────┘     └────────────────┘
         ┌─────────────┐
         │  DiskCache  │
         │ (大对象缓存)│
         └─────────────┘
```

**关键设计原则：**

- **前后端分离**：前端采用 Next.js 16，通过 `/api/v1/` 或 `/api/v2/` 调用后端 REST API
- **双版本 API**：提供 v1（兼容旧版）和 v2（reader/admin 分离）两个 API 版本
- **统一 API 入口**：使用 Django Ninja 声明式定义 API
- **异步任务**：爬虫任务通过 Celery + Redis 异步执行，避免阻塞 HTTP 请求
- **文件存储**：章节内容以 `.txt` 文件存储，数据库仅存元数据，支持外挂书籍目录
- **多层缓存**：Redis 做热点数据缓存，DiskCache 做大对象缓存（推荐向量、搜索结果）
- **完善的中间件**：性能监控、请求计时、JWT 认证、登录限流

---

## 3. 技术栈与依赖

### 后端 (Python)

| 分类 | 依赖 | 版本 | 用途 |
|------|------|------|------|
| 核心 | Django | ≥5.2 | Web 框架 |
| 核心 | django-ninja | ≥1.4.0 | REST API 框架（OpenAPI 自动生成） |
| 核心 | pydantic | ≥2.11.0 | Schema 验证 |
| 核心 | PyJWT | ≥2.9.0 | JWT 认证 |
| 服务器 | granian | ≥2.2.0 | ASGI 服务器（生产部署） |
| 服务器 | uvloop | ≥0.21.0 | 高性能事件循环（非 Windows） |
| 静态文件 | whitenoise | ≥6.9.0 | 静态文件中间件 |
| 环境 | django-environ | ≥0.12.0 | 环境变量管理 |
| 后台 | django-unfold | ≥0.52.0 | Admin 后台美化 |
| 数据库 | psycopg[binary] | ≥3.2.0 | PostgreSQL 驱动 |
| 缓存/队列 | redis | ≥5.2.0 | Redis 客户端 |
| 缓存/队列 | django-redis | ≥5.4.0 | Django Redis 集成 |
| 缓存/队列 | diskcache | ≥5.6.0 | 磁盘缓存 |
| 缓存/队列 | celery | ≥5.5.0 | 异步任务队列 |
| 爬虫 | requests | ≥2.32.0 | HTTP 请求 |
| 爬虫 | beautifulsoup4 | ≥4.13.0 | HTML 解析 |
| 爬虫 | httpx[http2] | ≥0.28.0 | HTTP/2 客户端 |
| 爬虫 | tenacity | ≥9.1.0 | 重试策略 |
| 性能 | orjson | ≥3.10.0 | 高性能 JSON 序列化 |
| 安全 | django-cors-headers | ≥4.7.0 | CORS 跨域 |
| 测试 | pytest | ≥8.4.0 | 测试框架 |
| 测试 | pytest-django | ≥4.11.0 | Django 集成 |
| 测试 | pytest-cov | ≥6.1.0 | 覆盖率 |
| 代码质量 | ruff | ≥0.11.0 | Linter/Formatter |
| 调试 | django-debug-toolbar | ≥5.1.0 | 调试工具栏 |

### 前端 (TypeScript)

| 分类 | 依赖 | 版本 | 用途 |
|------|------|------|------|
| 核心 | React | 19.2.4 | UI 框架 |
| 核心 | Next.js | 16.2.7 | React 框架 |
| 路由 | Next.js App Router | 16.2.7 | 路由管理 |
| 状态 | zustand | 5.0.14 | 全局状态管理 |
| 数据 | @tanstack/react-query | 5.101.0 | 服务端状态/缓存 |
| 样式 | Tailwind CSS | 4 | 原子化 CSS |
| 图表 | recharts | 3.8.1 | 数据可视化 |
| 图标 | lucide-react | 1.17.0 | 图标库 |
| 构建 | Next.js Build | 16.2.7 | 构建工具 |

---

## 4. 后端模块详解

### 4.1 项目配置 - `novel_reader/`

| 文件 | 职责 |
|------|------|
| `settings.py` | 全局配置：数据库、缓存、Celery、日志、中间件、静态文件、Admin 主题 |
| `urls.py` | 根路由：挂载 admin（/sys-admin/）、API v1/v2 |
| `asgi.py` | ASGI 入口（Granian 使用） |
| `wsgi.py` | WSGI 入口 |
| `celery.py` | Celery 应用初始化，自动发现 tasks |
| `middleware.py` | 自定义中间件：APIMonitor、RequestTiming、JWTAuth、LoginRateLimit、SuppressBadAuthLog |

#### `settings.py` 关键配置项

```python
# 数据库 — 默认 PostgreSQL，支持通过 DATABASE_URL 环境变量切换
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('PG_DB', default='novel_reader'),
        'USER': env('PG_USER', default='novel_user'),
        'PASSWORD': env('PG_PASSWORD', default='novel_pass'),
        'HOST': env('PG_HOST', default='localhost'),
        'PORT': env('PG_PORT', default='5432'),
    }
}

# 分层缓存系统
if REDIS_AVAILABLE:
    CACHES = {
        'default': {  # Redis，热点数据，5min TTL
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
        },
        'disk': {  # DiskCache，大对象，24h TTL
            'BACKEND': 'diskcache.DjangoCache',
            'LOCATION': CACHE_DIR / 'diskcache',
        },
    }
else:
    CACHES = {  # 降级到 DiskCache
        'default': { 'BACKEND': 'diskcache.DjangoCache', ... },
        'disk': { 'BACKEND': 'diskcache.DjangoCache', ... },
    }

# Celery — broker 和 result backend 均使用 Redis
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')

# 静态文件 — WhiteNoise 托管，支持多种 Next.js 构建输出位置
STATICFILES_DIRS = [BASE_DIR / 'static']
for d in ['.next/static', 'out/static', 'dist/static', 'dist']:
    if (BASE_DIR / 'frontend' / d).is_dir():
        STATICFILES_DIRS.append(BASE_DIR / 'frontend' / d)

# 外挂书籍目录
BOOKS_EXTRA_DIRS = [Path(d) for d in env('BOOKS_EXTRA_DIRS', default='').split(':') if d.strip()]
BOOKS_ROOTS = [BOOKS_DIR] + BOOKS_EXTRA_DIRS

# JWT 配置
JWT_SECRET = env('JWT_SECRET', default=SECRET_KEY)
JWT_ACCESS_LIFETIME_MINUTES = env.int('JWT_ACCESS_LIFETIME_MINUTES', default=15)
JWT_REFRESH_LIFETIME_DAYS = env.int('JWT_REFRESH_LIFETIME_DAYS', default=7)
```

#### `middleware.py` - 中间件详解

| 中间件 | 职责 |
|--------|------|
| `APIMonitorMiddleware` | API 性能监控：统计 QPS、错误率、各路径响应时间 |
| `RequestTimingMiddleware` | 请求计时：记录每个请求的响应时间、慢请求告警 |
| `JWTAuthMiddleware` | JWT 认证：从 Authorization header 提取 token 并认证用户，支持用户缓存 |
| `LoginRateLimitMiddleware` | 登录限流：每 IP 每分钟最多 5 次登录尝试 |
| `SuppressBadAuthLog` | 日志过滤：抑制无用的 Bad Auth 日志 |

### 4.2 API v1 - `apps/api/`

**（兼容旧版，所有路由在同一文件中）**

| 文件 | 职责 |
|------|------|
| `router.py` | API 入口，挂载所有路由 |
| `schemas.py` | Pydantic Schema 定义 |
| `auth.py` | JWT 认证工具函数 |
| `routes_*.py` | 各模块路由 |

### 4.3 API v2 - `backend/api_v2/`

**（新版，reader/admin 分离）**

| 模块 | 职责 |
|------|------|
| `auth/` | 认证相关路由：登录、注册、登出、获取用户信息 |
| `reader/` | 读者功能路由：书籍、章节、阅读进度、收藏、统计 |
| `admin/` | 管理功能路由：书籍管理、爬虫、用户管理、监控 |
| `schemas.py` | 统一响应格式：`ApiResponse` |

**响应格式示例：**
```typescript
// 成功
{ "success": true, "data": {...}, "message": "" }

// 失败
{ "success": false, "data": null, "message": "错误信息" }
```

### 4.4 数据模型 - `apps/books/`

#### `Tag` 模型

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | CharField(30, unique) | 标签名，带索引 |
| `color` | CharField(7) | 颜色代码，默认 `#f59e0b` |
| `created_at` | DateTimeField | 创建时间 |

#### `Book` 模型

| 字段 | 类型 | 说明 |
|------|------|------|
| `title` | CharField(200) | 书名，带索引 |
| `author` | CharField(100) | 作者，带索引 |
| `category` | CharField(50) | 分类，带索引 |
| `folder_path` | CharField(500, unique) | 文件夹路径 |
| `description` | TextField | 简介 |
| `tags` | ManyToManyField(Tag) | 标签多对多 |
| `total_chapters` | PositiveIntegerField | 总章节数 |
| `created_at` | DateTimeField | 创建时间 |
| `updated_at` | DateTimeField | 更新时间，带索引 |

**属性方法：**
- `cover_gradient` — 基于 `book_id` 返回渐变色元组（来自 `utils/book_gradient.py`）
- `chapter_count` — 返回关联章节数量

**索引：**
- `(author, created_at)` — `book_author_created_idx`
- `(category, created_at)` — `book_category_created_idx`

### 4.5 数据模型 - `apps/chapters/`

#### `Chapter` 模型

| 字段 | 类型 | 说明 |
|------|------|------|
| `book` | FK(Book, CASCADE) | 所属书籍 |
| `chapter_number` | PositiveIntegerField | 章节号 |
| `title` | CharField(200) | 章节标题 |
| `file_path` | CharField(500) | 文件路径 |
| `word_count` | PositiveIntegerField | 字数 |
| `created_at` | DateTimeField | 创建时间 |

**约束：** `unique_together = ['book', 'chapter_number']`

**索引：** `(book, chapter_number)` — `chapter_book_num_idx`

### 4.6 数据模型 - `apps/reader/`

#### `ReadingProgress` 模型

| 字段 | 类型 | 说明 |
|------|------|------|
| `user` | FK(User, CASCADE) | 用户 |
| `book` | FK(Book, CASCADE) | 书籍 |
| `chapter` | FK(Chapter, SET_NULL) | 当前章节 |
| `position` | PositiveIntegerField | 阅读位置 |
| `updated_at` | DateTimeField | 更新时间 |

**约束：** `unique_together = ['user', 'book']` — 每用户每书仅一条进度

#### `ReadingStats` 模型

| 字段 | 类型 | 说明 |
|------|------|------|
| `user` | FK(User, CASCADE) | 用户 |
| `date` | DateField | 日期 |
| `read_seconds` | PositiveIntegerField | 阅读秒数 |
| `chapters_read` | PositiveIntegerField | 阅读章节数 |
| `words_read` | PositiveIntegerField | 阅读字数 |

**约束：** `unique_together = ['user', 'date']` — 每用户每天一条统计

### 4.7 数据模型 - `apps/favorites/`

#### `Favorite` 模型

| 字段 | 类型 | 说明 |
|------|------|------|
| `user` | FK(User, CASCADE) | 用户 |
| `book` | FK(Book, CASCADE) | 书籍 |
| `created_at` | DateTimeField | 创建时间 |

**约束：** `unique_together = ['user', 'book']`

### 4.8 数据模型 - `apps/crawler/`

#### `CrawlerTask` 模型

| 字段 | 类型 | 说明 |
|------|------|------|
| `user` | FK(User, CASCADE) | 创建者 |
| `url` | URLField | 目标 URL |
| `status` | CharField(20) | 状态：pending / running / completed / failed / cancelled |
| `book` | FK(Book, SET_NULL) | 关联书籍 |
| `total_chapters` | PositiveIntegerField | 总章节数 |
| `downloaded_chapters` | PositiveIntegerField | 已下载数 |
| `error_message` | TextField | 错误信息 |
| `logs` | TextField | JSON 格式日志 |
| `created_at` / `updated_at` | DateTimeField | 时间戳 |

### 4.9 工具模块 - `utils/`

#### `crawler_engine.py` - 爬虫引擎

**核心类：`CrawlerEngine`**

| 方法 | 说明 |
|------|------|
| `run(task)` | 执行完整爬取流程：URL 验证 → 获取页面 → 解析书籍信息 → 解析章节列表 → 逐章下载 → 保存文件和数据库 |
| `stop()` | 设置停止标志，取消正在进行的任务 |
| `_fetch_page(session, url)` | 带重试的 HTTP 请求，指数退避 + 随机 UA |
| `_delay()` | 随机延迟（0.5x~1.5x 配置延迟） |
| `_get_ua()` | 从 UA 池随机选择 User-Agent |
| `_get_proxy()` | 获取代理配置 |
| `_safe_filename(name)` | 清理文件名中的非法字符 |
| `_append_log(task, message)` | 追加 JSON 日志到任务记录 |

**核心类：`IntelligentParser`**

| 方法 | 说明 |
|------|------|
| `parse_chapter_list(html, base_url)` | 使用配置的 CSS 选择器解析章节列表 |
| `parse_chapter_content(html)` | 使用配置的 CSS 选择器提取正文内容 |
| `parse_book_info(html)` | 提取书名、作者、简介 |
| `_clean_content(element)` | 清理 HTML：移除 script/style/iframe，提取段落文本 |

**安全函数：`validate_crawl_url(url)`**

- 验证 URL scheme（仅 http/https）
- 阻止 SSRF 攻击（禁止访问内网 IP、元数据地址）
- DNS 解析后检查 IP 是否为私有地址

#### `crawler_config.py` - 爬虫配置

**核心数据类：`SiteConfig`**

| 字段 | 说明 |
|------|------|
| `name` | 站点名称 |
| `domain` | 域名匹配规则 |
| `chapter_list_selectors` | 章节列表 CSS 选择器列表 |
| `content_selectors` | 正文内容 CSS 选择器列表 |
| `title_selector` | 书名选择器 |
| `author_selector` | 作者选择器 |
| `description_selector` | 简介选择器 |
| `link_selector` | 链接选择器（默认 `a[href]`） |
| `skip_keywords` | 跳过的关键词列表 |
| `request_delay` | 请求间隔（秒） |
| `user_agents` | 自定义 UA 池 |
| `cookies` | 自定义 Cookies |
| `use_proxy` / `proxy_url` | 代理配置 |
| `retry_delay` / `max_retries` | 重试策略 |

**配置查找：** `get_config_for_url(url)` — 根据 URL 域名匹配 `SITE_CONFIGS`，未匹配则返回 `DEFAULT_CONFIG`

**`UA_POOL`** — 内置多个主流浏览器 UA（Chrome/Firefox/Safari/Edge/Opera，含移动端）

#### `book_gradient.py` - 封面渐变色

```python
BOOK_GRADIENTS = [('#667eea', '#764ba2'), ('#f093fb', '#f5576c'), ...]

def get_book_gradient(book_id: int) -> tuple:
    return BOOK_GRADIENTS[book_id % len(BOOK_GRADIENTS)]
```

基于 `book_id` 取模，为每本书分配确定性渐变色。

### 4.10 Celery 任务 - `apps/crawler/tasks.py`

```python
@shared_task(bind=True, max_retries=3)
def run_crawler_task(self, task_id):
    task = CrawlerTask.objects.get(id=task_id)
    engine = CrawlerEngine(task.id, str(settings.BOOKS_DIR))
    engine.run(task)
    # 失败时 60s 后重试，最多 3 次
```

### 4.11 新增模块

#### `apps/recommender/` - 推荐系统

| 文件 | 职责 |
|------|------|
| `engine.py` | 推荐引擎核心 |
| `search.py` | 搜索相关推荐 |
| `management/commands/init_engines.py` | 初始化推荐引擎命令 |

#### `apps/search/` - 搜索服务

| 文件 | 职责 |
|------|------|
| `mappings.py` | 搜索索引映射 |
| `services.py` | 搜索服务 |

#### `apps/config/` - 系统配置

| 文件 | 职责 |
|------|------|
| `models.py` | 系统配置模型 |

---

## 5. 前端模块详解

### 5.1 项目结构

```
frontend/
├── app/
│   ├── (admin)/
│   │   └── admin/
│   │       ├── page.tsx              # 管理后台首页
│   │       ├── books/
│   │       │   ├── page.tsx          # 书籍管理
│   │       │   └── [id]/
│   │       │       └── page.tsx      # 书籍详情编辑
│   │       ├── crawler/
│   │       │   └── page.tsx          # 爬虫管理
│   │       ├── monitor/
│   │       │   └── page.tsx          # 系统监控
│   │       ├── tags/
│   │       │   └── page.tsx          # 标签管理
│   │       └── users/
│   │           └── page.tsx          # 用户管理
│   ├── (reader)/
│   │   ├── page.tsx                  # 首页
│   │   ├── login/
│   │   │   └── page.tsx              # 登录页
│   │   ├── book/
│   │   │   └── [id]/
│   │   │       └── page.tsx          # 书籍详情
│   │   ├── read/
│   │   │   └── [id]/
│   │   │       └── page.tsx          # 阅读页
│   │   ├── search/
│   │   │   └── page.tsx              # 搜索页
│   │   ├── shelf/
│   │   │   └── page.tsx              # 书架
│   │   └── stats/
│   │       └── page.tsx              # 统计页
│   ├── layout.tsx                    # 根布局
│   ├── _global-error/
│   │   └── page.tsx                  # 全局错误页
│   └── _not-found/
│       └── page.tsx                  # 404 页
├── .next/                            # Next.js 构建输出
├── package.json
└── tsconfig.json
```

### 5.2 核心依赖

- **Next.js 16 App Router** - 文件系统路由
- **React 19** - UI 框架
- **Zustand 5** - 状态管理
- **@tanstack/react-query 5** - 数据获取与缓存
- **Tailwind CSS 4** - 样式
- **Lucide React** - 图标
- **Recharts** - 图表

### 5.3 页面路由

| 路径 | 组件 | 说明 |
|------|------|------|
| `/` | 首页 | 推荐书籍、最新更新 |
| `/login` | 登录页 | 登录/注册 |
| `/book/[id]` | 书籍详情 | 书籍信息、章节列表 |
| `/read/[id]` | 阅读页 | 章节阅读、进度保存 |
| `/search` | 搜索页 | 全文搜索 |
| `/shelf` | 书架 | 收藏的书籍 |
| `/stats` | 统计页 | 阅读统计图表 |
| `/admin` | 管理后台 | 管理员入口 |
| `/admin/books` | 书籍管理 | 书籍增删改查 |
| `/admin/crawler` | 爬虫管理 | 爬虫任务监控 |
| `/admin/monitor` | 系统监控 | API 性能、系统状态 |

---

## 6. 数据模型与关系

```
User (Django Auth)
 ├── 1:N ── ReadingProgress  ── N:1 ── Book
 ├── 1:N ── ReadingStats
 ├── 1:N ── Favorite ── N:1 ── Book
 └── 1:N ── CrawlerTask ── N:1 ── Book

Book
 ├── M:N ── Tag (through books_tags)
 ├── 1:N ── Chapter
 ├── 1:N ── ReadingProgress
 ├── 1:N ── Favorite
 └── 1:N ── CrawlerTask

Chapter
 └── N:1 ── Book
      └── 1:N ── ReadingProgress (chapter FK)
```

---

## 7. API 接口文档

> API v1 基础路径：`/api/v1/`
> API v2 基础路径：`/api/v2/`
> Swagger 文档：
> - v1: `/api/v1/docs/`
> - v2: `/api/v2/docs/`

### 7.1 API v1 接口（兼容版）

#### 认证接口

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/auth/login/` | 无 | 用户登录 |
| POST | `/auth/register/` | 无 | 用户注册 |
| POST | `/auth/logout/` | Session/JWT | 用户登出 |
| GET | `/auth/me/` | 可选 | 获取当前用户信息 |

#### 书籍接口

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | `/books/` | 可选 | 书籍列表（分页，支持 tag/category/search 过滤） |
| POST | `/books/import/` | Session/JWT | 批量导入 TXT 文件 |
| GET | `/books/{id}/` | 可选 | 书籍详情（含收藏状态和阅读进度） |
| GET | `/books/{id}/chapters/` | 可选 | 章节列表 |
| GET | `/books/{id}/chapters/{id}/` | 可选 | 章节内容（带缓存） |

#### 阅读进度接口

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | `/progress/` | Session/JWT | 阅读进度列表（分页） |
| POST | `/progress/` | Session/JWT | 保存/更新阅读进度 |
| POST | `/progress/track-stats/` | Session/JWT | 上报阅读统计 |

#### 爬虫接口

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | `/crawler/` | Session/JWT | 爬虫任务列表（分页） |
| POST | `/crawler/` | Session/JWT | 创建爬虫任务（触发 Celery 异步执行） |
| GET | `/crawler/{id}/` | Session/JWT | 爬虫任务详情（含日志） |

#### 标签接口

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | `/tags/` | 可选 | 标签列表（分页，含书籍计数） |
| POST | `/tags/` | Session/JWT | 创建标签 |
| DELETE | `/tags/{id}/` | Session/JWT | 删除标签 |

#### 收藏接口

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | `/favorites/` | Session/JWT | 收藏列表（分页） |
| POST | `/favorites/toggle/` | Session/JWT | 切换收藏状态 |

#### 统计接口

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | `/stats/` | Session/JWT | 用户阅读统计（支持 days 参数） |
| GET | `/dashboard/` | 可选 | 仪表盘全局统计 |
| GET | `/search/` | 可选 | 搜索书籍（支持 q 参数和自动建议） |

#### 用户接口

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | `/users/` | Session/JWT | 用户列表（分页） |

#### 健康检查

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | `/health/` | 无 | 检查数据库、缓存、磁盘状态 |

### 7.2 API v2 接口（新版）

#### 统一响应格式

```typescript
interface ApiResponse<T> {
  success: boolean;
  data: T | null;
  message: string;
}
```

#### 认证模块 (`/api/v2/auth/`)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/login` | 登录 |
| POST | `/register` | 注册 |
| POST | `/logout` | 登出 |
| GET | `/me` | 获取当前用户 |

#### 读者模块 (`/api/v2/reader/`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/books` | 书籍列表 |
| GET | `/books/:id` | 书籍详情 |
| GET | `/books/:id/chapters` | 章节列表 |
| GET | `/chapters/:id` | 章节内容 |
| POST | `/progress` | 保存进度 |
| POST | `/favorites/toggle` | 切换收藏 |
| GET | `/stats` | 阅读统计 |

#### 管理模块 (`/api/v2/admin/`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/books` | 书籍管理列表 |
| POST | `/books/import` | 导入书籍 |
| GET | `/crawler/tasks` | 爬虫任务 |
| POST | `/crawler/tasks` | 创建爬虫任务 |
| GET | `/monitor/stats` | 系统监控统计 |
| GET | `/users` | 用户列表 |

---

## 8. 爬虫系统

### 8.1 架构流程

```
用户提交 URL
     │
     ▼
API: POST /api/v1/crawler/ → 创建 CrawlerTask(status='pending')
     │
     ▼
Celery Task: run_crawler_task.delay(task_id)
     │
     ▼
CrawlerEngine.run(task)
     │
     ├─ 1. validate_crawl_url() → SSRF 防护
     ├─ 2. get_config_for_url() → 匹配站点配置
     ├─ 3. _fetch_page() → 获取目录页
     ├─ 4. IntelligentParser.parse_book_info() → 解析书籍信息
     ├─ 5. IntelligentParser.parse_chapter_list() → 解析章节列表
     ├─ 6. 循环每个章节:
     │     ├─ _fetch_page() → 获取章节页
     │     ├─ IntelligentParser.parse_chapter_content() → 提取正文
     │     ├─ 写入 .txt 文件
     │     └─ 创建/更新 Chapter 记录
     └─ 7. 更新 Book.total_chapters, CrawlerTask.status='completed'
```

### 8.2 安全机制

- **SSRF 防护**：`validate_crawl_url()` 阻止对内网 IP、元数据地址的请求
- **DNS 重绑定防护**：解析域名后检查 IP 是否为私有地址
- **请求限速**：`request_delay` 配置 + 随机抖动
- **UA 轮换**：从 UA 池随机选择 User-Agent
- **重试策略**：指数退避 + 随机抖动，最多 3 次

### 8.3 扩展新站点

在 `utils/crawler_config.py` 的 `SITE_CONFIGS` 中添加配置：

```python
SITE_CONFIGS = {
    "new-site.com": SiteConfig(
        name="New Novel Site",
        domain="new-site.com",
        chapter_list_selectors=["#chapter-list"],
        content_selectors=["#content"],
        title_selector="h1.title",
        author_selector=".author",
        request_delay=1.0,
    ),
}
```

---

## 9. 认证与安全

### 9.1 认证方式

- **Session 认证**：基于 Django Session + Cookie（适合 Web 端）
- **JWT 认证**：基于 JWT Token（适合 API 调用、移动端）
- **双认证支持**：`JWTAuthMiddleware` 会在 Session 未认证时尝试 JWT 认证
- **用户缓存**：JWT 认证后的用户会缓存 5 分钟，减少数据库查询

### 9.2 JWT 认证流程

```
用户登录 → 后端验证 → 返回 access_token + refresh_token
     │
     ▼
后续请求 → Authorization: Bearer <access_token>
     │
     ▼
JWTAuthMiddleware → 验证 token → 缓存用户 → request.user 设置
```

### 9.3 生产安全

当 `DEBUG=False` 时自动启用：

- SSL 重定向 (`SECURE_SSL_REDIRECT`)
- 安全 Cookie (`SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`)
- HSTS (`SECURE_HSTS_SECONDS`, `SECURE_HSTS_INCLUDE_SUBDOMAINS`, `SECURE_HSTS_PRELOAD`)
- 内容类型嗅探防护 (`SECURE_CONTENT_TYPE_NOSNIFF`)
- XSS 过滤 (`SECURE_BROWSER_XSS_FILTER`)
- X-Frame-Options: DENY

### 9.4 速率限制

- **登录接口**：每 IP 每分钟最多 5 次尝试
- **API 监控**：记录所有请求的响应时间，统计 QPS 和错误率

---

## 10. 配置与部署

### 10.1 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SECRET_KEY` | 自动生成（开发） | Django 密钥 |
| `DEBUG` | `False` | 调试模式 |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1,0.0.0.0` | 允许的主机 |
| `PG_DB` | `novel_reader` | PostgreSQL 数据库名 |
| `PG_USER` | `novel_user` | PostgreSQL 用户名 |
| `PG_PASSWORD` | `novel_pass` | PostgreSQL 密码 |
| `PG_HOST` | `localhost` | PostgreSQL 主机 |
| `PG_PORT` | `5432` | PostgreSQL 端口 |
| `DATABASE_URL` | - | 数据库连接 URL（覆盖 PG 配置） |
| `CONN_MAX_AGE` | `60` | 数据库连接最大存活时间 |
| `REDIS_URL` | `redis://localhost:6379/1` | Redis 缓存 URL |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Celery Broker |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/0` | Celery Result Backend |
| `BOOKS_EXTRA_DIRS` | - | 外挂书籍目录（冒号分隔） |
| `JWT_SECRET` | `SECRET_KEY` | JWT 签名密钥 |
| `JWT_ACCESS_LIFETIME_MINUTES` | `15` | Access Token 有效期（分钟） |
| `JWT_REFRESH_LIFETIME_DAYS` | `7` | Refresh Token 有效期（天） |
| `SECURE_SSL_REDIRECT` | `False` | SSL 重定向 |
| `SECURE_HSTS_SECONDS` | `0` | HSTS 时长 |
| `CORS_ALLOWED_ORIGINS` | - | CORS 允许的来源（逗号分隔） |

### 10.2 Docker 部署

**`docker-compose.yml` 定义三个服务：**

| 服务 | 镜像 | 端口 | 说明 |
|------|------|------|------|
| `web` | 自建 (Dockerfile) | 8000 | Django + Granian |
| `celery` | 自建 (Dockerfile) | - | Celery Worker |
| `redis` | `redis:7-alpine` | 6379 | 消息队列 + 缓存 |

**启动命令：**
```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f web celery

# 停止服务
docker-compose down
```

### 10.3 数据目录

```
data/
├── db.sqlite3          # SQLite 数据库（如果使用 SQLite）
├── books/              # 章节文本文件
│   └── {书名}/
│       ├── 第1章.txt
│       ├── 第2章.txt
│       └── ...
├── cache/              # DiskCache 缓存目录
│   └── diskcache/
├── logs/
│   ├── app.log         # 应用日志 (5MB 轮转, 10 备份)
│   ├── errors.log      # 错误日志 (5MB 轮转, 5 备份)
│   ├── requests.log    # 请求日志 (10MB 轮转, 10 备份)
│   ├── auth.log        # 认证日志 (5MB 轮转, 5 备份)
│   └── crawler.log     # 爬虫日志 (10MB 轮转, 10 备份)
└── book_dirs.json      # 保存的外挂目录配置
```

---

## 11. 日志体系

### 11.1 日志配置

| Handler | 输出 | 级别 | 轮转策略 |
|---------|------|------|----------|
| `console` | 终端 | DEBUG(开发)/INFO(生产) | - |
| `file` | `data/logs/app.log` | INFO | 5MB × 10 |
| `error_file` | `data/logs/errors.log` | ERROR | 5MB × 5 |
| `request_file` | `data/logs/requests.log` | INFO | 10MB × 10 |
| `auth_file` | `data/logs/auth.log` | INFO | 5MB × 5 |
| `crawler_file` | `data/logs/crawler.log` | INFO | 10MB × 10 |

### 11.2 Logger 分层

| Logger | Handler | 级别 | 说明 |
|--------|---------|------|------|
| `django` | console + file | INFO | Django 框架日志 |
| `django.request` | console + error_file | ERROR | HTTP 请求错误 |
| `django.db.backends` | console + file | DEBUG(开发)/INFO | 数据库查询 |
| `novel_reader.request` | console + request_file + file | INFO | 请求日志 |
| `novel_reader.auth` | console + auth_file + file + error_file | INFO | 认证日志 |
| `apps.crawler` | console + crawler_file + error_file | DEBUG | 爬虫应用日志 |
| `utils.crawler_engine` | console + crawler_file + error_file | DEBUG | 爬虫引擎日志 |
| `ninja` | console + file | INFO | API 框架日志 |
| `root` | console + file + error_file | INFO | 全局兜底 |

### 11.3 格式

```
[2026-06-07 10:00:00] [INFO] novel_reader.request:123: GET /api/v1/books/ | status=200 | 0.023s | size=1234B | user=admin(id=1) | ip=127.0.0.1
```

---

## 12. 项目运行方式

### 12.1 Docker 一键部署（推荐）

```bash
# 复制环境变量模板（可选）
cp .env.example .env
# 编辑 .env 文件配置

# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

访问 http://localhost:8000

默认管理员账号会自动创建，密码可通过 `ADMIN_PASSWORD` 环境变量设置。

### 12.2 本地开发

#### 后端开发

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 数据库迁移
python manage.py migrate

# 启动 Redis（需要单独安装或使用 Docker）
docker run -d -p 6379:6379 redis:7-alpine

# 启动 Celery Worker（另一个终端）
celery -A novel_reader worker --loglevel=info

# 启动 Django 开发服务器
python manage.py runserver
```

#### 前端开发

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端开发服务器：http://localhost:3000
后端 API：http://localhost:8000
API v1 文档：http://localhost:8000/api/v1/docs/
API v2 文档：http://localhost:8000/api/v2/docs/
Admin 后台：http://localhost:8000/sys-admin/

### 12.3 构建与生产运行

```bash
# 构建前端
cd frontend
npm run build
cd ..

# 收集静态文件
python manage.py collectstatic --noinput

# 使用 Granian 启动
granian novel_reader.asgi:application --host 0.0.0.0 --port 8000 --interface asginl --workers 2
```
