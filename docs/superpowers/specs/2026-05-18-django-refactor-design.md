# Novel Reader Django 重构设计文档

## 项目概述

将现有的 FastAPI + Vue 3 + Vite 前后端分离架构，重构为 Django + Django Templates + 原生 JavaScript 的单体架构。删除所有 Vue/Vite 相关代码，使用 Django ORM 替代 SQLAlchemy，使用 Django 内置认证替代 JWT。

## 目标

- 简化技术栈，减少构建步骤
- 使用 Django 的 admin、auth、ORM 等内置功能
- 保留所有核心功能：用户认证、书籍管理、章节阅读、收藏、爬虫、搜索
- 不使用 Docker，支持本地直接运行

## 技术栈

- **后端框架**: Django 4.2 LTS
- **数据库**: Django ORM + SQLite（保留）
- **模板引擎**: Django Templates
- **前端**: 原生 JavaScript (ES6) + CSS3
- **任务队列**: Django Q（轻量级，替代 Celery）
- **HTTP 客户端**: 原生 fetch API
- **CSS 框架**: 自定义 CSS（保留深色主题）

## 架构设计

### 目录结构

```
novel_reader/
├── manage.py
├── novel_reader/              # 项目配置
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── accounts/              # 用户认证（替代原有auth）
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── forms.py
│   ├── books/                 # 书籍管理
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── forms.py
│   ├── chapters/              # 章节管理
│   │   ├── models.py
│   │   ├── views.py
│   │   └── urls.py
│   ├── reader/                # 阅读进度
│   │   ├── models.py
│   │   ├── views.py
│   │   └── urls.py
│   ├── favorites/             # 收藏功能
│   │   ├── models.py
│   │   ├── views.py
│   │   └── urls.py
│   ├── crawler/               # 爬虫任务
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── tasks.py
│   └── search/                # 全文搜索
│       ├── views.py
│       └── urls.py
├── templates/                 # Django HTML模板
│   ├── base.html
│   ├── home.html
│   ├── accounts/
│   │   ├── login.html
│   │   └── register.html
│   ├── books/
│   │   ├── list.html
│   │   ├── detail.html
│   │   └── add.html
│   ├── chapters/
│   │   └── read.html
│   ├── favorites/
│   │   └── list.html
│   ├── crawler/
│   │   └── tasks.html
│   └── search/
│       └── results.html
├── static/                    # CSS/JS静态文件
│   ├── css/
│   │   └── main.css
│   └── js/
│       ├── app.js
│       ├── reader.js
│       └── crawler.js
├── utils/                     # 工具模块
│   ├── crawler_engine.py      # 爬虫核心逻辑
│   └── search_engine.py       # 搜索核心逻辑
└── data/                      # 数据目录
    ├── db.sqlite3
    ├── books/
    ├── logs/
    └── cache/
```

### 模型映射

| 原 SQLAlchemy 模型 | Django 模型 | App | 说明 |
|-------------------|------------|-----|------|
| `User` | `django.contrib.auth.models.User` | accounts | 使用Django内置User，扩展Profile |
| `Book` | `Book` | books | 保留所有字段 |
| `Chapter` | `Chapter` | chapters | 保留所有字段，外键关联Book |
| `ReadingProgress` | `ReadingProgress` | reader | 保留所有字段 |
| `Favorite` | `Favorite` | favorites | 保留所有字段 |
| `FavoriteFolder` | `FavoriteFolder` | favorites | 保留所有字段 |
| `Tag` | `Tag` | books | 保留所有字段 |
| `CrawlerTask` | `CrawlerTask` | crawler | 保留所有字段 |

### URL 路由映射

| 原 Vue 路由 | Django URL | 视图 | 说明 |
|------------|-----------|------|------|
| `/` | `/` | `home` | 首页 |
| `/books` | `/books/` | `book_list` | 书架列表 |
| `/books/:id` | `/books/<int:pk>/` | `book_detail` | 书籍详情 |
| `/reader/:bookId/:chapterId` | `/reader/<int:book_id>/<int:chapter_id>/` | `chapter_read` | 阅读页面 |
| `/search` | `/search/` | `search_results` | 搜索结果 |
| `/crawler` | `/crawler/` | `crawler_tasks` | 爬虫管理 |
| `/login` | `/accounts/login/` | `login` | 登录（Django内置） |
| `/register` | `/accounts/register/` | `register` | 注册 |
| `/favorites` | `/favorites/` | `favorite_list` | 收藏列表 |

### 视图设计

#### 函数视图 vs 类视图

- **列表页**（books, favorites, crawler tasks）：使用 `ListView` CBV
- **详情页**（book detail, chapter read）：使用 `DetailView` 或函数视图
- **表单页**（login, register, add book）：使用 `FormView` 或函数视图 + Django Forms
- **AJAX接口**（save progress, refresh task）：使用 `@require_POST` 函数视图返回 JsonResponse

