# Novel Reader - Django 小说阅读器

基于 Django 的本地小说阅读平台，支持书籍管理、章节阅读、爬虫抓取、收藏和搜索功能。

## 功能特性

- 用户注册/登录/退出
- 书籍管理（添加、查看、删除）
- 章节阅读（字体调节、进度保存）
- 收藏功能
- 全文搜索
- 网页爬虫（自动抓取小说章节）
- 深色主题 + 响应式布局

## 技术栈

- **后端**: Django 4.2 + SQLite
- **前端**: Django Templates + 原生 JavaScript + CSS3
- **爬虫**: requests + BeautifulSoup4

## 快速开始

### Linux/macOS

```bash
./start.sh start
```

### Windows (CMD)

```cmd
start.bat start
```

### Windows (PowerShell)

```powershell
.\start.ps1 start
```

启动后访问 http://localhost:8000

默认账号: `admin / admin123`

## 启动脚本命令

所有启动脚本支持以下命令：

| 命令 | 说明 |
|------|------|
| `start` | 启动服务（默认） |
| `stop` | 停止服务 |
| `restart` | 重启服务 |
| `status` | 查看服务状态 |
| `migrate` | 执行数据库迁移 |
| `createsuperuser` | 创建超级用户 |
| `shell` | 进入 Django shell |
| `help` | 显示帮助 |

## 项目结构

```
novel_reader/
├── manage.py              # Django 管理命令
├── novel_reader/          # 项目配置
│   ├── settings.py
│   ├── urls.py
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
│   └── crawler_engine.py  # 爬虫引擎
└── data/                  # 数据目录
    ├── db.sqlite3         # SQLite 数据库
    └── books/             # 书籍文件
```

## 手动运行

```bash
# 安装依赖
pip install -r requirements.txt

# 数据库迁移
python manage.py migrate

# 创建超级用户
python manage.py createsuperuser

# 启动服务
python manage.py runserver
```

## 许可证

MIT
