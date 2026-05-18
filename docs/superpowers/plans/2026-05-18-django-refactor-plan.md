# Novel Reader Django 重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 FastAPI + Vue 3 + Vite 架构重构为 Django + Django Templates + 原生 JavaScript 单体架构，删除所有 Vue/Vite 代码。

**Architecture:** 使用 Django 4.2 LTS 作为全栈框架，Django ORM 管理 SQLite 数据库，Django Templates 渲染 HTML，原生 JavaScript 处理前端交互。爬虫使用 threading 后台执行。

**Tech Stack:** Django 4.2, SQLite, Django Templates, Vanilla JS, CSS3

---

## 项目结构

```
novel_reader/
├── manage.py
├── novel_reader/              # 项目配置
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── accounts/              # 用户认证
│   ├── books/                 # 书籍管理
│   ├── chapters/              # 章节管理
│   ├── reader/                # 阅读进度
│   ├── favorites/             # 收藏功能
│   ├── crawler/               # 爬虫任务
│   └── search/                # 全文搜索
├── templates/                 # Django HTML模板
├── static/                    # CSS/JS静态文件
├── utils/                     # 工具模块
└── data/                      # 数据目录
```

---

## Task 1: 清理旧代码并创建 Django 项目结构

**Files:**
- Delete: `frontend/`, `backend/`, `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`
- Create: `novel_reader/`, `apps/`, `templates/`, `static/`, `utils/`, `data/`

- [ ] **Step 1: 删除旧的前后端代码**

```bash
cd /workspace
rm -rf frontend backend docker-compose.yml .dockerignore
rm -f deploy.ps1 deploy.py deploy.sh deploy-termux.sh
rm -f start.bat start.ps1 start.sh
rm -f update.py update.sh version.py
rm -rf scripts/
```

- [ ] **Step 2: 创建新目录结构**

```bash
mkdir -p novel_reader
mkdir -p apps/accounts apps/books apps/chapters apps/reader apps/favorites apps/crawler apps/search
mkdir -p templates/accounts templates/books templates/chapters templates/favorites templates/crawler templates/search
mkdir -p static/css static/js
mkdir -p utils
mkdir -p data/books data/logs data/cache
```

- [ ] **Step 3: 创建 requirements.txt**

Create: `/workspace/requirements.txt`

```text
Django>=4.2,<5.0
requests>=2.31.0
beautifulsoup4>=4.12.0
tenacity>=8.2.0
```

- [ ] **Step 4: 安装依赖**

```bash
pip install -r requirements.txt
```

---

## Task 2: 创建 Django 项目和配置

**Files:**
- Create: `novel_reader/__init__.py`, `novel_reader/settings.py`, `novel_reader/urls.py`, `novel_reader/wsgi.py`
- Create: `manage.py`

- [ ] **Step 1: 创建 manage.py**

Create: `/workspace/manage.py`

```python
#!/usr/bin/env python
import os
import sys

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'novel_reader.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)
```

- [ ] **Step 2: 创建 settings.py**

Create: `/workspace/novel_reader/settings.py`

```python
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-dev-key-change-in-production')

DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'apps.accounts',
    'apps.books',
    'apps.chapters',
    'apps.reader',
    'apps.favorites',
    'apps.crawler',
    'apps.search',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'novel_reader.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
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
STATICFILES_DIRS = [BASE_DIR / 'static']

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# Custom settings
BOOKS_DIR = BASE_DIR / 'data' / 'books'
LOGS_DIR = BASE_DIR / 'data' / 'logs'
CACHE_DIR = BASE_DIR / 'data' / 'cache'
```

- [ ] **Step 3: 创建 urls.py**

Create: `/workspace/novel_reader/urls.py`

```python
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('apps.accounts.urls')),
    path('books/', include('apps.books.urls')),
    path('chapters/', include('apps.chapters.urls')),
    path('reader/', include('apps.reader.urls')),
    path('favorites/', include('apps.favorites.urls')),
    path('crawler/', include('apps.crawler.urls')),
    path('search/', include('apps.search.urls')),
    path('', include('apps.books.urls_home')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
```

- [ ] **Step 4: 创建 wsgi.py**

Create: `/workspace/novel_reader/wsgi.py`

```python
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'novel_reader.settings')
application = get_wsgi_application()
```

- [ ] **Step 5: 创建 __init__.py**

Create: `/workspace/novel_reader/__init__.py`

```python
```

---

## Task 3: 创建所有 Django Apps 的模型

**Files:**
- Create: `apps/accounts/models.py`, `apps/books/models.py`, `apps/chapters/models.py`, `apps/reader/models.py`, `apps/favorites/models.py`, `apps/crawler/models.py`
- Create: 各 app 的 `__init__.py`, `apps.py`

- [ ] **Step 1: 创建 apps/books/models.py**

Create: `/workspace/apps/books/models.py`

```python
from django.db import models


class Book(models.Model):
    title = models.CharField(max_length=200, db_index=True, verbose_name='书名')
    author = models.CharField(max_length=100, db_index=True, blank=True, verbose_name='作者')
    folder_path = models.CharField(max_length=500, unique=True, verbose_name='文件夹路径')
    description = models.TextField(blank=True, verbose_name='简介')
    total_chapters = models.PositiveIntegerField(default=0, verbose_name='总章节数')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '书籍'
        verbose_name_plural = '书籍'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name='标签名')
    color = models.CharField(max_length=7, blank=True, verbose_name='颜色')

    class Meta:
        verbose_name = '标签'
        verbose_name_plural = '标签'

    def __str__(self):
        return self.name


class BookTag(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name='书籍')
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, verbose_name='标签')

    class Meta:
        unique_together = ['book', 'tag']
        verbose_name = '书籍标签'
        verbose_name_plural = '书籍标签'
```

- [ ] **Step 2: 创建 apps/chapters/models.py**

Create: `/workspace/apps/chapters/models.py`

```python
from django.db import models
from apps.books.models import Book


class Chapter(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='chapters', verbose_name='书籍')
    chapter_number = models.PositiveIntegerField(verbose_name='章节号')
    title = models.CharField(max_length=200, verbose_name='标题')
    file_path = models.CharField(max_length=500, verbose_name='文件路径')
    word_count = models.PositiveIntegerField(default=0, verbose_name='字数')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '章节'
        verbose_name_plural = '章节'
        ordering = ['chapter_number']
        unique_together = ['book', 'chapter_number']

    def __str__(self):
        return f'{self.book.title} - 第{self.chapter_number}章 {self.title}'
```

- [ ] **Step 3: 创建 apps/reader/models.py**

Create: `/workspace/apps/reader/models.py`

```python
from django.db import models
from django.contrib.auth.models import User
from apps.books.models import Book
from apps.chapters.models import Chapter


class ReadingProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name='书籍')
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, verbose_name='章节')
    position = models.PositiveIntegerField(default=0, verbose_name='阅读位置')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '阅读进度'
        verbose_name_plural = '阅读进度'
        unique_together = ['user', 'book']

    def __str__(self):
        return f'{self.user.username} - {self.book.title}'
```

- [ ] **Step 4: 创建 apps/favorites/models.py**

Create: `/workspace/apps/favorites/models.py`

```python
from django.db import models
from django.contrib.auth.models import User
from apps.books.models import Book


class FavoriteFolder(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    name = models.CharField(max_length=50, verbose_name='文件夹名')
    description = models.CharField(max_length=200, blank=True, verbose_name='描述')
    color = models.CharField(max_length=7, blank=True, verbose_name='颜色')
    sort_order = models.IntegerField(default=0, verbose_name='排序')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '收藏夹'
        verbose_name_plural = '收藏夹'
        ordering = ['sort_order', 'created_at']

    def __str__(self):
        return self.name


class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name='书籍')
    folder = models.ForeignKey(FavoriteFolder, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='收藏夹')
    notes = models.CharField(max_length=500, blank=True, verbose_name='备注')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '收藏'
        verbose_name_plural = '收藏'
        unique_together = ['user', 'book']

    def __str__(self):
        return f'{self.user.username} - {self.book.title}'
```

- [ ] **Step 5: 创建 apps/crawler/models.py**

Create: `/workspace/apps/crawler/models.py`

```python
from django.db import models
from django.contrib.auth.models import User
from apps.books.models import Book


class CrawlerTask(models.Model):
    STATUS_CHOICES = [
        ('pending', '等待中'),
        ('running', '运行中'),
        ('completed', '已完成'),
        ('failed', '失败'),
        ('cancelled', '已取消'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    url = models.URLField(max_length=500, verbose_name='目标URL')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='状态')
    book = models.ForeignKey(Book, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='关联书籍')
    total_chapters = models.PositiveIntegerField(default=0, verbose_name='总章节数')
    downloaded_chapters = models.PositiveIntegerField(default=0, verbose_name='已下载章节数')
    error_message = models.TextField(blank=True, verbose_name='错误信息')
    logs = models.TextField(blank=True, verbose_name='日志')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '爬虫任务'
        verbose_name_plural = '爬虫任务'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.url} ({self.get_status_display()})'
```