#### 认证方式

- 使用 Django 内置 `SessionAuthentication`
- 登录/登出使用 `django.contrib.auth` 的 views
- 注册使用自定义 `UserCreationForm`
- 受保护页面使用 `@login_required` 装饰器

### 模板设计

#### base.html 布局

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}小说阅读器{% endblock %}</title>
    <link rel="stylesheet" href="{% static 'css/main.css' %}">
</head>
<body>
    <nav class="navbar">
        <!-- 导航栏：Logo、链接、用户区域 -->
    </nav>
    <main class="main-content">
        {% block content %}{% endblock %}
    </main>
    <script src="{% static 'js/app.js' %}"></script>
    {% block extra_js %}{% endblock %}
</body>
</html>
```

#### 页面模板列表

1. **home.html** - 首页仪表盘，统计卡片 + 最近阅读 + 快速操作
2. **books/list.html** - 书架列表，分页 + 搜索 + 添加按钮
3. **books/detail.html** - 书籍详情，封面 + 元信息 + 章节目录
4. **chapters/read.html** - 阅读器，工具栏 + 内容 + 导航
5. **accounts/login.html** - 登录表单
6. **accounts/register.html** - 注册表单
7. **search/results.html** - 搜索结果
8. **crawler/tasks.html** - 爬虫任务列表 + 创建表单
9. **favorites/list.html** - 收藏列表

### 静态文件

#### CSS (main.css)

保留原有深色主题设计系统：
- CSS 变量定义颜色系统
- 通用工具类（.btn, .input, .card, .page-container）
- 响应式布局
- 阅读器专用样式

#### JavaScript

- **app.js** - 通用功能：导航栏交互、表单验证、AJAX辅助函数
- **reader.js** - 阅读器功能：字体调节、进度保存、章节导航
- **crawler.js** - 爬虫页面：任务状态轮询

### 业务逻辑迁移

#### 爬虫服务 (crawler_engine.py)

将原有的 `CrawlerService` 迁移为同步版本（Django ORM 同步）：
- `IntelligentParser` 类保持不变
- `DynamicConcurrencyController` 改为同步信号量
- 使用 `requests` 替代 `aiohttp`
- 使用 `threading` 替代 `asyncio`
- 使用 Django Q 进行后台任务调度

#### 搜索服务 (search_engine.py)

保留 SQLite FTS5 实现：
- 使用 Django ORM 的 `raw()` 执行 FTS5 查询
- 保留触发器自动同步索引

#### 扫描服务

将 `BookScanner` 改为同步版本：
- 使用标准文件 I/O 替代 `aiofiles`
- 保留目录扫描和书籍注册逻辑

### 数据流设计

```
用户请求 → Django URLConf → View → Model → SQLite
                              ↓
                         Template → HTML + CSS + JS → 浏览器
                              ↓
                         AJAX → JsonResponse → 局部更新
```

### 认证流程

```
登录页 (GET) → 显示表单
登录页 (POST) → 验证 → Django login() → 重定向首页
注册页 (POST) → UserCreationForm → 创建用户 → 自动登录
受保护页面 → @login_required → 未登录重定向登录页
```

## 部署方式

### 本地开发

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### 生产环境

使用 Gunicorn + Nginx（可选）：

```bash
gunicorn novel_reader.wsgi:application --bind 0.0.0.0:8000
```

### 跨平台支持

- 保留 `start.sh` 和 `deploy.sh` 脚本，适配 Django 命令
- Termux 支持：使用 SQLite，无需 Redis

## 删除的内容

- 整个 `frontend/` 目录（Vue、Vite、Pinia、Axios）
- 整个 `backend/` 目录下的 FastAPI 代码
- `app/services/update_service.py`
- `app/services/version_service.py`
- `app/services/cache_service.py`（使用 Django 缓存框架）
- JWT 认证相关代码
- Docker 相关文件（Dockerfile, docker-compose.yml）
- Pydantic Schemas（使用 Django Forms）

## 保留的核心功能

1. 用户注册/登录/登出
2. 书籍 CRUD（创建、列表、详情、删除）
3. 章节阅读（字体调节、进度保存、上一章/下一章）
4. 收藏功能（添加/取消收藏）
5. 爬虫任务管理（创建任务、查看状态）
6. 全文搜索（标题、作者）
7. 搜索建议
8. 阅读进度保存和恢复
9. 跨平台部署支持

## 开发顺序

1. 创建 Django 项目和 App 结构
2. 配置 settings.py（数据库、静态文件、模板）
3. 创建所有 Models
4. 创建数据库迁移并执行
5. 创建基础模板（base.html）和 CSS
6. 实现用户认证（登录/注册）
7. 实现书籍列表和详情页
8. 实现章节阅读页
9. 实现收藏功能
10. 实现搜索功能
11. 实现爬虫功能
12. 实现首页仪表盘
13. 添加 JavaScript 交互
14. 测试和调试
