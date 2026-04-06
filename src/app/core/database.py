from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

_engine_kwargs: dict = {
    "echo": settings.debug,
}

# SQLite does not support pool_size / max_overflow (uses StaticPool)
if not settings.database_url.startswith("sqlite"):
    _engine_kwargs["pool_size"] = 5
    _engine_kwargs["max_overflow"] = 10

engine = create_async_engine(settings.database_url, **_engine_kwargs)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    """Dependency that yields an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def create_task_session_factory():
    """Create a fresh engine + session factory for use in Celery tasks.

    Each ``asyncio.run()`` call creates a new event loop, so the module-level
    engine (whose pool is tied to the loop that first used it) cannot be reused.
    This function returns a session factory bound to a brand-new engine that
    will work on the *current* event loop.
    """
    task_engine = create_async_engine(settings.database_url, **_engine_kwargs)
    return async_sessionmaker(
        task_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
