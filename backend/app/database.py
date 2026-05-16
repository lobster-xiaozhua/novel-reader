from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from pathlib import Path
from app.core.config import get_settings

settings = get_settings()

if "sqlite" in settings.DATABASE_URL:
    engine = create_async_engine(
        settings.DATABASE_URL,
        pool_size=1,
        max_overflow=0,
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_async_engine(
        settings.DATABASE_URL,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_recycle=settings.DB_POOL_RECYCLE,
        pool_pre_ping=True
    )

Base = declarative_base()

AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def get_db_no_commit():
    async with AsyncSessionLocal() as session:
        yield session

async def init_database():
    # 确保数据目录存在
    data_dir = Path(settings.DATA_DIR)
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建所有表
    async with engine.begin() as conn:
        from app.models import (
            User, Book, Chapter, ReadingProgress,
            Favorite, FavoriteFolder, CrawlerTask,
            Tag, BookTag
        )
        await conn.run_sync(Base.metadata.create_all)