- [ ] **Step 6: 创建各 app 的 apps.py**

Create: `/workspace/apps/books/apps.py`

```python
from django.apps import AppConfig

class BooksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.books'
    verbose_name = '书籍管理'
```

Create: `/workspace/apps/chapters/apps.py`

```python
from django.apps import AppConfig

class ChaptersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.chapters'
    verbose_name = '章节管理'
```

Create: `/workspace/apps/reader/apps.py`

```python
from django.apps import AppConfig

class ReaderConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.reader'
    verbose_name = '阅读进度'
```

Create: `/workspace/apps/favorites/apps.py`

```python
from django.apps import AppConfig

class FavoritesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.favorites'
    verbose_name = '收藏管理'
```

Create: `/workspace/apps/crawler/apps.py`

```python
from django.apps import AppConfig

class CrawlerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.crawler'
    verbose_name = '爬虫任务'
```

Create: `/workspace/apps/accounts/apps.py`

```python
from django.apps import AppConfig

class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'
    verbose_name = '用户认证'
```

Create: `/workspace/apps/search/apps.py`

```python
from django.apps import AppConfig

class SearchConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.search'
    verbose_name = '搜索'
```

- [ ] **Step 7: 创建所有 __init__.py**

Create empty `__init__.py` in:
- `/workspace/apps/__init__.py`
- `/workspace/apps/accounts/__init__.py`
- `/workspace/apps/books/__init__.py`
- `/workspace/apps/chapters/__init__.py`
- `/workspace/apps/reader/__init__.py`
- `/workspace/apps/favorites/__init__.py`
- `/workspace/apps/crawler/__init__.py`
- `/workspace/apps/search/__init__.py`

- [ ] **Step 8: 执行数据库迁移**

```bash
cd /workspace
python manage.py makemigrations accounts books chapters reader favorites crawler search
python manage.py migrate
```

---

## Task 4: 创建基础模板和静态文件

**Files:**
- Create: `templates/base.html`, `static/css/main.css`, `static/js/app.js`

- [ ] **Step 1: 创建 base.html**

Create: `/workspace/templates/base.html`

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}小说阅读器{% endblock %}</title>
    {% load static %}
    <link rel="stylesheet" href="{% static 'css/main.css' %}">
</head>
<body>
    <nav class="navbar">
        <div class="nav-brand">
            <a href="{% url 'home' %}">📖 小说阅读器</a>
        </div>
        <div class="nav-links">
            <a href="{% url 'home' %}" class="{% if request.path == '/' %}active{% endif %}">首页</a>
            <a href="{% url 'book_list' %}" class="{% if '/books/' in request.path %}active{% endif %}">书架</a>
            <a href="{% url 'search' %}" class="{% if '/search/' in request.path %}active{% endif %}">搜索</a>
            <a href="{% url 'crawler_tasks' %}" class="{% if '/crawler/' in request.path %}active{% endif %}">爬虫</a>
        </div>
        <div class="nav-user">
            {% if user.is_authenticated %}
                <span class="username">{{ user.username }}</span>
                <a href="{% url 'logout' %}" class="btn btn-secondary btn-sm">退出</a>
            {% else %}
                <a href="{% url 'login' %}" class="btn btn-primary btn-sm">登录</a>
            {% endif %}
        </div>
    </nav>

    <main class="main-content">
        {% if messages %}
            <div class="messages">
                {% for message in messages %}
                    <div class="alert alert-{{ message.tags }}">{{ message }}</div>
                {% endfor %}
            </div>
        {% endif %}
        {% block content %}{% endblock %}
    </main>

    <script src="{% static 'js/app.js' %}"></script>
    {% block extra_js %}{% endblock %}
</body>
</html>
```

- [ ] **Step 2: 创建 main.css**

Create: `/workspace/static/css/main.css`

```css
:root {
    --bg-primary: #0f172a;
    --bg-secondary: #1e293b;
    --bg-hover: #334155;
    --text-primary: #f1f5f9;
    --text-secondary: #94a3b8;
    --text-tertiary: #64748b;
    --accent: #f59e0b;
    --accent-hover: #d97706;
    --border-color: #334155;
    --danger: #ef4444;
    --success: #22c55e;
    --info: #3b82f6;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg-primary);
    color: var(--text-primary);
    line-height: 1.6;
    min-height: 100vh;
}

/* Navbar */
.navbar {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    height: 64px;
    background: rgba(15, 23, 42, 0.95);
    backdrop-filter: blur(10px);
    border-bottom: 1px solid var(--border-color);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 32px;
    z-index: 100;
}

.nav-brand a {
    font-size: 20px;
    font-weight: 700;
    color: var(--accent);
    text-decoration: none;
}

.nav-links {
    display: flex;
    gap: 24px;
}

.nav-links a {
    color: var(--text-secondary);
    text-decoration: none;
    font-size: 15px;
    font-weight: 500;
    transition: color 0.2s;
    padding: 8px 12px;
    border-radius: 8px;
}

.nav-links a:hover,
.nav-links a.active {
    color: var(--accent);
    background: rgba(245, 158, 11, 0.1);
}

.nav-user {
    display: flex;
    align-items: center;
    gap: 12px;
}

.username {
    color: var(--text-secondary);
    font-size: 14px;
}

/* Main Content */
.main-content {
    max-width: 1200px;
    margin: 0 auto;
    padding: 88px 24px 40px;
}

/* Page Title */
.page-title {
    font-size: 28px;
    font-weight: 700;
    margin-bottom: 24px;
    color: var(--text-primary);
}

.page-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 24px;
}

/* Buttons */
.btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 10px 20px;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    border: 1px solid transparent;
    text-decoration: none;
}

.btn-primary {
    background: var(--accent);
    color: #fff;
    border-color: var(--accent);
}

.btn-primary:hover {
    background: var(--accent-hover);
    border-color: var(--accent-hover);
}

.btn-secondary {
    background: transparent;
    color: var(--text-secondary);
    border-color: var(--border-color);
}

.btn-secondary:hover {
    border-color: var(--accent);
    color: var(--accent);
}

.btn-danger {
    background: transparent;
    color: var(--danger);
    border-color: var(--danger);
}

.btn-danger:hover {
    background: var(--danger);
    color: #fff;
}

.btn-sm {
    padding: 6px 14px;
    font-size: 13px;
}

.btn-full {
    width: 100%;
    padding: 12px;
    font-size: 15px;
}

/* Inputs */
.input {
    width: 100%;
    padding: 12px 16px;
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 10px;
    color: var(--text-primary);
    font-size: 14px;
    transition: border-color 0.2s;
}

.input:focus {
    outline: none;
    border-color: var(--accent);
}

.input::placeholder {
    color: var(--text-tertiary);
}

textarea.input {
    resize: vertical;
    min-height: 80px;
}

/* Form Group */
.form-group {
    margin-bottom: 16px;
}

.form-label {
    display: block;
    font-size: 14px;
    color: var(--text-secondary);
    margin-bottom: 6px;
}

/* Cards */
.card {
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 24px;
    transition: all 0.3s;
}

.card:hover {
    border-color: var(--accent);
    transform: translateY(-2px);
}

/* Book Card */
.book-card {
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 20px;
    cursor: pointer;
    transition: all 0.3s;
}

.book-card:hover {
    border-color: var(--accent);
    transform: translateY(-2px);
}

.book-card-title {
    font-size: 16px;
    font-weight: 600;
    margin-bottom: 8px;
    color: var(--text-primary);
}

.book-card-author {
    font-size: 13px;
    color: var(--text-secondary);
    margin-bottom: 8px;
}

.book-card-desc {
    font-size: 13px;
    color: var(--text-tertiary);
    line-height: 1.6;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

.book-card-meta {
    font-size: 12px;
    color: var(--text-tertiary);
    margin-top: 12px;
}

/* Grid */
.books-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
    gap: 16px;
}

.stats-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin-bottom: 40px;
}

.stat-card {
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 24px;
    text-align: center;
    transition: all 0.3s;
}

.stat-card:hover {
    border-color: var(--accent);
    transform: translateY(-2px);
}

.stat-icon {
    font-size: 28px;
    margin-bottom: 8px;
}

.stat-value {
    font-size: 32px;
    font-weight: 700;
    color: var(--accent);
    margin-bottom: 4px;
}

.stat-label {
    font-size: 13px;
    color: var(--text-tertiary);
}

/* Quick Actions */
.quick-actions {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
}

.action-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    padding: 32px 24px;
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    text-decoration: none;
    color: var(--text-primary);
    transition: all 0.3s;
}

.action-card:hover {
    border-color: var(--accent);
    transform: translateY(-2px);
    color: var(--accent);
}

.action-icon {
    font-size: 36px;
}

.action-text {
    font-size: 15px;
    font-weight: 500;
}

