from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DATA_DIR = _PROJECT_ROOT / "data"
_DATA_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    APP_NAME: str = "Novel Reader"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    DATABASE_URL: str = f"sqlite+aiosqlite:///{_DATA_DIR / 'novel.db'}"

    REDIS_URL: str = "redis://localhost:6379"

    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    DATA_DIR: str = str(_DATA_DIR)
    BOOKS_DIR: str = str(_DATA_DIR / "books")
    INDEX_DIR: str = str(_DATA_DIR / "index")
    STATIC_DIR: str = str(_DATA_DIR / "static")
    LOGS_DIR: str = str(_DATA_DIR / "logs")
    CACHE_DIR: str = str(_DATA_DIR / "cache")

    PASSWORD_MIN_LENGTH: int = 8
    BCRYPT_ROUNDS: int = 12
    MAX_LOGIN_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15

    CRAWLER_MAX_CONCURRENT: int = 5
    CRAWLER_REQUEST_DELAY: float = 1.0
    CRAWLER_MAX_RETRIES: int = 3
    CRAWLER_TIMEOUT: int = 30

    CACHE_EXPIRE_MINUTES: int = 10
    SEARCH_RESULTS_LIMIT: int = 50
    PAGE_SIZE: int = 20

    MAX_CHAPTER_CONTENT_SIZE: int = 50000
    CHAPTER_BATCH_SIZE: int = 50
    FTS_BATCH_SIZE: int = 100
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_RECYCLE: int = 3600
    REDIS_POOL_SIZE: int = 10

    LOGIN_RATE_LIMIT_MAX: int = 5
    LOGIN_RATE_LIMIT_WINDOW: int = 300

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
