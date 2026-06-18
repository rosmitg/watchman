from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.portfolio import Base

engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a session and closes it afterwards."""
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    """Create all tables defined on the declarative ``Base`` metadata."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