/* Section */
.section {
    margin-bottom: 40px;
}

.section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
}

.section-title {
    font-size: 20px;
    font-weight: 600;
    color: var(--text-primary);
}

.section-link {
    font-size: 14px;
    color: var(--accent);
    text-decoration: none;
}

/* Pagination */
.pagination {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 16px;
    margin-top: 24px;
}

.page-info {
    font-size: 14px;
    color: var(--text-secondary);
}

/* Empty State */
.empty-state {
    text-align: center;
    padding: 60px 24px;
}

.empty-icon {
    font-size: 48px;
    margin-bottom: 16px;
}

.empty-text {
    font-size: 15px;
    color: var(--text-tertiary);
}

/* Loading */
.loading-spinner {
    text-align: center;
    padding: 40px;
    color: var(--text-secondary);
}

/* Modal */
.modal-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.6);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 200;
}

.modal {
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 16px;
    padding: 32px;
    width: 90%;
    max-width: 480px;
}

.modal-title {
    font-size: 20px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 24px;
}

.modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
    margin-top: 24px;
}

/* Alerts */
.alert {
    padding: 12px 16px;
    border-radius: 8px;
    margin-bottom: 16px;
    font-size: 14px;
}

.alert-success {
    background: rgba(34, 197, 94, 0.1);
    color: var(--success);
    border: 1px solid rgba(34, 197, 94, 0.2);
}

.alert-error {
    background: rgba(239, 68, 68, 0.1);
    color: var(--danger);
    border: 1px solid rgba(239, 68, 68, 0.2);
}

.alert-info {
    background: rgba(59, 130, 246, 0.1);
    color: var(--info);
    border: 1px solid rgba(59, 130, 246, 0.2);
}

/* Login Page */
.login-page {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
}

.login-card {
    width: 100%;
    max-width: 400px;
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 16px;
    padding: 40px 32px;
}

.login-header {
    text-align: center;
    margin-bottom: 32px;
}

.login-icon {
    font-size: 48px;
    display: block;
    margin-bottom: 12px;
}

.login-title {
    font-size: 24px;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 4px;
}

.login-subtitle {
    font-size: 14px;
    color: var(--text-tertiary);
}

.login-form {
    display: flex;
    flex-direction: column;
    gap: 16px;
}

.login-footer {
    text-align: center;
    margin-top: 24px;
    font-size: 14px;
    color: var(--text-tertiary);
}

.login-footer a {
    color: var(--accent);
    font-weight: 500;
    text-decoration: none;
}

.error-msg {
    font-size: 13px;
    color: var(--danger);
    padding: 8px 12px;
    background: rgba(239, 68, 68, 0.1);
    border-radius: 6px;
}

/* Search */
.search-box {
    display: flex;
    gap: 12px;
    margin-bottom: 24px;
}

.search-input {
    flex: 1;
}

.suggestions {
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 10px;
    overflow: hidden;
    margin-bottom: 24px;
}

.suggestion-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    cursor: pointer;
    transition: background 0.2s;
}

.suggestion-item:hover {
    background: var(--bg-hover);
}

.suggestion-item + .suggestion-item {
    border-top: 1px solid var(--border-color);
}

/* Book Detail */
.book-header {
    display: flex;
    gap: 32px;
    margin-bottom: 40px;
    padding: 32px;
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 16px;
}

.book-cover-large {
    flex-shrink: 0;
    width: 160px;
    height: 220px;
    background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 48px;
}

.book-meta-info {
    flex: 1;
    min-width: 0;
}

.book-title {
    font-size: 28px;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 8px;
}

.book-author {
    font-size: 15px;
    color: var(--text-secondary);
    margin-bottom: 12px;
}

.book-desc {
    font-size: 14px;
    color: var(--text-secondary);
    line-height: 1.8;
    margin-bottom: 16px;
}

.book-stats {
    display: flex;
    gap: 16px;
    font-size: 13px;
    color: var(--accent);
    margin-bottom: 20px;
}

.book-actions {
    display: flex;
    gap: 12px;
}

/* Chapters List */
.chapters-list {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 8px;
}

.chapter-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 16px;
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s;
    font-size: 14px;
    color: var(--text-secondary);
    text-decoration: none;
}

.chapter-item:hover {
    border-color: var(--accent);
    color: var(--text-primary);
}

.chapter-number {
    color: var(--accent);
    font-weight: 500;
    white-space: nowrap;
}

.chapter-title {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.chapter-words {
    font-size: 12px;
    color: var(--text-tertiary);
    white-space: nowrap;
}

/* Reader */
.reader-view {
    min-height: 100vh;
    background: var(--bg-primary);
}

.reader-toolbar {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    height: 56px;
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-color);
    display: flex;
    align-items: center;
    padding: 0 24px;
    z-index: 100;
    gap: 16px;
}

.toolbar-btn {
    padding: 6px 14px;
    background: transparent;
    border: 1px solid var(--border-color);
    border-radius: 6px;
    color: var(--text-secondary);
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;
    white-space: nowrap;
}

.toolbar-btn:hover {
    border-color: var(--accent);
    color: var(--accent);
}

.toolbar-title {
    flex: 1;
    font-size: 15px;
    color: var(--text-primary);
    text-align: center;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.toolbar-right {
    display: flex;
    align-items: center;
    gap: 8px;
}

.font-size-display {
    font-size: 12px;
    color: var(--text-tertiary);
    min-width: 36px;
    text-align: center;
}

.reader-content {
    max-width: 720px;
    margin: 0 auto;
    padding: 80px 24px 120px;
    line-height: 1.9;
    color: var(--text-primary);
}

.chapter-title {
    font-family: 'Noto Serif SC', 'Source Han Serif SC', 'STSong', Georgia, serif;
    font-size: 1.6em;
    font-weight: 700;
    text-align: center;
    margin-bottom: 40px;
    color: var(--text-primary);
}

.chapter-body p {
    font-family: 'Noto Serif SC', 'Source Han Serif SC', 'STSong', Georgia, serif;
    text-indent: 2em;
    margin-bottom: 1em;
    color: #cbd5e1;
    line-height: 1.9;
}

.reader-nav {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    height: 64px;
    background: var(--bg-secondary);
    border-top: 1px solid var(--border-color);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 32px;
    z-index: 100;
}

.nav-btn {
    padding: 10px 24px;
    border: 1px solid var(--border-color);
    border-radius: 8px;
    background: transparent;
    color: var(--text-secondary);
    font-size: 14px;
    cursor: pointer;
    transition: all 0.2s;
    text-decoration: none;
}

.nav-btn:hover {
    border-color: var(--accent);
    color: var(--accent);
}

.nav-btn:disabled {
    opacity: 0.3;
    cursor: not-allowed;
}

.nav-info {
    font-size: 14px;
    color: var(--text-tertiary);
}

/* Crawler */
.crawler-input {
    display: flex;
    gap: 12px;
    margin-bottom: 32px;
}

.crawler-input .input {
    flex: 1;
}

.tasks-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.task-card {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 16px 20px;
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 10px;
}

.task-info {
    flex: 1;
    min-width: 0;
}

.task-url {
    font-size: 14px;
    color: var(--text-primary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    margin-bottom: 8px;
}

.task-meta {
    display: flex;
    align-items: center;
    gap: 12px;
}

.task-status {
    font-size: 12px;
    padding: 2px 10px;
    border-radius: 20px;
    font-weight: 500;
}

.status-pending {
    background: rgba(245, 158, 11, 0.15);
    color: #f59e0b;
}

.status-running {
    background: rgba(59, 130, 246, 0.15);
    color: #3b82f6;
}

.status-completed {
    background: rgba(34, 197, 94, 0.15);
    color: #22c55e;
}

.status-failed {
    background: rgba(239, 68, 68, 0.15);
    color: #ef4444;
}

.status-cancelled {
    background: rgba(100, 116, 139, 0.15);
    color: #64748b;
}

.task-time {
    font-size: 12px;
    color: var(--text-tertiary);
}

.task-detail {
    font-size: 13px;
    color: var(--text-secondary);
    margin-top: 6px;
}

/* Scrollbar */
::-webkit-scrollbar {
    width: 8px;
}

::-webkit-scrollbar-track {
    background: var(--bg-primary);
}

::-webkit-scrollbar-thumb {
    background: var(--border-color);
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background: var(--text-tertiary);
}

/* Responsive */
@media (max-width: 768px) {
    .navbar {
        padding: 0 16px;
    }
    .nav-links {
        gap: 8px;
    }
    .nav-links a {
        font-size: 13px;
        padding: 6px 8px;
    }
    .main-content {
        padding: 80px 16px 24px;
    }
    .stats-grid {
        grid-template-columns: repeat(2, 1fr);
    }
    .quick-actions {
        grid-template-columns: 1fr;
    }
    .books-grid {
        grid-template-columns: 1fr;
    }
    .book-header {
        flex-direction: column;
        align-items: center;
        text-align: center;
    }
    .book-actions {
        justify-content: center;
    }
    .chapters-list {
        grid-template-columns: 1fr;
    }
}
```

- [ ] **Step 3: 创建 app.js**

Create: `/workspace/static/js/app.js`

```javascript
document.addEventListener('DOMContentLoaded', function() {
    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    });
});

