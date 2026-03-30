"""Tests for user CRUD (USER-01)."""

import pytest
from httpx import AsyncClient

from app.models.user import User


@pytest.mark.asyncio
async def test_create_user(async_client: AsyncClient, admin_token: str):
    """POST /api/v1/users with admin token creates a user (201)."""
    response = await async_client.post(
        "/api/v1/users",
        json={"username": "newuser", "password": "password123"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["data"]["username"] == "newuser"
    assert body["data"]["id"] is not None


@pytest.mark.asyncio
async def test_create_user_duplicate(async_client: AsyncClient, admin_token: str):
    """Creating a user with a duplicate username returns 409."""
    await async_client.post(
        "/api/v1/users",
        json={"username": "dupeuser", "password": "password123"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    response = await async_client.post(
        "/api/v1/users",
        json={"username": "dupeuser", "password": "password123"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_create_user_forbidden_non_admin(
    async_client: AsyncClient, regular_token: str
):
    """POST /api/v1/users with non-admin token returns 403."""
    response = await async_client.post(
        "/api/v1/users",
        json={"username": "forbidden", "password": "password123"},
        headers={"Authorization": f"Bearer {regular_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_users(async_client: AsyncClient, admin_token: str):
    """GET /api/v1/users returns paginated list of users."""
    # Create two users
    await async_client.post(
        "/api/v1/users",
        json={"username": "listuser1", "password": "password123"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    await async_client.post(
        "/api/v1/users",
        json={"username": "listuser2", "password": "password123"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    response = await async_client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    # admin_user fixture + 2 created = at least 3
    assert len(body["data"]) >= 2
    assert body["meta"]["total_count"] >= 2
    assert "page" in body["meta"]
    assert "page_size" in body["meta"]


@pytest.mark.asyncio
async def test_get_user_by_id(async_client: AsyncClient, admin_token: str):
    """GET /api/v1/users/{id} returns the correct user."""
    create_resp = await async_client.post(
        "/api/v1/users",
        json={"username": "getuser", "password": "password123"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    user_id = create_resp.json()["data"]["id"]

    response = await async_client.get(
        f"/api/v1/users/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["username"] == "getuser"


@pytest.mark.asyncio
async def test_update_user(async_client: AsyncClient, admin_token: str):
    """PUT /api/v1/users/{id} updates user fields."""
    create_resp = await async_client.post(
        "/api/v1/users",
        json={"username": "updateuser", "password": "password123"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    user_id = create_resp.json()["data"]["id"]

    response = await async_client.put(
        f"/api/v1/users/{user_id}",
        json={"email": "new@test.com"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["email"] == "new@test.com"


@pytest.mark.asyncio
async def test_delete_user(async_client: AsyncClient, admin_token: str):
    """DELETE /api/v1/users/{id} soft deletes the user."""
    create_resp = await async_client.post(
        "/api/v1/users",
        json={"username": "deleteuser", "password": "password123"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    user_id = create_resp.json()["data"]["id"]

    delete_resp = await async_client.delete(
        f"/api/v1/users/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert delete_resp.status_code == 204

    # Verify user is soft-deleted (GET returns 404)
    get_resp = await async_client.get(
        f"/api/v1/users/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_resp.status_code == 404
