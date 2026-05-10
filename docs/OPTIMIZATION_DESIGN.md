# Novel Reader 全面优化设计文档

> **日期:** 2026-05-10
> **范围:** 后端代码全面优化（性能 + 稳定性 + 可维护性）

---

## 一、问题诊断

### 1.1 性能问题

| 问题 | 位置 | 影响 | 严重程度 |
|------|------|------|---------|
| **搜索 N+1 查询** | `api/search.py:28-35` | 每页 50 条搜索 → 51 次数据库查询 | 🔴 高 |
| **数据库连接池过大** | `database.py:pool_size=20` | SQLite 不需要连接池，浪费资源 | 🟡 中 |
| **缓存服务单例无连接池** | `cache_service.py` | Redis 连接频繁创建/销毁 | 🟡 中 |
| **爬虫无并发控制** | `api/crawler.py:70` | BackgroundTasks 无限并发 | 🟡 中 |
| **章节内容全量读取** | `api/chapters.py:44-45` | 大章节文件一次性读入内存 | 🟡 中 |

### 1.2 稳定性问题

| 问题 | 位置 | 影响 | 严重程度 |
|------|------|------|---------|
| **缺少阅读进度表** | `models/` 无 `reading_progress.py` | 阅读进度功能完全不可用 | 🔴 高 |
| **缺少请求限流** | `main.py` | API 无速率限制，易被刷 | 🔴 高 |
| **错误处理不一致** | 多处 `try/except` 吞异常 | 问题难以排查 | 🟡 中 |
| **日志使用 root logger** | 多处 `logging.getLogger(__name__)` | 日志格式不统一，无法分级 | 🟡 中 |
| **health check 强依赖 psutil** | `api/health.py` | psutil 未安装时 health 报错 | 🟢 低 |

### 1.3 可维护性问题

| 问题 | 位置 | 影响 |
|------|------|------|
| **配置分散** | `.env` + `config.py` + 硬编码 | 配置管理混乱 |
| **缺少 API 文档注释** | 多数路由无 docstring | 自动文档不完整 |
| **类型注解不完整** | 部分函数缺少返回类型 | 静态检查困难 |
| **测试覆盖缺失** | `tests/` 目录内容未知 | 无法保证代码质量 |

---

## 二、优化方案

### 2.1 性能优化

#### 2.1.1 修复搜索 N+1 查询

**当前代码:**
```python
for book_id, relevance in results:
    book_result = await db.execute(select(Book).where(Book.id == book_id))
    book = book_result.scalar_one_or_none()
```

**优化方案:** 使用 `selectinload` 或 `where(Book.id.in_(...))` 批量查询

```python
book_ids = [r[0] for r in results]
book_result = await db.execute(select(Book).where(Book.id.in_(book_ids)))
books = {b.id: b for b in book_result.scalars().all()}
```

#### 2.1.2 优化数据库连接池

SQLite 是文件级数据库，不需要大连接池：
```python
# SQLite 优化
connect_args = {"check_same_thread": False}
if "sqlite" in database_url:
    engine = create_async_engine(
        database_url,
        connect_args=connect_args,
        pool_pre_ping=True,
        pool_recycle=300,
    )
```

#### 2.1.3 添加爬虫并发控制

使用 `asyncio.Semaphore` 限制并发：
```python
_crawler_semaphore = asyncio.Semaphore(3)

async def execute_crawl(task_id: int):
    async with _crawler_semaphore:
        # 爬虫逻辑
```

#### 2.1.4 章节内容流式读取

大文件使用生成器逐块读取：
```python
async def read_chapter_content(file_path: Path, max_size: int):
    content = ""
    async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
        while len(content) < max_size:
            chunk = await f.read(8192)
            if not chunk:
                break
            content += chunk
    return content[:max_size]
```

### 2.2 稳定性优化

#### 2.2.1 创建阅读进度模型

```python
class ReadingProgress(Base):
    __tablename__ = "reading_progress"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), index=True, nullable=False)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=False)
    position = Column(Integer, default=0)
    percent = Column(Integer, default=0)  # 0-100
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('user_id', 'book_id', name='uix_user_book_progress'),
    )
```

#### 2.2.2 添加 API 速率限制

使用 `slowapi` 或自定义中间件：
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@router.post("/login")
@limiter.limit("5/minute")
async def login(...):
```

#### 2.2.3 统一错误处理

创建全局异常处理器：
```python
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    logger.warning(f"HTTP {exc.status_code}: {exc.detail} - {request.url}")
    return JSONResponse(...)

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.exception(f"未处理异常: {request.url}")
    return JSONResponse(status_code=500, content={"detail": "服务器内部错误"})
```

#### 2.2.4 结构化日志

使用 `structlog` 或自定义格式化：
```python
import logging
import sys

formatter = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(formatter)

logger = logging.getLogger("novel-reader")
logger.addHandler(handler)
logger.setLevel(logging.INFO)
```

### 2.3 可维护性优化

#### 2.3.1 配置集中管理

所有配置统一到 `config.py`，移除硬编码：
```python
class Settings(BaseSettings):
    # 数据库
    DATABASE_URL: str = "sqlite+aiosqlite:///data/novel.db"
    DB_POOL_SIZE: int = 5  # SQLite 小连接池
    DB_MAX_OVERFLOW: int = 10
    
    # 缓存
    REDIS_URL: str = "redis://localhost:6379"
    CACHE_TTL: int = 300
    
    # 安全
    SECRET_KEY: str = Field(..., min_length=32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    MAX_LOGIN_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 30
    
    # 性能
    MAX_CHAPTER_CONTENT_SIZE: int = 1024 * 1024  # 1MB
    CRAWLER_MAX_CONCURRENT: int = 3
    CRAWLER_TIMEOUT: int = 30
    
    # 搜索
    SEARCH_CACHE_TTL: int = 300
    SEARCH_MAX_RESULTS: int = 100
```

#### 2.3.2 添加 API 文档

为所有路由添加 docstring：
```python
@router.get("", response_model=BookListResponse)
async def list_books(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    author: Optional[str] = Query(None, description="作者筛选"),
    db: AsyncSession = Depends(get_db_no_commit),
):
    """
    获取书籍列表。
    
    支持分页和按作者筛选。
    """
```

---

## 三、实施计划

### Phase 1: 稳定性基础（高优先级）
1. 创建 `ReadingProgress` 模型 + API
2. 添加全局异常处理中间件
3. 配置结构化日志
4. 添加 API 速率限制

### Phase 2: 性能优化（中优先级）
5. 修复搜索 N+1 查询
6. 优化数据库连接池配置
7. 添加爬虫并发控制
8. 章节内容流式读取

### Phase 3: 可维护性（低优先级）
9. 配置集中化，移除硬编码
10. 完善 API 文档注释
11. 统一类型注解
12. 添加基础测试

---

## 四、验收标准

- [ ] 搜索 50 条结果只产生 ≤2 次数据库查询
- [ ] 阅读进度 API 可正常读写
- [ ] 连续快速请求 10 次登录会被限流
- [ ] 爬虫同时最多 3 个任务运行
- [ ] 日志包含时间、级别、模块名、消息
- [ ] 所有配置项可从环境变量覆盖