// AJAX helper
function ajax(url, options = {}) {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    const defaults = {
        headers: {
            'X-CSRFToken': csrfToken,
            'X-Requested-With': 'XMLHttpRequest',
        },
    };
    return fetch(url, { ...defaults, ...options });
}
```

---

## Task 5: 实现用户认证

**Files:**
- Create: `apps/accounts/urls.py`, `apps/accounts/views.py`, `apps/accounts/forms.py`
- Create: `templates/accounts/login.html`, `templates/accounts/register.html`

- [ ] **Step 1: 创建 accounts/forms.py**

Create: `/workspace/apps/accounts/forms.py`

```python
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm


class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'input',
            'placeholder': '请输入用户名'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'input',
            'placeholder': '请输入密码'
        })
    )


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'input',
            'placeholder': '邮箱（可选）'
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'input',
            'placeholder': '用户名'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'input',
            'placeholder': '密码'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'input',
            'placeholder': '确认密码'
        })
```

- [ ] **Step 2: 创建 accounts/views.py**

Create: `/workspace/apps/accounts/views.py`

```python
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import LoginForm, RegisterForm


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                next_url = request.GET.get('next', 'home')
                return redirect(next_url)
            else:
                messages.error(request, '用户名或密码错误')
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, '注册成功！')
            return redirect('home')
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    messages.success(request, '已退出登录')
    return redirect('login')
```

- [ ] **Step 3: 创建 accounts/urls.py**

Create: `/workspace/apps/accounts/urls.py`

```python
from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
]
```

- [ ] **Step 4: 创建 login.html**

Create: `/workspace/templates/accounts/login.html`

```html
{% extends 'base.html' %}

{% block title %}登录 - 小说阅读器{% endblock %}

{% block content %}
<div class="login-page">
    <div class="login-card">
        <div class="login-header">
            <span class="login-icon">📖</span>
            <h1 class="login-title">小说阅读器</h1>
            <p class="login-subtitle">登录你的账号</p>
        </div>

        <form method="post" class="login-form">
            {% csrf_token %}
            <div class="form-group">
                <label class="form-label">用户名</label>
                {{ form.username }}
            </div>
            <div class="form-group">
                <label class="form-label">密码</label>
                {{ form.password }}
            </div>
            <button type="submit" class="btn btn-primary btn-full">登录</button>
        </form>

        <div class="login-footer">
            还没有账号？
            <a href="{% url 'register' %}">立即注册</a>
        </div>
    </div>
</div>
{% endblock %}
```

- [ ] **Step 5: 创建 register.html**

Create: `/workspace/templates/accounts/register.html`

```html
{% extends 'base.html' %}

{% block title %}注册 - 小说阅读器{% endblock %}

{% block content %}
<div class="login-page">
    <div class="login-card">
        <div class="login-header">
            <span class="login-icon">📖</span>
            <h1 class="login-title">小说阅读器</h1>
            <p class="login-subtitle">创建新账号</p>
        </div>

        <form method="post" class="login-form">
            {% csrf_token %}
            <div class="form-group">
                <label class="form-label">用户名</label>
                {{ form.username }}
            </div>
            <div class="form-group">
                <label class="form-label">邮箱（可选）</label>
                {{ form.email }}
            </div>
            <div class="form-group">
                <label class="form-label">密码</label>
                {{ form.password1 }}
            </div>
            <div class="form-group">
                <label class="form-label">确认密码</label>
                {{ form.password2 }}
            </div>
            {% if form.errors %}
                <div class="error-msg">
                    {% for field, errors in form.errors.items %}
                        {{ errors.0 }}
                    {% endfor %}
                </div>
            {% endif %}
            <button type="submit" class="btn btn-primary btn-full">注册</button>
        </form>

        <div class="login-footer">
            已有账号？
            <a href="{% url 'login' %}">立即登录</a>
        </div>
    </div>
</div>
{% endblock %}
```

---

## Task 6: 实现书籍管理

**Files:**
- Create: `apps/books/urls.py`, `apps/books/views.py`, `apps/books/forms.py`, `apps/books/urls_home.py`
- Create: `templates/books/list.html`, `templates/books/detail.html`
- Create: `templates/home.html`

- [ ] **Step 1: 创建 books/forms.py**

Create: `/workspace/apps/books/forms.py`

```python
from django import forms
from .models import Book


class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ['title', 'author', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'input', 'placeholder': '书名'}),
            'author': forms.TextInput(attrs={'class': 'input', 'placeholder': '作者'}),
            'description': forms.Textarea(attrs={'class': 'input', 'placeholder': '简介', 'rows': 3}),
        }
```

- [ ] **Step 2: 创建 books/views.py**

Create: `/workspace/apps/books/views.py`

```python
import os
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Book
from .forms import BookForm


@login_required
def home(request):
    recent_books = Book.objects.all()[:6]
    book_count = Book.objects.count()
    context = {
        'recent_books': recent_books,
        'stats': {
            'book_count': book_count,
            'reading_count': 0,
            'favorite_count': 0,
            'completed_count': 0,
        }
    }
    return render(request, 'home.html', context)


@login_required
def book_list(request):
    query = request.GET.get('q', '')
    books = Book.objects.all()
    if query:
        books = books.filter(Q(title__icontains=query) | Q(author__icontains=query))

    paginator = Paginator(books, 12)
    page = request.GET.get('page', 1)
    page_obj = paginator.get_page(page)

    context = {
        'page_obj': page_obj,
        'query': query,
    }
    return render(request, 'books/list.html', context)


@login_required
def book_detail(request, pk):
    book = get_object_or_404(Book, pk=pk)
    chapters = book.chapters.all()
    context = {
        'book': book,
        'chapters': chapters,
    }
    return render(request, 'books/detail.html', context)


@login_required
def book_add(request):
    if request.method == 'POST':
        form = BookForm(request.POST)
        if form.is_valid():
            book = form.save(commit=False)
            safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in book.title)
            book.folder_path = os.path.join('data/books', safe_name.strip())
            os.makedirs(book.folder_path, exist_ok=True)
            book.save()
            messages.success(request, f'书籍《{book.title}》已添加')
            return redirect('book_list')
    else:
        form = BookForm()

    return render(request, 'books/list.html', {'form': form})


@login_required
def book_delete(request, pk):
    book = get_object_or_404(Book, pk=pk)
    if request.method == 'POST':
        title = book.title
        book.delete()
        messages.success(request, f'书籍《{title}》已删除')
        return redirect('book_list')
    return redirect('book_detail', pk=pk)
```

- [ ] **Step 3: 创建 books/urls.py**

Create: `/workspace/apps/books/urls.py`

```python
from django.urls import path
from . import views

urlpatterns = [
    path('', views.book_list, name='book_list'),
    path('add/', views.book_add, name='book_add'),
    path('<int:pk>/', views.book_detail, name='book_detail'),
    path('<int:pk>/delete/', views.book_delete, name='book_delete'),
]
```

- [ ] **Step 4: 创建 books/urls_home.py**

Create: `/workspace/apps/books/urls_home.py`

```python
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
]
```

- [ ] **Step 5: 创建 home.html**

Create: `/workspace/templates/home.html`

```html
{% extends 'base.html' %}

{% block title %}首页 - 小说阅读器{% endblock %}

{% block content %}
<h1 class="page-title">🏠 首页</h1>

<div class="stats-grid">
    <div class="stat-card">
        <div class="stat-icon">📚</div>
        <div class="stat-value">{{ stats.book_count }}</div>
        <div class="stat-label">书籍总数</div>
    </div>
    <div class="stat-card">
        <div class="stat-icon">📖</div>
        <div class="stat-value">{{ stats.reading_count }}</div>
        <div class="stat-label">阅读中</div>
    </div>
    <div class="stat-card">
        <div class="stat-icon">⭐</div>
        <div class="stat-value">{{ stats.favorite_count }}</div>
        <div class="stat-label">收藏数</div>
    </div>
    <div class="stat-card">
        <div class="stat-icon">✅</div>
        <div class="stat-value">{{ stats.completed_count }}</div>
        <div class="stat-label">已读完</div>
    </div>
</div>

