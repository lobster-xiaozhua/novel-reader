# Novel Reader — Code Wiki

> 基于 Django 5.2 + React 19 的高性能本地小说阅读平台

---

## 目录

1. [项目概述](#1-项目概述)
2. [整体架构](#2-整体架构)
3. [技术栈与依赖](#3-技术栈与依赖)
4. [后端模块详解](#4-后端模块详解)
5. [前端模块详解](#5-前端模块详解)
6. [数据模型与关系](#6-数据模型与关系)
7. [API 接口文档](#7-api-接口文档)
8. [爬虫系统](#8-爬虫系统)
9. [认证与安全](#9-认证与安全)
10. [配置与部署](#10-配置与部署)
11. [日志体系](#11-日志体系)
12. [测试](#12-测试)
13. [项目运行方式](#13-项目运行方式)

---

## 1. 项目概述

Novel Reader 是一个全栈小说阅读平台，支持：

- 用户注册 / 登录 / 登出（Session 认证）
- 书籍管理（批量导入 TXT、查看、删除）
- 章节阅读（字体调节、键盘翻页、进度保存）
- 收藏功能（收藏 / 取消收藏）
- 阅读统计（每日阅读时长、章节数、字数追踪）
- 全文搜索（基于标题 / 作者 / 描述模糊匹配）
- 网页爬虫（自动抓取小说章节，支持可配置解析规则，Celery 异步执行）
- 深色主题 + 响应式布局
- Docker 一键部署

---

## 2. 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                     浏览器 (SPA)                         │
│         React 19 + Vite + Tailwind CSS + Zustand        │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP (REST API)
                       ▼
┌─────────────────────────────────────────────────────────┐
│              Granian (ASGI Server)                       │
│              Django 5.2 + Django Ninja                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐  │
│  │ accounts │ │  books   │ │ chapters │ │  reader   │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌───────────────────────┐   │
│  │favorites │ │ crawler  │ │    ninja_api (统一)    │   │
│  └──────────┘ └──────────┘ └───────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │              utils/                               │   │
│  │   crawler_engine  │  crawler_config  │ gradient  │   │
│  └──────────────────────────────────────────────────┘   │
└──────────┬──────────────────────┬───────────────────────┘
           │                      │
     ┌─────▼─────┐        ┌──────▼──────┐
     │  SQLite   │        │    Redis    │
     │ (数据库)   │        │ (Celery/缓存)│
     └───────────┘        └─────────────┘
```

**关键设计原则：**

- **前后端分离**：前端 SPA 通过 `/api/v1/` 调用后端 REST API，开发时 Vite 代理，生产时 WhiteNoise 托管前端静态文件
- **统一 API 入口**：所有 API 端点集中在 `apps/ninja_api.py` 一个文件中，使用 Django Ninja 声明式定义
- **异步任务**：爬虫任务通过 Celery + Redis 异步执行，避免阻塞 HTTP 请求
- **文件存储**：章节内容以 `.txt` 文件存储在 `data/books/` 目录，数据库仅存元数据

---

## 3. 技术栈与依赖

### 后端 (Python)

| 分类 | 依赖 | 用途 |
|------|------|------|
| 核心 | Django ≥5.2 | Web 框架 |
| 核心 | django-ninja ≥1.4.0 | REST API 框架（OpenAPI 自动生成） |
| 核心 | pydantic ≥2.11.0 | Schema 验证 |
| 服务器 | granian ≥2.2.0 | ASGI 服务器（生产部署） |
| 服务器 | uvloop ≥0.21.0 | 高性能事件循环 |
| 静态文件 | whitenoise ≥6.9.0 | 静态文件中间件 |
| 环境 | django-environ ≥0.12.0 | 环境变量管理 |
| 后台 | django-unfold ≥0.52.0 | Admin 后台美化 |
| 缓存/队列 | redis ≥5.2.0 | Redis 客户端 |
| 缓存/队列 | celery ≥5.5.0 | 异步任务队列 |
| 爬虫 | requests ≥2.32.0 | HTTP 请求 |
| 爬虫 | beautifulsoup4 ≥4.13.0 | HTML 解析 |
| 爬虫 | httpx[http2] ≥0.28.0 | HTTP/2 客户端 |
| 爬虫 | tenacity ≥9.1.0 | 重试策略 |
| 性能 | orjson ≥3.10.0 | 高性能 JSON 序列化 |
| 安全 | django-cors-headers ≥4.7.0 | CORS 跨域 |
| 测试 | pytest ≥8.4.0 | 测试框架 |
| 测试 | pytest-django ≥4.11.0 | Django 集成 |
| 测试 | pytest-cov ≥6.1.0 | 覆盖率 |
| 代码质量 | ruff ≥0.11.0 | Linter/Formatter |
| 调试 | django-debug-toolbar ≥5.1.0 | 调试工具栏 |

### 前端 (TypeScript)

| 分类 | 依赖 | 用途 |
|------|------|------|
| 核心 | React 19 | UI 框架 |
| 核心 | react-router-dom 7 | 路由 |
| 状态 | zustand 5 | 全局状态管理 |
| 数据 | @tanstack/react-query 5 | 服务端状态/缓存 |
| HTTP | axios | HTTP 客户端 |
| 样式 | Tailwind CSS 4 | 原子化 CSS |
| 图表 | recharts | 数据可视化 |
| 图标 | lucide-react | 图标库 |
| Markdown | react-markdown + remark-gfm + rehype-highlight | Markdown 渲染 |
| 构建 | Vite 8 | 构建工具 |

---

## 4. 后端模块详解

### 4.1 项目配置 — `novel_reader/`

| 文件 | 职责 |
|------|------|
| `settings.py` | 全局配置：数据库、缓存、Celery、日志、中间件、静态文件、Admin 主题 |
| `urls.py` | 根路由：挂载 admin、API、前端 SPA catch-all |
| `asgi.py` | ASGI 入口（Granian 使用） |
| `wsgi.py` | WSGI 入口 |
| `celery.py` | Celery 应用初始化，自动发现 tasks |
| `middleware.py` | 自定义中间件：`DisableCSRFForAPI` |

#### `settings.py` 关键配置项

```python
# 数据库 — 默认 SQLite，支持通过 DATABASE_URL 环境变量切换
DATABASES = {'default': env.db_url(default=f'sqlite:///{BASE_DIR / "data" / "db.sqlite3"}')}

# 缓存 — 默认 LocMemCache，可切换 Redis
CACHES = {'default': {'BACKEND': env('CACHE_BACKEND'), 'LOCATION': env('CACHE_LOCATION')}}

# Celery — broker 和 result backend 均使用 Redis
CELERY_BROKER_URL = env('CELERY_BROKER_URL')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND')

# 静态文件 — WhiteNoise 托管，含前端 dist
STATICFILES_DIRS = [BASE_DIR / 'static', BASE_DIR / 'frontend' / 'dist' / 'static', BASE_DIR / 'frontend' / 'dist']

# Admin — Unfold 深色主题，自定义侧边栏导航
UNFOLD = { "THEME": "dark", "SIDEBAR": {...} }
```

#### `middleware.py` — DisableCSRFForAPI

```python
class DisableCSRFForAPI:
    """对 /api/ 路径跳过 CSRF 校验，API 使用 Session 认证而非 CSRF Token"""
    def __call__(self, request):
        if request.path.startswith('/api/'):
            setattr(request, '_dont_enforce_csrf_checks', True)
        return self.get_response(request)
```

#### `urls.py` — 路由策略

```python
urlpatterns = [
    path('admin/', admin.site.urls),       # Admin 后台
    path('api/v1/', api.urls),             # Django Ninja API
]
# DEBUG 模式：非 static/admin/api/__debug__ 的请求返回前端 SPA
# 生产模式：非 static/admin/api 的请求返回前端 SPA
```

---

### 4.2 统一 API 层 — `apps/ninja_api.py`

**这是整个后端最核心的文件**，所有 REST API 端点集中定义在此，约 795 行。

#### 认证方式

| 认证类 | 用途 | 行为 |
|--------|------|------|
| `OptionalSessionAuth` | 可选认证 | 已登录返回 user，未登录返回 True（允许匿名） |
| `SessionAuthNoCSRF` | 强制认证 | 已登录返回 user，未登录返回 401 |

#### Schema 定义（Pydantic）

| Schema | 用途 |
|--------|------|
| `TagSchema` / `TagListSchema` / `TagIn` | 标签 CRUD |
| `BookListSchema` / `BookDetailSchema` | 书籍列表 / 详情 |
| `ChapterSchema` / `ChapterContentSchema` | 章节列表 / 含内容 |
| `ProgressOut` / `ReadingProgressIn` | 阅读进度 |
| `StatsTrackIn` | 阅读统计上报 |
| `CrawlerTaskSchema` / `CrawlerTaskIn` / `CrawlerTaskDetailSchema` | 爬虫任务 |
| `FavoriteSchema` / `FavoriteToggleIn` | 收藏 |
| `UserSchema` / `LoginIn` / `RegisterIn` / `AuthResponse` | 用户认证 |
| `UserStatsSchema` / `DailyStat` | 阅读统计 |
| `DashboardStatsSchema` / `CategoryStat` | 仪表盘统计 |
| `SearchResponse` / `SearchResult` | 搜索 |
| `HealthSchema` | 健康检查 |
| `BatchImportResult` | 批量导入结果 |

#### 全局异常处理

```python
@api.exception_handler(Exception)
def global_exception_handler(request, exc):
    logger.error(f'API Error: {request.path} - {type(exc).__name__}: {str(exc)}')
    if isinstance(exc, HttpError):
        raise exc
    return api.create_response(request, {'error': str(exc)}, status=500)
```

---

### 4.3 数据模型 — `apps/books/`

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
| `updated_at` | DateTimeField | 更新时间 |

**属性方法：**
- `cover_gradient` — 基于 `book_id` 返回渐变色元组（来自 `utils/book_gradient.py`）
- `chapter_count` — 返回关联章节数量

**索引：**
- `(author, created_at)` — `book_author_created_idx`
- `(category, created_at)` — `book_category_created_idx`

---

### 4.4 数据模型 — `apps/chapters/`

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

---

### 4.5 数据模型 — `apps/reader/`

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

---

### 4.6 数据模型 — `apps/favorites/`

#### `FavoriteFolder` 模型

| 字段 | 类型 | 说明 |
|------|------|------|
| `user` | FK(User, CASCADE) | 用户 |
| `name` | CharField(50) | 文件夹名 |
| `description` | CharField(200) | 描述 |
| `color` | CharField(7) | 颜色 |
| `sort_order` | IntegerField | 排序 |
| `created_at` | DateTimeField | 创建时间 |

#### `Favorite` 模型

| 字段 | 类型 | 说明 |
|------|------|------|
| `user` | FK(User, CASCADE) | 用户 |
| `book` | FK(Book, CASCADE) | 书籍 |
| `folder` | FK(FavoriteFolder, SET_NULL) | 收藏夹（可选） |
| `notes` | CharField(500) | 备注 |
| `created_at` | DateTimeField | 创建时间 |
| `updated_at` | DateTimeField | 更新时间 |

**约束：** `unique_together = ['user', 'book']`

---

### 4.7 数据模型 — `apps/crawler/`

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

---

### 4.8 工具模块 — `utils/`

#### `crawler_engine.py` — 爬虫引擎

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

#### `crawler_config.py` — 爬虫配置

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

**`UA_POOL`** — 内置 16 个主流浏览器 UA（Chrome/Firefox/Safari/Edge/Opera，含移动端）

#### `book_gradient.py` — 封面渐变色

```python
BOOK_GRADIENTS = [('#667eea', '#764ba2'), ('#f093fb', '#f5576c'), ...]  # 8 组渐变色

def get_book_gradient(book_id: int) -> tuple:
    return BOOK_GRADIENTS[book_id % len(BOOK_GRADIENTS)]
```

基于 `book_id` 取模，为每本书分配确定性渐变色。

---

### 4.9 Celery 任务 — `apps/crawler/tasks.py`

```python
@shared_task(bind=True, max_retries=3)
def run_crawler_task(self, task_id):
    task = CrawlerTask.objects.get(id=task_id)
    engine = CrawlerEngine(task.id, str(settings.BOOKS_DIR))
    engine.run(task)
    # 失败时 60s 后重试，最多 3 次
```

---

### 4.10 Admin 后台 — `apps/books/admin.py`

**`dashboard_callback(request, context)`** — Unfold Admin 仪表盘回调

统计卡片：总书籍数、本周/月新增、今日阅读时长/章节/字数、爬虫任务状态

图表数据：分类分布、最近 7 天阅读趋势

---

## 5. 前端模块详解

### 5.1 项目结构

```
frontend/src/
├── api/            # API 调用封装
├── assets/         # 静态资源
├── components/     # 通用组件
├── config/         # 配置常量
├── layout/         # 布局组件
├── stores/         # Zustand 状态管理
├── styles/         # 全局样式
├── types/          # TypeScript 类型定义
├── utils/          # 工具函数
├── views/          # 页面视图
├── App.tsx         # 路由定义
└── main.tsx        # 入口文件
```

### 5.2 入口与路由 — `main.tsx` / `App.tsx`

**`main.tsx`** — 应用入口

- 创建 `QueryClient`（staleTime 5min, retry 1）
- 包裹 `QueryClientProvider` → `BrowserRouter` → `ToastProvider` → `App`
- 将 `useUserStore` 挂载到 `window.__userStore` 供 axios 拦截器使用

**`App.tsx`** — 路由配置

| 路径 | 组件 | 认证 |
|------|------|------|
| `/login` | Login | 无 |
| `/error/403` `/error/404` `/error/500` | ErrorPage | 无 |
| `/` `/dashboard` | Dashboard | AuthGuard |
| `/books` | Books | AuthGuard |
| `/chapters` | Chapters | AuthGuard |
| `/tags` | Tags | AuthGuard |
| `/users` | Users | AuthGuard |
| `/progress` | Progress | AuthGuard |
| `/stats` | Stats | AuthGuard |
| `/favorites` | Favorites | AuthGuard |
| `/crawler` | Crawler | AuthGuard |
| `*` | ErrorPage(404) | — |

### 5.3 状态管理 — `stores/`

#### `appStore.ts` — 应用全局状态

| 状态 | 类型 | 说明 |
|------|------|------|
| `sidebar.opened` | boolean | 侧边栏是否展开 |
| `sidebar.withoutAnimation` | boolean | 是否禁用动画 |
| `device` | 'mobile' \| 'desktop' | 设备类型 |
| `layout` | 'vertical' \| 'horizontal' \| 'mix' | 布局模式 |

持久化到 localStorage，key: `app-store`

#### `userStore.ts` — 用户状态

| 状态 | 类型 | 说明 |
|------|------|------|
| `user` | User \| null | 当前用户信息 |
| `isLoggedIn` | boolean | 是否已登录 |

| 方法 | 说明 |
|------|------|
| `login(user)` | 设置用户并标记已登录 |
| `logout()` | 调用 `/auth/logout/` API 并清除状态 |

持久化到 localStorage，key: `user-store`

#### `tagsStore.ts` — 标签页状态

| 状态 | 类型 | 说明 |
|------|------|------|
| `visitedViews` | TagView[] | 已访问的标签页列表 |
| `cachedViews` | string[] | 需要缓存的组件名列表 |

| 方法 | 说明 |
|------|------|
| `addView(view)` | 添加标签页（去重） |
| `removeView(view)` | 移除标签页 |
| `removeOthers(view)` | 仅保留当前和 Dashboard |
| `removeAll()` | 仅保留 Dashboard |

### 5.4 HTTP 工具 — `utils/http.ts`

基于 axios 封装，统一配置：

- `baseURL`: `/api/v1`
- `timeout`: 30000ms
- `withCredentials`: true（Session Cookie）
- 401 拦截器：自动登出并跳转 `/login`

导出函数：`get<T>()` / `post<T>()` / `put<T>()` / `del<T>()` / `upload<T>()`

### 5.5 API 模块 — `api/`

| 文件 | 函数 | 对应后端端点 |
|------|------|-------------|
| `books.ts` | `fetchBooks` / `fetchBook` / `fetchChapters` / `fetchChapterContent` / `importBooks` | `/books/` `/books/{id}/` `/books/{id}/chapters/` `/books/{id}/chapters/{id}/` `/books/import/` |
| `crawler.ts` | `fetchCrawlerTasks` / `createCrawlerTask` / `fetchCrawlerTask` | `/crawler/` `/crawler/{id}/` |
| `favorites.ts` | `fetchFavorites` / `toggleFavorite` | `/favorites/` `/favorites/toggle/` |
| `progress.ts` | `fetchProgress` / `saveProgress` / `trackStats` | `/progress/` `/progress/track-stats/` |
| `stats.ts` | `fetchStats` / `fetchDashboard` | `/stats/` `/dashboard/` |
| `tags.ts` | `fetchTags` / `createTag` / `deleteTag` | `/tags/` `/tags/{id}/` |
| `users.ts` | `fetchUsers` | `/users/` |

### 5.6 通用组件 — `components/`

| 组件 | 说明 |
|------|------|
| `AuthGuard` | 认证守卫：未登录时调用 `/auth/me/` 检查，失败跳转 `/login` |
| `ErrorBoundary` | React 错误边界，捕获子组件渲染异常 |
| `Loading` | 加载状态组件 |
| `NovelReader` | 小说阅读器核心：字体调节（14-28px）、键盘翻页（←→）、段落缩进排版 |
| `ReDialog` | 对话框组件（含 Provider） |
| `Toast` | 消息提示组件（含 Provider） |

### 5.7 布局组件 — `layout/`

| 组件 | 说明 |
|------|------|
| `Layout` | 主布局：Sidebar + Navbar + TagsView + Outlet，响应式适配 |
| `Sidebar` | 侧边栏：9 个菜单项、折叠/展开、移动端遮罩 |
| `Navbar` | 顶部栏：搜索框、通知按钮、用户信息、登出 |
| `TagsView` | 标签页导航栏 |

### 5.8 页面视图 — `views/`

| 页面 | 说明 |
|------|------|
| `Dashboard` | 仪表盘：统计卡片、分类分布图表 |
| `Books` | 书籍列表：搜索、标签筛选、批量导入、阅读入口 |
| `Chapters` | 章节阅读：使用 NovelReader 组件 |
| `Tags` | 标签管理：创建、删除、颜色选择 |
| `Users` | 用户列表 |
| `Progress` | 阅读进度：所有在读书籍进度 |
| `Stats` | 阅读统计：图表展示每日阅读数据 |
| `Favorites` | 收藏列表：收藏/取消收藏 |
| `Crawler` | 爬虫任务：创建任务、查看进度和日志 |
| `Login` | 登录/注册页面 |
| `ErrorPage` | 错误页面（403/404/500） |

### 5.9 类型定义 — `types/index.ts`

完整 TypeScript 接口定义，与后端 Schema 一一对应：

`Book` / `Tag` / `Chapter` / `CrawlerTask` / `ReadingStats` / `User` / `FavoriteItem` / `ProgressItem` / `StatsData` / `TagItem` / `UserItem` / `MenuItem` / `TagView` / `CategoryStat` / `DashboardStats`

### 5.10 配置常量 — `config/colors.ts`

```typescript
COLORS = { primary: '#f59e0b', success: '#10b981', info: '#3b82f6', ... }
CHART_COLORS = Object.values(COLORS)  // 图表配色
TAG_COLORS = [...]                      // 标签配色（10 色）
```

---

## 6. 数据模型与关系

```
User (Django Auth)
 ├── 1:N ── ReadingProgress  ── N:1 ── Book
 ├── 1:N ── ReadingStats
 ├── 1:N ── Favorite ── N:1 ── Book
 ├── 1:N ── FavoriteFolder ── 1:N ── Favorite
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

> 基础路径：`/api/v1/`
> Swagger 文档：`/api/v1/docs/`

### 7.1 认证接口

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/auth/login/` | 无 | 用户登录 |
| POST | `/auth/register/` | 无 | 用户注册 |
| POST | `/auth/logout/` | Session | 用户登出 |
| GET | `/auth/me/` | 可选 | 获取当前用户信息 |

### 7.2 书籍接口

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | `/books/` | 可选 | 书籍列表（分页，支持 tag/category/search 过滤） |
| POST | `/books/import/` | Session | 批量导入 TXT 文件 |
| GET | `/books/{id}/` | 可选 | 书籍详情（含收藏状态和阅读进度） |
| GET | `/books/{id}/chapters/` | 可选 | 章节列表 |
| GET | `/books/{id}/chapters/{id}/` | 可选 | 章节内容（带缓存） |

### 7.3 阅读进度接口

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | `/progress/` | Session | 阅读进度列表（分页） |
| POST | `/progress/` | Session | 保存/更新阅读进度 |
| POST | `/progress/track-stats/` | Session | 上报阅读统计 |

### 7.4 爬虫接口

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | `/crawler/` | Session | 爬虫任务列表（分页） |
| POST | `/crawler/` | Session | 创建爬虫任务（触发 Celery 异步执行） |
| GET | `/crawler/{id}/` | Session | 爬虫任务详情（含日志） |

### 7.5 标签接口

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | `/tags/` | 可选 | 标签列表（分页，含书籍计数） |
| POST | `/tags/` | Session | 创建标签 |
| DELETE | `/tags/{id}/` | Session | 删除标签 |

### 7.6 收藏接口

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | `/favorites/` | Session | 收藏列表（分页） |
| POST | `/favorites/toggle/` | Session | 切换收藏状态 |

### 7.7 统计接口

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | `/stats/` | Session | 用户阅读统计（支持 days 参数） |
| GET | `/dashboard/` | 可选 | 仪表盘全局统计 |
| GET | `/search/` | 可选 | 搜索书籍（支持 q 参数和自动建议） |

### 7.8 用户接口

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | `/users/` | Session | 用户列表（分页） |

### 7.9 健康检查

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | `/health/` | 无 | 检查数据库、缓存、磁盘状态 |

---

## 8. 爬虫系统

### 8.1 架构流程

```
用户提交 URL
     │
     ▼
API: POST /api/v1/crawler/  →  创建 CrawlerTask(status='pending')
     │
     ▼
Celery Task: run_crawler_task.delay(task_id)
     │
     ▼
CrawlerEngine.run(task)
     │
     ├─ 1. validate_crawl_url()  ── SSRF 防护
     ├─ 2. get_config_for_url()  ── 匹配站点配置
     ├─ 3. _fetch_page()         ── 获取目录页
     ├─ 4. IntelligentParser.parse_book_info()      ── 解析书籍信息
     ├─ 5. IntelligentParser.parse_chapter_list()   ── 解析章节列表
     ├─ 6. 循环每个章节:
     │     ├─ _fetch_page()                          ── 获取章节页
     │     ├─ IntelligentParser.parse_chapter_content() ── 提取正文
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

- **Session 认证**：基于 Django Session + Cookie
- **CSRF 豁免**：API 路径（`/api/`）通过自定义中间件 `DisableCSRFForAPI` 跳过 CSRF 检查
- **CORS**：开发模式允许所有来源，生产模式通过 `CORS_ALLOWED_ORIGINS` 配置

### 9.2 生产安全

当 `DEBUG=False` 时自动启用：

- SSL 重定向 (`SECURE_SSL_REDIRECT`)
- 安全 Cookie (`SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`)
- HSTS (`SECURE_HSTS_SECONDS`, `SECURE_HSTS_INCLUDE_SUBDOMAINS`, `SECURE_HSTS_PRELOAD`)
- 内容类型嗅探防护 (`SECURE_CONTENT_TYPE_NOSNIFF`)
- XSS 过滤 (`SECURE_BROWSER_XSS_FILTER`)
- X-Frame-Options: DENY

### 9.3 前端认证流程

```
用户访问页面
     │
     ▼
AuthGuard 检查 userStore.isLoggedIn
     │
     ├─ true  → 渲染页面
     └─ false → 调用 GET /api/v1/auth/me/
                  │
                  ├─ success + user → login(user) → 渲染页面
                  └─ fail → 跳转 /login
```

---

## 10. 配置与部署

### 10.1 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SECRET_KEY` | 开发用 key | Django 密钥 |
| `DEBUG` | `True` | 调试模式 |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | 允许的主机 |
| `DATABASE_URL` | `sqlite:///data/db.sqlite3` | 数据库连接 |
| `CONN_MAX_AGE` | `60` | 数据库连接最大存活时间 |
| `CACHE_BACKEND` | `locmem` | 缓存后端 |
| `CACHE_LOCATION` | `novelreader-cache` | 缓存位置 |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Celery Broker |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/0` | Celery Result Backend |
| `SECURE_SSL_REDIRECT` | `False` | SSL 重定向 |
| `SECURE_HSTS_SECONDS` | `0` | HSTS 时长 |
| `CORS_ALLOWED_ORIGINS` | `[]` | CORS 允许的来源 |

### 10.2 Docker 部署

**`docker-compose.yml`** 定义三个服务：

| 服务 | 镜像 | 端口 | 说明 |
|------|------|------|------|
| `web` | 自建 (Dockerfile) | 8000 | Django + Granian |
| `celery` | 自建 (Dockerfile) | — | Celery Worker |
| `redis` | `redis:7-alpine` | 6379 | 消息队列 + 缓存 |

**Dockerfile 构建流程：**

1. Python 3.12-slim 基础镜像
2. 安装 gcc + nodejs + npm
3. 安装 Python 依赖
4. 安装前端依赖并构建 (`npm ci` + `npm run build`)
5. 收集静态文件
6. 启动命令：`granian novel_reader.asgi:application --host 0.0.0.0 --port 8000 --interface asgi`

### 10.3 数据目录

```
data/
├── db.sqlite3       # SQLite 数据库
├── books/           # 章节文本文件
│   └── {书名}/
│       ├── 第1章.txt
│       ├── 第2章.txt
│       └── ...
├── logs/
│   ├── app.log      # 应用日志 (5MB 轮转, 10 备份)
│   ├── errors.log   # 错误日志 (5MB 轮转, 5 备份)
│   └── crawler.log  # 爬虫日志 (10MB 轮转, 10 备份)
└── cache/           # 缓存目录
```

---

## 11. 日志体系

### 11.1 日志配置

| Handler | 输出 | 级别 | 轮转策略 |
|---------|------|------|----------|
| `console` | 终端 | DEBUG(开发)/INFO(生产) | — |
| `file` | `data/logs/app.log` | INFO | 5MB × 10 |
| `error_file` | `data/logs/errors.log` | ERROR | 5MB × 5 |
| `crawler_file` | `data/logs/crawler.log` | INFO | 10MB × 10 |

### 11.2 Logger 分层

| Logger | Handler | 级别 | 说明 |
|--------|---------|------|------|
| `django` | console + file | INFO | Django 框架日志 |
| `django.request` | console + error_file | ERROR | HTTP 请求错误 |
| `apps.crawler` | console + crawler_file + error_file | DEBUG | 爬虫应用日志 |
| `utils.crawler_engine` | console + crawler_file + error_file | DEBUG | 爬虫引擎日志 |
| `ninja` | console + file | INFO | API 框架日志 |
| `root` | console + file + error_file | INFO | 全局兜底 |

### 11.3 格式

```
[2026-05-23 10:00:00] [INFO] apps.crawler:42: 任务 1: 开始执行
```

---

## 12. 测试

### 12.1 配置

- 框架：pytest + pytest-django
- 配置文件：`pytest.ini`
- 测试目录：`tests/`
- 运行命令：`pytest` 或 `pytest --cov=apps`

### 12.2 测试用例

| 测试类 | 测试内容 |
|--------|----------|
| `CrawlerConfigTest` | 默认配置验证、URL 匹配配置、URL 安全验证 |
| `IntelligentParserTest` | HTML 内容清理（去除 script）、章节列表解析（过滤 skip_keywords） |
| `BookGradientTest` | 渐变色返回类型、确定性、取模循环 |

---

## 13. 项目运行方式

### 13.1 Docker 一键启动（推荐）

```bash
docker-compose up -d
docker-compose exec web python manage.py rebuild_index  # 初始化搜索索引
```

访问 http://localhost:8000，默认账号 `admin` / `admin123`

### 13.2 启动脚本

```bash
./start.sh start     # 生产模式（安装依赖 → 迁移 → 构建前端 → Granian）
./start.sh dev       # 开发模式（Django runserver + Vite dev server）
./start.sh stop      # 停止服务
./start.sh restart   # 重启服务
./start.sh status    # 查看服务状态
./start.sh migrate   # 执行数据库迁移
./start.sh build     # 构建前端
```

### 13.3 手动启动

```bash
# 安装依赖
pip install -r requirements.txt
cd frontend && npm ci && cd ..

# 数据库迁移
python manage.py migrate

# 构建前端
cd frontend && npm run build && cd ..

# 收集静态文件
python manage.py collectstatic --noinput

# 启动 Celery Worker（另一终端）
celery -A novel_reader worker --loglevel=info

# 启动 Web 服务器
granian novel_reader.asgi:application --host 0.0.0.0 --port 8000 --interface asgi --workers 1
```

### 13.4 开发模式

```bash
# 终端 1：后端
python manage.py runserver 0.0.0.0:8000

# 终端 2：前端（Vite 开发服务器，自动代理 /api → localhost:8000）
cd frontend && npm run dev
```

前端开发服务器：http://localhost:5173
后端 API：http://localhost:8000
API 文档：http://localhost:8000/api/v1/docs/
Admin 后台：http://localhost:8000/admin/
