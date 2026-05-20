# Novel Reader - Django 小说阅读器

基于 Django 的本地小说阅读平台，支持书籍管理、章节阅读、爬虫抓取、收藏和搜索功能。

## 功能特性

- 用户注册/登录/退出
- 书籍管理（添加、查看、删除）
- 章节阅读（字体调节、进度保存）
- 收藏功能
- 全文搜索（基于 Haystack + Whoosh）
- 网页爬虫（自动抓取小说章节，支持可配置解析规则）
- 任务队列（Celery + Redis）
- 深色主题 + 响应式布局
- Docker 部署支持

## 技术栈

- **后端**: Django 4.2 + SQLite
- **任务队列**: Celery + Redis
- **搜索**: Django Haystack + Whoosh
- **前端**: Django Templates + 原生 JavaScript + CSS3
- **爬虫**: requests + BeautifulSoup4
- **部署**: Docker + Gunicorn
- **测试**: pytest

## 快速开始

### 使用 Docker（推荐）

```bash
# 启动所有服务
docker-compose up -d

# 初始化搜索索引
docker-compose exec web python manage.py rebuild_index
```

访问 http://localhost:8000

默认账号: `admin` / `admin123`

### 传统方式

```bash
# 安装依赖
pip install -r requirements.txt

# 数据库迁移
python manage.py migrate

# 初始化搜索索引
python manage.py rebuild_index

# 创建超级用户
python manage.py createsuperuser

# 启动 Celery worker（另一个终端）
celery -A novel_reader worker --loglevel=info

# 启动开发服务器
python manage.py runserver
```

或者使用提供的启动脚本：

```bash
# Linux/macOS
./start.sh start

# Windows (PowerShell)
.\start.ps1 start
```

## 配置爬虫站点

在 `utils/crawler_config.py` 中添加或修改站点配置：

```python
SITE_CONFIGS = {
    "your-site.com": SiteConfig(
        name="Your Novel Site",
        domain="your-site.com",
        chapter_list_selectors=["#chapter-list"],
        content_selectors=["#novel-content"],
        title_selector="h1.title",
        request_delay=1.0,
    ),
}
```

## 测试

```bash
# 运行测试
pytest

# 带覆盖率报告
pytest --cov=apps
```

## 项目结构

```
novel_reader/
├── manage.py
├── novel_reader/          # 项目配置
│   ├── settings.py
│   ├── urls.py
│   ├── celery.py
│   └── wsgi.py
├── apps/                  # 应用模块
│   ├── accounts/          # 用户认证
│   ├── books/             # 书籍管理
│   ├── chapters/          # 章节管理
│   ├── reader/            # 阅读进度
│   ├── favorites/         # 收藏功能
│   ├── crawler/           # 爬虫任务
│   └── search/            # 全文搜索
├── templates/             # HTML 模板
├── static/                # CSS/JS 静态文件
├── utils/                 # 工具模块
│   ├── crawler_engine.py  # 爬虫引擎
│   └── crawler_config.py  # 爬虫配置
├── tests/                 # 测试文件
├── data/                  # 数据目录
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## 许可证

MIT