<section class="section">
    <div class="section-header">
        <h2 class="section-title">最近阅读</h2>
        <a href="{% url 'book_list' %}" class="section-link">查看全部 →</a>
    </div>
    {% if recent_books %}
        <div class="books-grid">
            {% for book in recent_books %}
                <div class="book-card" onclick="location.href='{% url 'book_detail' book.id %}'">
                    <div class="book-card-title">{{ book.title }}</div>
                    {% if book.author %}
                        <div class="book-card-author">作者：{{ book.author }}</div>
                    {% endif %}
                    {% if book.description %}
                        <div class="book-card-desc">{{ book.description }}</div>
                    {% endif %}
                    <div class="book-card-meta">{{ book.total_chapters }} 章</div>
                </div>
            {% endfor %}
        </div>
    {% else %}
        <div class="empty-state">
            <div class="empty-icon">📚</div>
            <div class="empty-text">还没有阅读记录，去书架看看吧</div>
        </div>
    {% endif %}
</section>

<section class="section">
    <div class="section-header">
        <h2 class="section-title">快速操作</h2>
    </div>
    <div class="quick-actions">
        <a href="{% url 'search' %}" class="action-card">
            <span class="action-icon">🔍</span>
            <span class="action-text">搜索小说</span>
        </a>
        <a href="{% url 'crawler_tasks' %}" class="action-card">
            <span class="action-icon">🕷️</span>
            <span class="action-text">爬取小说</span>
        </a>
        <a href="{% url 'book_list' %}" class="action-card">
            <span class="action-icon">📚</span>
            <span class="action-text">浏览书架</span>
        </a>
    </div>
</section>
{% endblock %}
```

- [ ] **Step 6: 创建 books/list.html**

Create: `/workspace/templates/books/list.html`

```html
{% extends 'base.html' %}

{% block title %}书架 - 小说阅读器{% endblock %}

{% block content %}
<div class="page-header">
    <h1 class="page-title">📚 书架</h1>
    <button class="btn btn-primary" onclick="document.getElementById('addModal').style.display='flex'">+ 添加书籍</button>
</div>

<div class="search-bar">
    <form method="get" action="{% url 'book_list' %}">
        <input type="text" name="q" class="input" placeholder="搜索书架中的书籍..." value="{{ query }}">
    </form>
</div>

{% if page_obj %}
    <div class="books-grid">
        {% for book in page_obj %}
            <div class="book-card" onclick="location.href='{% url 'book_detail' book.id %}'">
                <div class="book-card-title">{{ book.title }}</div>
                {% if book.author %}
                    <div class="book-card-author">作者：{{ book.author }}</div>
                {% endif %}
                {% if book.description %}
                    <div class="book-card-desc">{{ book.description }}</div>
                {% endif %}
                <div class="book-card-meta">{{ book.total_chapters }} 章</div>
            </div>
        {% endfor %}
    </div>

    {% if page_obj.has_other_pages %}
        <div class="pagination">
            {% if page_obj.has_previous %}
                <a href="?page={{ page_obj.previous_page_number }}{% if query %}&q={{ query }}{% endif %}" class="btn btn-secondary btn-sm">上一页</a>
            {% else %}
                <button class="btn btn-secondary btn-sm" disabled>上一页</button>
            {% endif %}
            <span class="page-info">{{ page_obj.number }} / {{ page_obj.paginator.num_pages }}</span>
            {% if page_obj.has_next %}
                <a href="?page={{ page_obj.next_page_number }}{% if query %}&q={{ query }}{% endif %}" class="btn btn-secondary btn-sm">下一页</a>
            {% else %}
                <button class="btn btn-secondary btn-sm" disabled>下一页</button>
            {% endif %}
        </div>
    {% endif %}
{% else %}
    <div class="empty-state">
        <div class="empty-icon">📚</div>
        <div class="empty-text">书架还是空的，添加一本书吧</div>
    </div>
{% endif %}

<!-- Add Book Modal -->
<div id="addModal" class="modal-overlay" style="display:none;" onclick="if(event.target===this)this.style.display='none'">
    <div class="modal">
        <h2 class="modal-title">添加书籍</h2>
        <form method="post" action="{% url 'book_add' %}">
            {% csrf_token %}
            <div class="form-group">
                <label class="form-label">书名 *</label>
                <input type="text" name="title" class="input" placeholder="输入书名" required>
            </div>
            <div class="form-group">
                <label class="form-label">作者</label>
                <input type="text" name="author" class="input" placeholder="输入作者">
            </div>
            <div class="form-group">
                <label class="form-label">简介</label>
                <textarea name="description" class="input" rows="3" placeholder="输入简介"></textarea>
            </div>
            <div class="modal-actions">
                <button type="button" class="btn btn-secondary" onclick="document.getElementById('addModal').style.display='none'">取消</button>
                <button type="submit" class="btn btn-primary">添加</button>
            </div>
        </form>
    </div>
</div>
{% endblock %}
```

- [ ] **Step 7: 创建 books/detail.html**

Create: `/workspace/templates/books/detail.html`

```html
{% extends 'base.html' %}

{% block title %}{{ book.title }} - 小说阅读器{% endblock %}

{% block content %}
<div class="book-header">
    <div class="book-cover-large">📖</div>
    <div class="book-meta-info">
        <h1 class="book-title">{{ book.title }}</h1>
        {% if book.author %}
            <p class="book-author">作者：{{ book.author }}</p>
        {% endif %}
        {% if book.description %}
            <p class="book-desc">{{ book.description }}</p>
        {% endif %}
        <div class="book-stats">
            <span>{{ book.total_chapters }} 章</span>
        </div>
        <div class="book-actions">
            {% if chapters %}
                <a href="{% url 'chapter_read' book.id chapters.0.id %}" class="btn btn-primary">开始阅读</a>
            {% endif %}
            <form method="post" action="{% url 'favorite_toggle' %}" style="display:inline;">
                {% csrf_token %}
                <input type="hidden" name="book_id" value="{{ book.id }}">
                <button type="submit" class="btn btn-secondary">☆ 收藏</button>
            </form>
            <form method="post" action="{% url 'book_delete' book.id %}" style="display:inline;" onsubmit="return confirm('确定要删除这本书吗？')">
                {% csrf_token %}
                <button type="submit" class="btn btn-danger">删除</button>
            </form>
        </div>
    </div>
</div>

<section class="chapters-section">
    <h2 class="section-title">章节目录</h2>
    {% if chapters %}
        <div class="chapters-list">
            {% for chapter in chapters %}
                <a href="{% url 'chapter_read' book.id chapter.id %}" class="chapter-item">
                    <span class="chapter-number">第{{ chapter.chapter_number }}章</span>
                    <span class="chapter-title">{{ chapter.title }}</span>
                    {% if chapter.word_count %}
                        <span class="chapter-words">{{ chapter.word_count }}字</span>
                    {% endif %}
                </a>
            {% endfor %}
        </div>
    {% else %}
        <div class="empty-state">
            <div class="empty-icon">📄</div>
            <div class="empty-text">暂无章节</div>
        </div>
    {% endif %}
</section>
{% endblock %}
```

---

## Task 7: 实现章节阅读

**Files:**
- Create: `apps/chapters/urls.py`, `apps/chapters/views.py`
- Create: `templates/chapters/read.html`
- Create: `static/js/reader.js`

- [ ] **Step 1: 创建 chapters/views.py**

Create: `/workspace/apps/chapters/views.py`

```python
import os
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from apps.books.models import Book
from apps.reader.models import ReadingProgress
from .models import Chapter


