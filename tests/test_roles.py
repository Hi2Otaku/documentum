"""Tests for role CRUD (USER-04)."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_role(async_client: AsyncClient, admin_token: str):
    """POST /api/v1/roles creates a role (201)."""
    response = await async_client.post(
        "/api/v1/roles",
        json={"name": "Reviewer"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["data"]["name"] == "Reviewer"


@pytest.mark.asyncio
async def test_assign_role_to_user(async_client: AsyncClient, admin_token: str):
    """POST /api/v1/roles/assign assigns a role to a user."""
    # Create a role
    role_resp = await async_client.post(
        "/api/v1/roles",
        json={"name": "AssignRole"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    role_id = role_resp.json()["data"]["id"]

    # Create a user
    user_resp = await async_client.post(
        "/api/v1/users",
        json={"username": "roleuser", "password": "password123"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    user_id = user_resp.json()["data"]["id"]

    # Assign role
    response = await async_client.post(
        "/api/v1/roles/assign",
        json={"user_id": user_id, "role_id": role_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_roles(async_client: AsyncClient, admin_token: str):
    """GET /api/v1/roles returns paginated list."""
    await async_client.post(
        "/api/v1/roles",
        json={"name": "ListRole1"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    await async_client.post(
        "/api/v1/roles",
        json={"name": "ListRole2"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    response = await async_client.get(
        "/api/v1/roles",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) >= 2
