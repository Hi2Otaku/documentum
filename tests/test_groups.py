"""Tests for group CRUD (USER-03)."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_group(async_client: AsyncClient, admin_token: str):
    """POST /api/v1/groups creates a group (201)."""
    response = await async_client.post(
        "/api/v1/groups",
        json={"name": "ReviewerGroup"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["data"]["name"] == "ReviewerGroup"


@pytest.mark.asyncio
async def test_create_group_duplicate(async_client: AsyncClient, admin_token: str):
    """Creating a group with duplicate name returns 409."""
    await async_client.post(
        "/api/v1/groups",
        json={"name": "DupeGroup"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    response = await async_client.post(
        "/api/v1/groups",
        json={"name": "DupeGroup"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_add_users_to_group(async_client: AsyncClient, admin_token: str):
    """POST /api/v1/groups/{id}/members adds users to a group."""
    # Create a group
    group_resp = await async_client.post(
        "/api/v1/groups",
        json={"name": "MemberGroup"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    group_id = group_resp.json()["data"]["id"]

    # Create a user
    user_resp = await async_client.post(
        "/api/v1/users",
        json={"username": "groupmember", "password": "password123"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    user_id = user_resp.json()["data"]["id"]

    # Add user to group
    response = await async_client.post(
        f"/api/v1/groups/{group_id}/members",
        json={"user_ids": [user_id]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_groups(async_client: AsyncClient, admin_token: str):
    """GET /api/v1/groups returns paginated list."""
    await async_client.post(
        "/api/v1/groups",
        json={"name": "ListGroup1"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    await async_client.post(
        "/api/v1/groups",
        json={"name": "ListGroup2"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    response = await async_client.get(
        "/api/v1/groups",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) >= 2