@login_required
def chapter_read(request, book_id, chapter_id):
    book = get_object_or_404(Book, pk=book_id)
    chapter = get_object_or_404(Chapter, pk=chapter_id, book=book)
    chapters = list(book.chapters.all().values('id', 'chapter_number', 'title'))

    # Get content
    content = ''
    if os.path.exists(chapter.file_path):
        try:
            with open(chapter.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except:
            try:
                with open(chapter.file_path, 'r', encoding='gbk') as f:
                    content = f.read()
            except:
                content = '章节内容读取失败'
    else:
        content = '章节文件不存在'

    # Get reading progress
    progress = ReadingProgress.objects.filter(user=request.user, book=book).first()

    context = {
        'book': book,
        'chapter': chapter,
        'chapters': chapters,
        'content': content,
        'progress': progress,
    }
    return render(request, 'chapters/read.html', context)


@login_required
@require_POST
def save_progress(request, book_id):
    chapter_id = request.POST.get('chapter_id')
    position = request.POST.get('position', 0)

    book = get_object_or_404(Book, pk=book_id)
    chapter = get_object_or_404(Chapter, pk=chapter_id, book=book)

    progress, _ = ReadingProgress.objects.update_or_create(
        user=request.user,
        book=book,
        defaults={'chapter': chapter, 'position': position}
    )

    return JsonResponse({'status': 'ok'})
```

- [ ] **Step 2: 创建 chapters/urls.py**

Create: `/workspace/apps/chapters/urls.py`

```python
from django.urls import path
from . import views

urlpatterns = [
    path('<int:book_id>/<int:chapter_id>/', views.chapter_read, name='chapter_read'),
    path('<int:book_id>/save-progress/', views.save_progress, name='save_progress'),
]
```

- [ ] **Step 3: 创建 read.html**

Create: `/workspace/templates/chapters/read.html`

```html
{% extends 'base.html' %}
{% load static %}

{% block title %}{{ chapter.title }} - {{ book.title }}{% endblock %}

{% block content %}
<div class="reader-view">
    <div class="reader-toolbar">
        <a href="{% url 'book_detail' book.id %}" class="toolbar-btn">← 返回</a>
        <span class="toolbar-title">{{ chapter.title }}</span>
        <div class="toolbar-right">
            <button class="toolbar-btn" onclick="decreaseFontSize()">A-</button>
            <span class="font-size-display" id="fontSizeDisplay">18</span>
            <button class="toolbar-btn" onclick="increaseFontSize()">A+</button>
        </div>
    </div>

    <div class="reader-content" id="readerContent" style="font-size: 18px;">
        <h1 class="chapter-title">{{ chapter.title }}</h1>
        <div class="chapter-body">
            {% for paragraph in content|splitlines %}
                {% if paragraph.strip %}
                    <p>{{ paragraph }}</p>
                {% endif %}
            {% endfor %}
        </div>
    </div>

    <div class="reader-nav">
        {% if prev_chapter %}
            <a href="{% url 'chapter_read' book.id prev_chapter.id %}" class="nav-btn">← 上一章</a>
        {% else %}
            <button class="nav-btn" disabled>← 上一章</button>
        {% endif %}
        <span class="nav-info">第{{ chapter.chapter_number }}章</span>
        {% if next_chapter %}
            <a href="{% url 'chapter_read' book.id next_chapter.id %}" class="nav-btn">下一章 →</a>
        {% else %}
            <button class="nav-btn" disabled>下一章 →</button>
        {% endif %}
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script src="{% static 'js/reader.js' %}"></script>
<script>
    window.bookId = {{ book.id }};
    window.chapterId = {{ chapter.id }};
    window.chapters = {{ chapters|safe }};
</script>
{% endblock %}
```

- [ ] **Step 4: 创建 reader.js**

Create: `/workspace/static/js/reader.js`

```javascript
let fontSize = parseInt(localStorage.getItem('reader-font-size') || '18');
let saveTimer = null;

function updateFontSize() {
    document.getElementById('readerContent').style.fontSize = fontSize + 'px';
    document.getElementById('fontSizeDisplay').textContent = fontSize;
    localStorage.setItem('reader-font-size', fontSize);
}

function increaseFontSize() {
    if (fontSize < 28) {
        fontSize += 2;
        updateFontSize();
    }
}

function decreaseFontSize() {
    if (fontSize > 12) {
        fontSize -= 2;
        updateFontSize();
    }
}

function saveProgress() {
    if (typeof window.chapterId === 'undefined') return;
    const position = window.scrollY;

    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    fetch(`/chapters/${window.bookId}/save-progress/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken,
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `chapter_id=${window.chapterId}&position=${position}`
    }).catch(() => {});
}

function scheduleSave() {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(saveProgress, 2000);
}

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    updateFontSize();
    window.addEventListener('scroll', scheduleSave);
    window.addEventListener('beforeunload', saveProgress);
});
```

- [ ] **Step 5: 创建模板过滤器**

Create: `/workspace/apps/books/templatetags/__init__.py`

Create: `/workspace/apps/books/templatetags/custom_filters.py`

```python
from django import template

register = template.Library()


@register.filter
def splitlines(value):
    return value.splitlines()
```

---

## Task 8: 实现收藏功能

**Files:**
- Create: `apps/favorites/urls.py`, `apps/favorites/views.py`
- Create: `templates/favorites/list.html`

- [ ] **Step 1: 创建 favorites/views.py**

Create: `/workspace/apps/favorites/views.py`

```python
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from apps.books.models import Book
from .models import Favorite


@login_required
def favorite_list(request):
    favorites = Favorite.objects.filter(user=request.user).select_related('book')
    return render(request, 'favorites/list.html', {'favorites': favorites})


@login_required
@require_POST
def favorite_toggle(request):
    book_id = request.POST.get('book_id')
    book = get_object_or_404(Book, pk=book_id)

    favorite = Favorite.objects.filter(user=request.user, book=book).first()
    if favorite:
        favorite.delete()
        messages.success(request, f'已取消收藏《{book.title}》')
    else:
        Favorite.objects.create(user=request.user, book=book)
        messages.success(request, f'已收藏《{book.title}》')

    next_url = request.POST.get('next', 'book_list')
    return redirect(next_url)
```

- [ ] **Step 2: 创建 favorites/urls.py**

Create: `/workspace/apps/favorites/urls.py`

```python
from django.urls import path
from . import views

urlpatterns = [
    path('', views.favorite_list, name='favorite_list'),
    path('toggle/', views.favorite_toggle, name='favorite_toggle'),
]
```

- [ ] **Step 3: 创建 favorites/list.html**

Create: `/workspace/templates/favorites/list.html`

```html
{% extends 'base.html' %}

{% block title %}我的收藏 - 小说阅读器{% endblock %}

{% block content %}
<h1 class="page-title">⭐ 我的收藏</h1>

{% if favorites %}
    <div class="books-grid">
        {% for fav in favorites %}
            <div class="book-card" onclick="location.href='{% url 'book_detail' fav.book.id %}'">
                <div class="book-card-title">{{ fav.book.title }}</div>
                {% if fav.book.author %}
                    <div class="book-card-author">作者：{{ fav.book.author }}</div>
                {% endif %}
                {% if fav.notes %}
                    <div class="book-card-desc">{{ fav.notes }}</div>
                {% endif %}
                <div class="book-card-meta">{{ fav.book.total_chapters }} 章</div>
            </div>
        {% endfor %}
    </div>
{% else %}
    <div class="empty-state">
        <div class="empty-icon">⭐</div>
        <div class="empty-text">还没有收藏任何书籍</div>
    </div>
{% endif %}
{% endblock %}
```

---

## Task 9: 实现搜索功能

**Files:**
- Create: `apps/search/urls.py`, `apps/search/views.py`
- Create: `templates/search/results.html`

- [ ] **Step 1: 创建 search/views.py**

Create: `/workspace/apps/search/views.py`

```python
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from apps.books.models import Book


@login_required
def search(request):
    query = request.GET.get('q', '')
    results = []
    suggestions = []

    if query:
        results = Book.objects.filter(
            Q(title__icontains=query) | Q(author__icontains=query)
        )

    if len(query) >= 2:
        suggestions = Book.objects.filter(
            title__istartswith=query
        ).values_list('title', flat=True)[:10]

    context = {
        'query': query,
        'results': results,
        'suggestions': suggestions,
    }
    return render(request, 'search/results.html', context)
```

- [ ] **Step 2: 创建 search/urls.py**

Create: `/workspace/apps/search/urls.py`

```python
from django.urls import path
from . import views

urlpatterns = [
    path('', views.search, name='search'),
]
```

- [ ] **Step 3: 创建 search/results.html**

Create: `/workspace/templates/search/results.html`

```html
{% extends 'base.html' %}

{% block title %}搜索 - 小说阅读器{% endblock %}

{% block content %}
<h1 class="page-title">🔍 搜索</h1>

<div class="search-box">
    <form method="get" action="{% url 'search' %}" style="display:flex;gap:12px;width:100%;">
        <input type="text" name="q" class="input search-input" placeholder="搜索小说标题、作者..." value="{{ query }}" autocomplete="off">
        <button type="submit" class="btn btn-primary">搜索</button>
    </form>
</div>

{% if query %}
    {% if results %}
        <p class="results-count">找到 {{ results|length }} 个结果</p>
        <div class="books-grid">
            {% for book in results %}
                <div class="book-card" onclick="location.href='{% url 'book_detail' book.id %}'">
                    <div class="book-card-title">{{ book.title }}</div>
                    {% if book.author %}
                        <div class="book-card-author">作者：{{ book.author }}</div>
                    {% endif %}
                    {% if book.description %}
                        <div class="book-card-desc">{{ book.description }}</div>
                    {% endif %}
                    <div class="book-card-meta">{{ book.total_chapters }} 章</div>
                </div>
            {% endfor %}
        </div>
    {% else %}
        <div class="empty-state">
            <div class="empty-icon">🔍</div>
            <div class="empty-text">没有找到相关书籍</div>
        </div>
    {% endif %}
{% endif %}
{% endblock %}
```

---

## Task 10: 实现爬虫功能

**Files:**
- Create: `apps/crawler/urls.py`, `apps/crawler/views.py`, `apps/crawler/tasks.py`
- Create: `utils/crawler_engine.py`
- Create: `templates/crawler/tasks.html`
- Create: `static/js/crawler.js`

- [ ] **Step 1: 创建 utils/crawler_engine.py**

Create: `/workspace/utils/crawler_engine.py`

```python
import re
import time
import json
import socket
import ipaddress
import threading
import requests
from pathlib import Path
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


class IntelligentParser:
    CHAPTER_PATTERNS = [
        re.compile(r'^第[零一二三四五六七八九十百千万\d]+章', re.MULTILINE),
        re.compile(r'^第\d+章', re.MULTILINE),
        re.compile(r'^Chapter\s+\d+', re.MULTILINE | re.IGNORECASE),
    ]

    CONTENT_SELECTORS = [
        {"id": "content"},
        {"id": "bookContent"},
        {"class_": "content"},
        {"class_": "chapter-content"},
        {"class_": "read-content"},
    ]

    def parse_chapter_list(self, html, base_url):
        soup = BeautifulSoup(html, "html.parser")
        list_containers = soup.find_all(["div", "dl", "ul", "ol"], class_=re.compile(r"(list|chapter|catalog|menu|directory)", re.I))
        if not list_containers:
            list_containers = soup.find_all("dl")

        chapters = []
        seen_urls = set()

        for container in list_containers:
            links = container.find_all("a", href=True)
            for link in links:
                href = link.get("href", "")
                title = link.get_text(strip=True)
                if not title or not href:
                    continue
                if any(skip in title.lower() for skip in ["首页", "末页", "上一页", "下一页", "返回", "目录"]):
                    continue
                full_url = urljoin(base_url, href)
                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)
                chapters.append({"title": title, "url": full_url})

        return chapters

    def parse_chapter_content(self, html):
        soup = BeautifulSoup(html, "html.parser")
        for sel in self.CONTENT_SELECTORS:
            kwargs = {}
            if "id" in sel:
                kwargs = {"id": sel["id"]}
            elif "class_" in sel:
                kwargs = {"class_": sel["class_"]}
            element = soup.find("div", **kwargs)
            if element:
                content = self._clean_content(element)
                if len(content) > 50:
                    return {"title": "", "content": content}
        return {"title": "", "content": ""}

    def _clean_content(self, element):
        for tag in element.find_all(["script", "style", "iframe", "ins", "nav"]):
            tag.decompose()
        paragraphs = element.find_all("p")
        if paragraphs:
            parts = [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)]
            return "\n\n".join(parts)
        text = element.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n\n".join(lines)

    def parse_book_info(self, html):
        soup = BeautifulSoup(html, "html.parser")
        info = {"title": "", "author": "", "description": ""}
        title_tag = soup.find("h1")
        if title_tag:
            info["title"] = title_tag.get_text(strip=True)
        return info


SSRF_BLOCKED_HOSTS = {
    "169.254.169.254", "metadata.google.internal", "localhost", "127.0.0.1", "0.0.0.0", "::1"
}


def validate_crawl_url(url):
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    hostname = parsed.hostname
    if not hostname or hostname in SSRF_BLOCKED_HOSTS:
        return False
    try:
        resolved_ips = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        for family, _, _, _, sockaddr in resolved_ips:
            ip = sockaddr[0]
            if ipaddress.ip_address(ip).is_private:
                return False
    except socket.gaierror:
        return False
    return True


class CrawlerEngine:
    def __init__(self, task_id, books_dir):
        self.task_id = task_id
        self.books_dir = Path(books_dir)
        self.parser = IntelligentParser()
        self._ua_index = 0
        self._stop = False

    def _get_ua(self):
        ua = USER_AGENTS[self._ua_index % len(USER_AGENTS)]
        self._ua_index += 1
        return ua

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10),
           retry=retry_if_exception_type((requests.RequestException,)), reraise=True)
    def _fetch_page(self, session, url):
        headers = {"User-Agent": self._get_ua()}
        resp = session.get(url, headers=headers, timeout=30)
        if resp.status_code == 200:
            return resp.text
        return None

    def _safe_filename(self, name):
        name = re.sub(r'[\\/:*?"<>|]', '_', name)
        name = name.strip('. ')
        return name[:100] if name else "unnamed"

    def _append_log(self, task, message):
        from apps.crawler.models import CrawlerTask
        try:
            task = CrawlerTask.objects.get(id=task.id)
            logs = json.loads(task.logs) if task.logs else []
            logs.append({"time": time.time(), "msg": message})
            task.logs = json.dumps(logs, ensure_ascii=False)
            task.save(update_fields=['logs'])
        except Exception:
            pass

    def run(self, task):
        import os
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'novel_reader.settings')
        import django
        django.setup()

        from apps.books.models import Book
        from apps.chapters.models import Chapter

        if not validate_crawl_url(task.url):
            task.status = 'failed'
            task.error_message = '目标 URL 不合法或指向内网/元数据地址，禁止访问'
            task.save()
            return

        task.status = 'running'
        task.save()
        self._append_log(task, '任务开始执行')

        session = requests.Session()

        try:
            html = self._fetch_page(session, task.url)
            if not html:
                task.status = 'failed'
                task.error_message = '无法获取目录页'
                task.save()
                return

            book_info = self.parser.parse_book_info(html)
            chapter_list = self.parser.parse_chapter_list(html, task.url)

            if not chapter_list:
                task.status = 'failed'
                task.error_message = '无法解析章节列表'
                task.save()
                return

            task.total_chapters = len(chapter_list)
            self._append_log(task, f'解析到 {len(chapter_list)} 个章节')
            task.save()

            title = book_info.get("title") or f"来自 {task.url}"
            book, _ = Book.objects.get_or_create(
                title=title,
                defaults={
                    'author': book_info.get('author', ''),
                    'description': book_info.get('description', ''),
                    'folder_path': str(self.books_dir / self._safe_filename(title)),
                }
            )
            task.book = book
            task.save()

            books_dir = Path(book.folder_path)
            books_dir.mkdir(parents=True, exist_ok=True)

            for i, chapter_info in enumerate(chapter_list):
                if self._stop:
                    task.status = 'cancelled'
                    self._append_log(task, '任务已取消')
                    task.save()
                    return

                try:
                    chapter_html = self._fetch_page(session, chapter_info["url"])
                    if chapter_html:
                        parsed = self.parser.parse_chapter_content(chapter_html)
                        content = parsed.get("content", "")
                        chapter_title = parsed.get("title") or chapter_info["title"]

                        if content:
                            chapter_filename = f"第{i + 1}章.txt"
                            chapter_path = books_dir / chapter_filename
                            with open(chapter_path, 'w', encoding='utf-8') as f:
                                f.write(f"{chapter_title}\n\n{content}")

                            Chapter.objects.update_or_create(
                                book=book,
                                chapter_number=i + 1,
                                defaults={
                                    'title': chapter_title,
                                    'file_path': str(chapter_path),
                                    'word_count': len(content),
                                }
                            )

                            task.downloaded_chapters = i + 1
                            task.save()
                except Exception as e:
                    self._append_log(task, f'第 {i + 1} 章处理异常: {e}')

            book.total_chapters = task.downloaded_chapters
            book.save()
            task.status = 'completed'
            self._append_log(task, f'任务完成，共下载 {task.downloaded_chapters} 章')
            task.save()

        except Exception as e:
            task.status = 'failed'
            task.error_message = str(e)[:500]
            self._append_log(task, f'任务失败: {e}')
            task.save()

    def stop(self):
        self._stop = True
```

- [ ] **Step 2: 创建 crawler/views.py**

Create: `/workspace/apps/crawler/views.py`

```python
import json
import threading
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import CrawlerTask
from utils.crawler_engine import CrawlerEngine
from django.conf import settings


@login_required
def crawler_tasks(request):
    tasks = CrawlerTask.objects.filter(user=request.user)
    return render(request, 'crawler/tasks.html', {'tasks': tasks})


@login_required
@require_POST
def create_task(request):
    url = request.POST.get('url', '').strip()
    if not url:
        messages.error(request, '请输入URL')
        return redirect('crawler_tasks')

    task = CrawlerTask.objects.create(user=request.user, url=url)

    # Start crawler in background thread
    engine = CrawlerEngine(task.id, settings.BOOKS_DIR)
    thread = threading.Thread(target=engine.run, args=(task,))
    thread.daemon = True
    thread.start()

    messages.success(request, '爬虫任务已创建')
    return redirect('crawler_tasks')


@login_required
def task_detail(request, pk):
    task = get_object_or_404(CrawlerTask, pk=pk, user=request.user)
    logs = []
    if task.logs:
        try:
            logs = json.loads(task.logs)
        except:
            pass
    return JsonResponse({
        'id': task.id,
        'status': task.status,
        'total_chapters': task.total_chapters,
        'downloaded_chapters': task.downloaded_chapters,
        'error_message': task.error_message,
        'logs': logs,
    })
```

- [ ] **Step 3: 创建 crawler/urls.py**

Create: `/workspace/apps/crawler/urls.py`

```python
from django.urls import path
from . import views

urlpatterns = [
    path('', views.crawler_tasks, name='crawler_tasks'),
    path('create/', views.create_task, name='create_task'),
    path('<int:pk>/', views.task_detail, name='task_detail'),
]
```

- [ ] **Step 4: 创建 crawler/tasks.html**

Create: `/workspace/templates/crawler/tasks.html`

```html
{% extends 'base.html' %}
{% load static %}

{% block title %}爬虫管理 - 小说阅读器{% endblock %}

{% block content %}
<h1 class="page-title">🕷️ 爬虫管理</h1>

<div class="crawler-input">
    <form method="post" action="{% url 'create_task' %}" style="display:flex;gap:12px;width:100%;">
        {% csrf_token %}
        <input type="url" name="url" class="input" placeholder="输入小说页面URL..." required>
        <button type="submit" class="btn btn-primary">开始爬取</button>
    </form>
</div>

<section class="tasks-section">
    <h2 class="section-title">任务列表</h2>

    {% if tasks %}
        <div class="tasks-list" id="tasksList">
            {% for task in tasks %}
                <div class="task-card" data-task-id="{{ task.id }}">
                    <div class="task-info">
                        <div class="task-url">{{ task.url }}</div>
                        <div class="task-meta">
                            <span class="task-status status-{{ task.status }}">{{ task.get_status_display }}</span>
                            <span class="task-time">{{ task.created_at|date:"Y-m-d H:i" }}</span>
                        </div>
                        {% if task.error_message %}
                            <div class="task-detail">{{ task.error_message }}</div>
                        {% endif %}
                    </div>
                    <button class="btn btn-secondary btn-sm" onclick="refreshTask({{ task.id }})">刷新</button>
                </div>
            {% endfor %}
        </div>
    {% else %}
        <div class="empty-state">
            <div class="empty-icon">🕷️</div>
            <div class="empty-text">暂无爬虫任务</div>
        </div>
    {% endif %}
</section>
{% endblock %}

{% block extra_js %}
<script src="{% static 'js/crawler.js' %}"></script>
{% endblock %}
```

- [ ] **Step 5: 创建 crawler.js**

Create: `/workspace/static/js/crawler.js`

```javascript
function refreshTask(taskId) {
    fetch(`/crawler/${taskId}/`)
        .then(r => r.json())
        .then(data => {
            const card = document.querySelector(`[data-task-id="${taskId}"]`);
            if (card) {
                const statusEl = card.querySelector('.task-status');
                statusEl.className = `task-status status-${data.status}`;
                statusEl.textContent = getStatusText(data.status);
            }
        })
        .catch(() => {});
}

function getStatusText(status) {
    const map = {
        'pending': '等待中',
        'running': '运行中',
        'completed': '已完成',
        'failed': '失败',
        'cancelled': '已取消'
    };
    return map[status] || status;
}

// Auto-refresh running tasks
setInterval(() => {
    document.querySelectorAll('.task-status.status-running').forEach(el => {
        const card = el.closest('.task-card');
        if (card) {
            const taskId = card.dataset.taskId;
            refreshTask(taskId);
        }
    });
}, 5000);
```

---

## Task 11: 实现阅读进度和导航链接

**Files:**
- Create: `apps/reader/urls.py`, `apps/reader/views.py`
- Modify: `templates/base.html` (添加收藏链接)

- [ ] **Step 1: 创建 reader/urls.py**

Create: `/workspace/apps/reader/urls.py`

```python
from django.urls import path
from . import views

urlpatterns = [
]
```

- [ ] **Step 2: 修改 base.html 添加收藏链接**

Modify: `/workspace/templates/base.html`

Search for:
```html
        <div class="nav-links">
            <a href="{% url 'home' %}" class="{% if request.path == '/' %}active{% endif %}">首页</a>
            <a href="{% url 'book_list' %}" class="{% if '/books/' in request.path %}active{% endif %}">书架</a>
            <a href="{% url 'search' %}" class="{% if '/search/' in request.path %}active{% endif %}">搜索</a>
            <a href="{% url 'crawler_tasks' %}" class="{% if '/crawler/' in request.path %}active{% endif %}">爬虫</a>
        </div>
```

Replace with:
```html
        <div class="nav-links">
            <a href="{% url 'home' %}" class="{% if request.path == '/' %}active{% endif %}">首页</a>
            <a href="{% url 'book_list' %}" class="{% if '/books/' in request.path %}active{% endif %}">书架</a>
            <a href="{% url 'favorite_list' %}" class="{% if '/favorites/' in request.path %}active{% endif %}">收藏</a>
            <a href="{% url 'search' %}" class="{% if '/search/' in request.path %}active{% endif %}">搜索</a>
            <a href="{% url 'crawler_tasks' %}" class="{% if '/crawler/' in request.path %}active{% endif %}">爬虫</a>
        </div>
```

---

## Task 12: 修复章节阅读视图的上一章/下一章逻辑

**Files:**
- Modify: `apps/chapters/views.py`

- [ ] **Step 1: 修改 chapters/views.py**

Modify: `/workspace/apps/chapters/views.py`

Search for:
```python
    # Get reading progress
    progress = ReadingProgress.objects.filter(user=request.user, book=book).first()

    context = {
        'book': book,
        'chapter': chapter,
        'chapters': chapters,
        'content': content,
        'progress': progress,
    }
```

Replace with:
```python
    # Get reading progress
    progress = ReadingProgress.objects.filter(user=request.user, book=book).first()

    # Find prev/next chapters
    prev_chapter = None
    next_chapter = None
    for i, ch in enumerate(chapters):
        if ch['id'] == chapter.id:
            if i > 0:
                prev_chapter = chapters[i - 1]
            if i < len(chapters) - 1:
                next_chapter = chapters[i + 1]
            break

    context = {
        'book': book,
        'chapter': chapter,
        'chapters': chapters,
        'content': content,
        'progress': progress,
        'prev_chapter': prev_chapter,
        'next_chapter': next_chapter,
    }
```

---

## Task 13: 注册 Admin 并运行测试

**Files:**
- Create: `apps/books/admin.py`, `apps/chapters/admin.py`, `apps/crawler/admin.py`, `apps/favorites/admin.py`, `apps/reader/admin.py`

- [ ] **Step 1: 创建各 app 的 admin.py**

Create: `/workspace/apps/books/admin.py`

```python
from django.contrib import admin
from .models import Book, Tag, BookTag

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'total_chapters', 'created_at']
    search_fields = ['title', 'author']
    list_filter = ['created_at']

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name']

admin.site.register(BookTag)
```

Create: `/workspace/apps/chapters/admin.py`

```python
from django.contrib import admin
from .models import Chapter

@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ['book', 'chapter_number', 'title', 'word_count']
    list_filter = ['book']
```

Create: `/workspace/apps/crawler/admin.py`

```python
from django.contrib import admin
from .models import CrawlerTask

@admin.register(CrawlerTask)
class CrawlerTaskAdmin(admin.ModelAdmin):
    list_display = ['url', 'status', 'user', 'created_at']
    list_filter = ['status', 'created_at']
```

Create: `/workspace/apps/favorites/admin.py`

```python
from django.contrib import admin
from .models import Favorite, FavoriteFolder

@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ['user', 'book', 'created_at']

@admin.register(FavoriteFolder)
class FavoriteFolderAdmin(admin.ModelAdmin):
    list_display = ['name', 'user']
```

Create: `/workspace/apps/reader/admin.py`

```python
from django.contrib import admin
from .models import ReadingProgress

@admin.register(ReadingProgress)
class ReadingProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'book', 'chapter', 'updated_at']
```

- [ ] **Step 2: 运行开发服务器测试**

```bash
cd /workspace
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser --noinput --username admin --email admin@example.com || true
python manage.py shell -c "from django.contrib.auth.models import User; u=User.objects.filter(username='admin').first(); u and u.set_password('admin123') and u.save()"
python manage.py runserver 0.0.0.0:8000
```

---

## Task 14: 更新部署脚本

**Files:**
- Create: `start.sh`
- Create: `requirements.txt` (已创建)

- [ ] **Step 1: 创建 start.sh**

Create: `/workspace/start.sh`

```bash
#!/bin/bash
set -e

cd "$(dirname "$0")"

# Install dependencies if needed
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate

pip install -q -r requirements.txt

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput 2>/dev/null || true

# Create superuser if not exists
python manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Superuser created: admin / admin123')
" 2>/dev/null || true

echo "Starting server at http://localhost:8000"
python manage.py runserver 0.0.0.0:8000
```

```bash
chmod +x /workspace/start.sh
```

---

## 验证清单

- [ ] 首页 `/` 正常显示
- [ ] 登录 `/accounts/login/` 正常
- [ ] 注册 `/accounts/register/` 正常
- [ ] 书架 `/books/` 列表和分页正常
- [ ] 书籍详情 `/books/<id>/` 正常
- [ ] 阅读器 `/reader/<book_id>/<chapter_id>/` 正常
- [ ] 收藏 `/favorites/` 正常
- [ ] 搜索 `/search/` 正常
- [ ] 爬虫 `/crawler/` 正常
- [ ] Admin `/admin/` 正常
- [ ] 深色主题样式正确
- [ ] 响应式布局在移动端正常
