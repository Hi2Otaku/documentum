import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.core.config import settings
from app.routers import auth, documents, groups, health, roles, templates, users

logger = logging.getLogger(__name__)


async def seed_admin():
    """Create admin user on first startup if it doesn't already exist."""
    from app.core.database import async_session_factory
    from app.core.security import hash_password
    from app.models.user import User

    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(User.username == settings.admin_username)
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            admin = User(
                username=settings.admin_username,
                hashed_password=hash_password(settings.admin_password),
                is_superuser=True,
                is_active=True,
            )
            session.add(admin)
            await session.commit()
            logger.info("Admin user '%s' seeded successfully", settings.admin_username)
        else:
            logger.info("Admin user '%s' already exists", settings.admin_username)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: import engine to verify database connection config
    from app.core.database import engine  # noqa: F401

    try:
        await seed_admin()
    except Exception as e:
        logger.warning("Could not seed admin user (DB may not be ready): %s", e)

    try:
        from app.core.minio_client import ensure_documents_bucket

        await ensure_documents_bucket()
    except Exception as e:
        logger.warning("Could not ensure MinIO documents bucket (MinIO may not be ready): %s", e)

    yield
    # Shutdown: dispose of the engine connection pool
    await engine.dispose()


def create_app() -> FastAPI:
    application = FastAPI(
        title="Documentum Workflow Clone API",
        version="0.1.0",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(health.router, prefix=settings.api_v1_prefix)
    application.include_router(auth.router, prefix=settings.api_v1_prefix)
    application.include_router(users.router, prefix=settings.api_v1_prefix)
    application.include_router(groups.router, prefix=settings.api_v1_prefix)
    application.include_router(roles.router, prefix=settings.api_v1_prefix)
    application.include_router(documents.router, prefix=settings.api_v1_prefix)
    application.include_router(templates.router, prefix=settings.api_v1_prefix)

    return application


app = create_app()
