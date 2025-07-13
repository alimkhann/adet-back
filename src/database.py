from .config import settings
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from typing import AsyncGenerator

DATABASE_URL = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")

async_engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    future=True
)

Base = declarative_base()

async_session_maker = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_db():
    # In the future, you could add logic here to check for migrations
    # or seed the database on startup.
    pass

async def close_db():
    await async_engine.dispose()

async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    print(">>>> ENTERED get_async_db dependency")
    async with async_session_maker() as session:
        try:
            print(">>>> get_async_db about to yield session")
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

# Alias for legacy code
get_db = get_async_db