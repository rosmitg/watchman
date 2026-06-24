from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings


def _create_engine() -> AsyncEngine:
    """Build the async SQLAlchemy engine for the current environment.

    Local/CI connect over TCP using the plain DATABASE_URL. In production on
    Cloud Run, the database is reached through a Cloud SQL Unix socket mounted at
    /cloudsql/<INSTANCE_CONNECTION_NAME>; the asyncpg driver uses it via the URL's
    ``?host=`` query parameter, e.g.

        postgresql+asyncpg://USER:PASSWORD@/watchman?host=/cloudsql/watchman-gcp:australia-southeast1:watchman-db

    For the Cloud SQL path we keep a small connection pool (Cloud Run instances
    are short-lived and scale to zero) and enable pre-ping so connections dropped
    while an instance was idle are recycled rather than handed out dead.
    """
    if settings.is_cloud_sql:
        return create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            future=True,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=2,
        )

    return create_async_engine(settings.DATABASE_URL, echo=False, future=True)


engine = _create_engine()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a session and closes it afterwards."""
    async with AsyncSessionLocal() as session:
        yield session
