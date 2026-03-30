from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import health


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: import engine to verify database connection config
    from app.core.database import engine  # noqa: F401

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

    return application


app = create_app()
