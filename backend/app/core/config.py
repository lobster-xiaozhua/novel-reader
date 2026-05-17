from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DATA_DIR = _PROJECT_ROOT / "data"
_DATA_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "Novel Reader"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # 数据库配置
    DATABASE_URL: str = f"sqlite+aiosqlite:///{_DATA_DIR / 'novel.db'}"

    # Redis配置
    REDIS_URL: str = "redis://localhost:6379"

    # JWT配置
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # 路径配置 - 统一缓存目录
    DATA_DIR: str = str(_DATA_DIR)
    BOOKS_DIR: str = str(_DATA_DIR / "books")
    INDEX_DIR: str = str(_DATA_DIR / "index")
    STATIC_DIR: str = str(_DATA_DIR / "static")
    LOGS_DIR: str = str(_DATA_DIR / "logs")
    CACHE_DIR: str = str(_DATA_DIR / "cache")

    # 安全配置
    PASSWORD_MIN_LENGTH: int = 8
    BCRYPT_ROUNDS: int = 12
    MAX_LOGIN_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15

    # 爬虫配置
    CRAWLER_MAX_CONCURRENT: int = 5
    CRAWLER_REQUEST_DELAY: float = 1.0
    CRAWLER_MAX_RETRIES: int = 3
    CRAWLER_TIMEOUT: int = 30

    # 性能配置
    CACHE_EXPIRE_MINUTES: int = 10
    SEARCH_RESULTS_LIMIT: int = 50
    PAGE_SIZE: int = 20

    # 内存优化配置
    MAX_CHAPTER_CONTENT_SIZE: int = 50000  # 章节内容最大50KB
    CHAPTER_BATCH_SIZE: int = 50  # 批量处理章节数
    FTS_BATCH_SIZE: int = 100  # FTS索引批量大小
    DB_POOL_SIZE: int = 5  # 数据库连接池大小
    DB_MAX_OVERFLOW: int = 10  # 连接池溢出
    REDIS_POOL_SIZE: int = 10  # Redis连接池大小

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
