from .config import settings
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

async_engine = create_async_engine(
    settings.database_url.replace('postgresql://', 'postgresql+asyncpg://'),
    echo=True
)

AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

async def get_async_db():
    async with AsyncSessionLocal() as session:
        yield session