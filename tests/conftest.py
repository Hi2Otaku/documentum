import asyncio
import os
import uuid
from typing import AsyncGenerator

# Set environment variables BEFORE any app imports so Settings() picks them up
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("MINIO_ENDPOINT", "localhost:9000")
os.environ.setdefault("MINIO_ACCESS_KEY", "minioadmin")
os.environ.setdefault("MINIO_SECRET_KEY", "minioadmin")

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.core.security import create_access_token, hash_password
from app.main import app as fastapi_app
from app.models.base import Base
from app.models.user import User

# Import all models so Base.metadata knows about every table
import app.models  # noqa: F401

# Use aiosqlite for test DB (in-memory, no Docker needed)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
test_session_factory = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for session-scoped fixtures."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def setup_database():
    """Create all tables before each test, drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a test database session."""
    async with test_session_factory() as session:
        yield session


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create an admin user for testing."""
    user = User(
        id=uuid.uuid4(),
        username="admin",
        hashed_password=hash_password("adminpass123"),
        is_active=True,
        is_superuser=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def admin_token(admin_user: User) -> str:
    """Create JWT token for admin user."""
    return create_access_token({"sub": str(admin_user.id), "username": admin_user.username})


@pytest.fixture
async def regular_user(db_session: AsyncSession) -> User:
    """Create a non-admin user for testing."""
    user = User(
        id=uuid.uuid4(),
        username="regularuser",
        hashed_password=hash_password("userpass123"),
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def regular_token(regular_user: User) -> str:
    """Create JWT token for regular user."""
    return create_access_token({"sub": str(regular_user.id), "username": regular_user.username})


@pytest.fixture(autouse=True)
def mock_minio(monkeypatch):
    """Replace MinIO operations with in-memory dict storage for all tests."""
    storage = {}

    async def mock_upload(object_name, data, content_type="application/octet-stream"):
        storage[object_name] = data
        return object_name

    async def mock_download(object_name):
        if object_name not in storage:
            raise Exception(f"NoSuchKey: {object_name}")
        return storage[object_name]

    async def mock_delete(object_name):
        storage.pop(object_name, None)

    async def mock_ensure_bucket():
        pass  # No-op in tests

    # Patch on the source module
    monkeypatch.setattr("app.core.minio_client.upload_object", mock_upload)
    monkeypatch.setattr("app.core.minio_client.download_object", mock_download)
    monkeypatch.setattr("app.core.minio_client.delete_object", mock_delete)
    monkeypatch.setattr("app.core.minio_client.ensure_documents_bucket", mock_ensure_bucket)
    # Patch on the consumer module (already-bound references from import)
    monkeypatch.setattr("app.services.document_service.upload_object", mock_upload)
    monkeypatch.setattr("app.services.document_service.download_object", mock_download)
    monkeypatch.setattr("app.services.document_service.delete_object", mock_delete)
    return storage


@pytest.fixture
async def async_client(db_session: AsyncSession, mock_minio) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client with overridden DB dependency.

    Depends on mock_minio to ensure MinIO functions are patched before the
    app lifespan runs (which calls ensure_documents_bucket on startup).
    """

    async def override_get_db():
        yield db_session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=fastapi_app),
        base_url="http://test",
        follow_redirects=True,
    ) as client:
        yield client
    fastapi_app.dependency_overrides.clear()
