from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import get_settings

Base = declarative_base()
settings = get_settings()

DB_POOL_RECYCLE = getattr(settings, 'DB_POOL_RECYCLE', 3600)

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

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def get_db_no_commit():
    async with AsyncSessionLocal() as session:
        yield session


async def get_db_managed():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)