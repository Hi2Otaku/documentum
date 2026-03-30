"""Tests for authentication (USER-02)."""

import pytest
from httpx import AsyncClient

from app.models.user import User


@pytest.mark.asyncio
async def test_login_success(async_client: AsyncClient, admin_user: User):
    """POST /api/v1/auth/login with valid credentials returns access_token."""
    response = await async_client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "adminpass123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body["data"]
    assert body["data"]["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_password(async_client: AsyncClient, admin_user: User):
    """POST /api/v1/auth/login with wrong password returns 401."""
    response = await async_client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "wrongpassword"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(async_client: AsyncClient):
    """POST /api/v1/auth/login with unknown username returns 401."""
    response = await async_client.post(
        "/api/v1/auth/login",
        data={"username": "nonexistent", "password": "somepassword"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_no_token(async_client: AsyncClient):
    """GET /api/v1/users without Authorization header returns 401."""
    response = await async_client.get("/api/v1/users")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_invalid_token(async_client: AsyncClient):
    """GET /api/v1/users with invalid Bearer token returns 401."""
    response = await async_client.get(
        "/api/v1/users",
        headers={"Authorization": "Bearer invalidtoken"},
    )
    assert response.status_code == 401
