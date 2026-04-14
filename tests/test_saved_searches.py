"""Tests for saved searches and smart folders (SRCH-04, SRCH-05)."""
import pytest
from httpx import AsyncClient

from app.models.user import User


@pytest.mark.asyncio
async def test_create_saved_search(async_client: AsyncClient, admin_token: str):
    """POST /saved-searches/ creates a saved search."""
    resp = await async_client.post(
        "/api/v1/saved-searches/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "My Search",
            "query": "contract",
            "filters": {},
            "is_smart_folder": False,
        },
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["name"] == "My Search"
    assert data["query"] == "contract"
    assert data["is_smart_folder"] is False


@pytest.mark.asyncio
async def test_list_saved_searches(async_client: AsyncClient, admin_token: str):
    """GET /saved-searches/ returns user's saved searches."""
    # Create two
    await async_client.post(
        "/api/v1/saved-searches/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "Search 1", "query": "alpha", "filters": {}},
    )
    await async_client.post(
        "/api/v1/saved-searches/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "Search 2", "query": "beta", "filters": {}},
    )

    resp = await async_client.get(
        "/api/v1/saved-searches/",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) >= 2


@pytest.mark.asyncio
async def test_smart_folders_filter(async_client: AsyncClient, admin_token: str):
    """GET /saved-searches/?smart_folders_only=true returns only smart folders."""
    await async_client.post(
        "/api/v1/saved-searches/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "Regular", "query": "test", "filters": {}, "is_smart_folder": False},
    )
    await async_client.post(
        "/api/v1/saved-searches/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "Smart", "query": "test", "filters": {}, "is_smart_folder": True},
    )

    resp = await async_client.get(
        "/api/v1/saved-searches/?smart_folders_only=true",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    for item in data:
        assert item["is_smart_folder"] is True


@pytest.mark.asyncio
async def test_update_saved_search(async_client: AsyncClient, admin_token: str):
    """PUT /saved-searches/{id} updates a saved search."""
    create = await async_client.post(
        "/api/v1/saved-searches/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "Old Name", "query": "old", "filters": {}},
    )
    search_id = create.json()["data"]["id"]

    resp = await async_client.put(
        f"/api/v1/saved-searches/{search_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "New Name", "query": "new"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "New Name"
    assert resp.json()["data"]["query"] == "new"


@pytest.mark.asyncio
async def test_delete_saved_search(async_client: AsyncClient, admin_token: str):
    """DELETE /saved-searches/{id} removes a saved search."""
    create = await async_client.post(
        "/api/v1/saved-searches/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "To Delete", "query": "bye", "filters": {}},
    )
    search_id = create.json()["data"]["id"]

    resp = await async_client.delete(
        f"/api/v1/saved-searches/{search_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_saved_searches_are_per_user(
    async_client: AsyncClient, admin_token: str, regular_token: str
):
    """User A's saved searches are not visible to User B."""
    await async_client.post(
        "/api/v1/saved-searches/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "Admin Search", "query": "admin", "filters": {}},
    )

    resp = await async_client.get(
        "/api/v1/saved-searches/",
        headers={"Authorization": f"Bearer {regular_token}"},
    )
    data = resp.json()["data"]
    names = [s["name"] for s in data]
    assert "Admin Search" not in names
