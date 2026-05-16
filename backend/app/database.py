from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import get_settings

settings = get_settings()

Base = declarative_base()

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

AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
AsyncSessionLocalNoCommit = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False, autocommit=False)

async def init_database():
    # Import models here to avoid circular import
    from app.models import (
        User,
        Book,
        Chapter,
        ReadingProgress,
        Favorite,
        FavoriteFolder,
        CrawlerTask,
        Tag,
        BookTag
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def get_db_no_commit():
    async with AsyncSessionLocalNoCommit() as session:
        yield session