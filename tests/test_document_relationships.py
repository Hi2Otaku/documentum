"""Tests for document relationships (REL-01, REL-02, REL-03)."""
import uuid

import pytest
from httpx import AsyncClient

from app.models.user import User


@pytest.mark.asyncio
async def test_create_relationship(async_client: AsyncClient, admin_token: str):
    """POST /documents/{id}/relationships creates a typed relationship."""
    # Create two documents
    doc1 = await async_client.post(
        "/api/v1/documents/",
        headers={"Authorization": f"Bearer {admin_token}"},
        files={"file": ("a.txt", b"doc one", "text/plain")},
        data={"title": "Document A"},
    )
    doc2 = await async_client.post(
        "/api/v1/documents/",
        headers={"Authorization": f"Bearer {admin_token}"},
        files={"file": ("b.txt", b"doc two", "text/plain")},
        data={"title": "Document B"},
    )
    doc1_id = doc1.json()["data"]["id"]
    doc2_id = doc2.json()["data"]["id"]

    # Create relationship
    resp = await async_client.post(
        f"/api/v1/documents/{doc1_id}/relationships",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "target_document_id": doc2_id,
            "relationship_type": "references",
        },
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["source_document_id"] == doc1_id
    assert data["target_document_id"] == doc2_id
    assert data["relationship_type"] == "references"


@pytest.mark.asyncio
async def test_list_relationships_bidirectional(async_client: AsyncClient, admin_token: str):
    """GET /documents/{id}/relationships returns both outgoing and incoming."""
    doc1 = await async_client.post(
        "/api/v1/documents/",
        headers={"Authorization": f"Bearer {admin_token}"},
        files={"file": ("a.txt", b"one", "text/plain")},
        data={"title": "Doc A"},
    )
    doc2 = await async_client.post(
        "/api/v1/documents/",
        headers={"Authorization": f"Bearer {admin_token}"},
        files={"file": ("b.txt", b"two", "text/plain")},
        data={"title": "Doc B"},
    )
    doc1_id = doc1.json()["data"]["id"]
    doc2_id = doc2.json()["data"]["id"]

    # Create: A references B
    await async_client.post(
        f"/api/v1/documents/{doc1_id}/relationships",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"target_document_id": doc2_id, "relationship_type": "references"},
    )

    # List from A — should see outgoing
    resp_a = await async_client.get(
        f"/api/v1/documents/{doc1_id}/relationships",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_a.status_code == 200
    rels_a = resp_a.json()["data"]
    assert len(rels_a) >= 1

    # List from B — should see incoming
    resp_b = await async_client.get(
        f"/api/v1/documents/{doc2_id}/relationships",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_b.status_code == 200
    rels_b = resp_b.json()["data"]
    assert len(rels_b) >= 1


@pytest.mark.asyncio
async def test_delete_relationship(async_client: AsyncClient, admin_token: str):
    """DELETE /documents/{id}/relationships/{rel_id} removes relationship."""
    doc1 = await async_client.post(
        "/api/v1/documents/",
        headers={"Authorization": f"Bearer {admin_token}"},
        files={"file": ("a.txt", b"one", "text/plain")},
        data={"title": "Doc A"},
    )
    doc2 = await async_client.post(
        "/api/v1/documents/",
        headers={"Authorization": f"Bearer {admin_token}"},
        files={"file": ("b.txt", b"two", "text/plain")},
        data={"title": "Doc B"},
    )
    doc1_id = doc1.json()["data"]["id"]
    doc2_id = doc2.json()["data"]["id"]

    create_resp = await async_client.post(
        f"/api/v1/documents/{doc1_id}/relationships",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"target_document_id": doc2_id, "relationship_type": "supersedes"},
    )
    rel_id = create_resp.json()["data"]["id"]

    del_resp = await async_client.delete(
        f"/api/v1/documents/{doc1_id}/relationships/{rel_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert del_resp.status_code == 200

    # Verify gone
    list_resp = await async_client.get(
        f"/api/v1/documents/{doc1_id}/relationships",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    remaining = [r for r in list_resp.json()["data"] if r["id"] == rel_id]
    assert len(remaining) == 0


@pytest.mark.asyncio
async def test_duplicate_relationship_rejected(async_client: AsyncClient, admin_token: str):
    """Creating the same relationship twice should fail."""
    doc1 = await async_client.post(
        "/api/v1/documents/",
        headers={"Authorization": f"Bearer {admin_token}"},
        files={"file": ("a.txt", b"one", "text/plain")},
        data={"title": "Doc A"},
    )
    doc2 = await async_client.post(
        "/api/v1/documents/",
        headers={"Authorization": f"Bearer {admin_token}"},
        files={"file": ("b.txt", b"two", "text/plain")},
        data={"title": "Doc B"},
    )
    doc1_id = doc1.json()["data"]["id"]
    doc2_id = doc2.json()["data"]["id"]

    resp1 = await async_client.post(
        f"/api/v1/documents/{doc1_id}/relationships",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"target_document_id": doc2_id, "relationship_type": "references"},
    )
    assert resp1.status_code == 201

    resp2 = await async_client.post(
        f"/api/v1/documents/{doc1_id}/relationships",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"target_document_id": doc2_id, "relationship_type": "references"},
    )
    assert resp2.status_code in (400, 409, 422)
