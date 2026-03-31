"""Integration tests for document management (DOC-01 through DOC-08)."""

import json
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


# ── Helper ──────────────────────────────────────────────────────────────────


async def _upload_file(
    client: AsyncClient,
    token: str,
    title: str = "Test Doc",
    filename: str = "test.pdf",
    content: bytes = b"test content",
    author: str | None = None,
    custom_properties: dict | None = None,
):
    """Helper to upload a document and return the response."""
    files = {"file": (filename, content, "application/pdf")}
    data: dict = {"title": title}
    if author:
        data["author"] = author
    if custom_properties:
        data["custom_properties"] = json.dumps(custom_properties)
    return await client.post(
        "/api/v1/documents",
        files=files,
        data=data,
        headers={"Authorization": f"Bearer {token}"},
    )


async def _checkout(client: AsyncClient, token: str, doc_id: str):
    """Helper to checkout a document."""
    return await client.post(
        f"/api/v1/documents/{doc_id}/checkout",
        headers={"Authorization": f"Bearer {token}"},
    )


async def _checkin(
    client: AsyncClient,
    token: str,
    doc_id: str,
    content: bytes = b"new content",
    filename: str = "test.pdf",
    comment: str | None = None,
):
    """Helper to checkin a document with new file content."""
    files = {"file": (filename, content, "application/pdf")}
    data: dict = {}
    if comment:
        data["comment"] = comment
    return await client.post(
        f"/api/v1/documents/{doc_id}/checkin",
        files=files,
        data=data,
        headers={"Authorization": f"Bearer {token}"},
    )


# ── DOC-01: Upload ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upload_document(async_client: AsyncClient, admin_token: str):
    """Upload a file creates a document with version 0.1."""
    resp = await _upload_file(async_client, admin_token)
    assert resp.status_code == 201
    body = resp.json()
    assert body["data"]["id"] is not None
    assert body["data"]["title"] == "Test Doc"
    assert body["data"]["filename"] == "test.pdf"
    assert body["data"]["current_version"] == "0.1"


@pytest.mark.asyncio
async def test_upload_document_unauthenticated(async_client: AsyncClient):
    """Upload without a token returns 401."""
    files = {"file": ("test.pdf", b"data", "application/pdf")}
    resp = await async_client.post(
        "/api/v1/documents",
        files=files,
        data={"title": "No Auth"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_upload_with_author_and_custom_properties(
    async_client: AsyncClient, admin_token: str
):
    """Upload with author and custom_properties persists them."""
    resp = await _upload_file(
        async_client,
        admin_token,
        author="John",
        custom_properties={"department": "legal"},
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["author"] == "John"
    assert data["custom_properties"]["department"] == "legal"


# ── DOC-02: Version Numbering ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_initial_version_is_0_1(async_client: AsyncClient, admin_token: str):
    """Upload creates version 0.1 (major=0, minor=1)."""
    resp = await _upload_file(async_client, admin_token)
    data = resp.json()["data"]
    assert data["current_major_version"] == 0
    assert data["current_minor_version"] == 1


@pytest.mark.asyncio
async def test_version_numbering(async_client: AsyncClient, admin_token: str):
    """Each checkin increments the minor version: 0.1 -> 0.2 -> 0.3."""
    resp = await _upload_file(async_client, admin_token, content=b"v1")
    doc_id = resp.json()["data"]["id"]

    # Checkout + checkin => 0.2
    await _checkout(async_client, admin_token, doc_id)
    resp2 = await _checkin(async_client, admin_token, doc_id, content=b"v2")
    assert resp2.status_code == 200
    assert resp2.json()["data"]["version_label"] == "0.2"

    # Checkout + checkin => 0.3
    await _checkout(async_client, admin_token, doc_id)
    resp3 = await _checkin(async_client, admin_token, doc_id, content=b"v3")
    assert resp3.status_code == 200
    assert resp3.json()["data"]["version_label"] == "0.3"

    # Version history should show 3 versions
    ver_resp = await async_client.get(
        f"/api/v1/documents/{doc_id}/versions",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert ver_resp.status_code == 200
    versions = ver_resp.json()["data"]
    assert len(versions) == 3
    labels = {v["version_label"] for v in versions}
    assert labels == {"0.1", "0.2", "0.3"}


# ── DOC-03: Checkout (Lock) ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_checkout_document(async_client: AsyncClient, admin_token: str):
    """Checkout sets locked_by and locked_at."""
    resp = await _upload_file(async_client, admin_token)
    doc_id = resp.json()["data"]["id"]

    co_resp = await _checkout(async_client, admin_token, doc_id)
    assert co_resp.status_code == 200
    data = co_resp.json()["data"]
    assert data["locked_by"] is not None
    assert data["locked_at"] is not None


@pytest.mark.asyncio
async def test_checkout_already_locked(
    async_client: AsyncClient, admin_token: str, regular_token: str
):
    """Second checkout by different user returns 403 (ACL) since creator has ADMIN ACL."""
    resp = await _upload_file(async_client, admin_token)
    doc_id = resp.json()["data"]["id"]

    await _checkout(async_client, admin_token, doc_id)
    co2_resp = await _checkout(async_client, regular_token, doc_id)
    # Regular user has no ACL entry on admin-created document -> 403
    assert co2_resp.status_code == 403


@pytest.mark.asyncio
async def test_checkout_already_locked_same_user(
    async_client: AsyncClient, admin_token: str
):
    """Same user cannot checkout twice; returns 409."""
    resp = await _upload_file(async_client, admin_token)
    doc_id = resp.json()["data"]["id"]

    await _checkout(async_client, admin_token, doc_id)
    co2_resp = await _checkout(async_client, admin_token, doc_id)
    assert co2_resp.status_code == 409


# ── DOC-04: Checkin ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_checkin_creates_version(async_client: AsyncClient, admin_token: str):
    """Checkin after checkout creates a new version."""
    resp = await _upload_file(async_client, admin_token, content=b"original")
    doc_id = resp.json()["data"]["id"]

    await _checkout(async_client, admin_token, doc_id)
    ci_resp = await _checkin(async_client, admin_token, doc_id, content=b"updated")
    assert ci_resp.status_code == 200
    assert ci_resp.json()["data"]["version_label"] == "0.2"


@pytest.mark.asyncio
async def test_checkin_without_lock(async_client: AsyncClient, admin_token: str):
    """Checkin without prior checkout returns 403."""
    resp = await _upload_file(async_client, admin_token)
    doc_id = resp.json()["data"]["id"]

    ci_resp = await _checkin(async_client, admin_token, doc_id, content=b"nope")
    assert ci_resp.status_code == 403


@pytest.mark.asyncio
async def test_checkin_wrong_user(
    async_client: AsyncClient, admin_token: str, regular_token: str
):
    """User B cannot checkin a document locked by user A."""
    resp = await _upload_file(async_client, admin_token, content=b"original")
    doc_id = resp.json()["data"]["id"]

    await _checkout(async_client, admin_token, doc_id)
    ci_resp = await _checkin(async_client, regular_token, doc_id, content=b"hijack")
    assert ci_resp.status_code == 403


@pytest.mark.asyncio
async def test_checkin_unchanged_content(async_client: AsyncClient, admin_token: str):
    """Checkin with same content does not create a new version (SHA-256 dedup)."""
    original_content = b"exactly the same bytes"
    resp = await _upload_file(async_client, admin_token, content=original_content)
    doc_id = resp.json()["data"]["id"]

    await _checkout(async_client, admin_token, doc_id)
    ci_resp = await _checkin(async_client, admin_token, doc_id, content=original_content)
    assert ci_resp.status_code == 200
    body = ci_resp.json()
    assert body["data"] is None
    assert "unchanged" in body["meta"]["message"].lower()

    # Verify version list still has only 1 version
    ver_resp = await async_client.get(
        f"/api/v1/documents/{doc_id}/versions",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert len(ver_resp.json()["data"]) == 1


# ── DOC-05: Force Unlock ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_force_unlock(
    async_client: AsyncClient, admin_token: str, regular_token: str
):
    """Admin can force-unlock a document locked by another user."""
    # Regular user uploads (gets ADMIN ACL) and checks out
    resp = await _upload_file(async_client, regular_token)
    doc_id = resp.json()["data"]["id"]

    await _checkout(async_client, regular_token, doc_id)

    # Admin force-unlocks
    unlock_resp = await async_client.post(
        f"/api/v1/documents/{doc_id}/unlock",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert unlock_resp.status_code == 200
    assert unlock_resp.json()["data"]["locked_by"] is None


@pytest.mark.asyncio
async def test_force_unlock_requires_admin(
    async_client: AsyncClient, admin_token: str, regular_token: str
):
    """Non-admin cannot force-unlock; returns 403."""
    resp = await _upload_file(async_client, admin_token)
    doc_id = resp.json()["data"]["id"]

    await _checkout(async_client, admin_token, doc_id)

    unlock_resp = await async_client.post(
        f"/api/v1/documents/{doc_id}/unlock",
        headers={"Authorization": f"Bearer {regular_token}"},
    )
    assert unlock_resp.status_code == 403


@pytest.mark.asyncio
async def test_force_unlock_not_locked(async_client: AsyncClient, admin_token: str):
    """Force-unlock on an unlocked document returns 400."""
    resp = await _upload_file(async_client, admin_token)
    doc_id = resp.json()["data"]["id"]

    unlock_resp = await async_client.post(
        f"/api/v1/documents/{doc_id}/unlock",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert unlock_resp.status_code == 400


# ── DOC-06: Version History and Download ────────────────────────────────────


@pytest.mark.asyncio
async def test_list_versions(async_client: AsyncClient, admin_token: str):
    """Version list returns all versions after multiple checkins."""
    resp = await _upload_file(async_client, admin_token, content=b"v1")
    doc_id = resp.json()["data"]["id"]

    await _checkout(async_client, admin_token, doc_id)
    await _checkin(async_client, admin_token, doc_id, content=b"v2")

    await _checkout(async_client, admin_token, doc_id)
    await _checkin(async_client, admin_token, doc_id, content=b"v3")

    ver_resp = await async_client.get(
        f"/api/v1/documents/{doc_id}/versions",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert ver_resp.status_code == 200
    versions = ver_resp.json()["data"]
    assert len(versions) == 3


@pytest.mark.asyncio
async def test_download_version(async_client: AsyncClient, admin_token: str):
    """Download returns correct file content and Content-Disposition header."""
    file_content = b"important document bytes"
    resp = await _upload_file(
        async_client, admin_token, content=file_content, filename="report.pdf"
    )
    doc_id = resp.json()["data"]["id"]

    # Get the version id
    ver_resp = await async_client.get(
        f"/api/v1/documents/{doc_id}/versions",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    version_id = ver_resp.json()["data"][0]["id"]

    dl_resp = await async_client.get(
        f"/api/v1/documents/{doc_id}/versions/{version_id}/download",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert dl_resp.status_code == 200
    assert dl_resp.content == file_content
    assert "report.pdf" in dl_resp.headers.get("content-disposition", "")


@pytest.mark.asyncio
async def test_download_nonexistent_version(
    async_client: AsyncClient, admin_token: str
):
    """Download with a random version_id returns 404."""
    resp = await _upload_file(async_client, admin_token)
    doc_id = resp.json()["data"]["id"]
    fake_version_id = str(uuid.uuid4())

    dl_resp = await async_client.get(
        f"/api/v1/documents/{doc_id}/versions/{fake_version_id}/download",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert dl_resp.status_code == 404


# ── DOC-07: Metadata ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_custom_metadata_on_upload(async_client: AsyncClient, admin_token: str):
    """Custom properties set on upload persist in the response."""
    props = {"department": "legal", "priority": "high"}
    resp = await _upload_file(async_client, admin_token, custom_properties=props)
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["custom_properties"]["department"] == "legal"
    assert data["custom_properties"]["priority"] == "high"


@pytest.mark.asyncio
async def test_update_metadata(async_client: AsyncClient, admin_token: str):
    """PUT updates title and custom_properties."""
    resp = await _upload_file(async_client, admin_token, title="Old Title")
    doc_id = resp.json()["data"]["id"]

    put_resp = await async_client.put(
        f"/api/v1/documents/{doc_id}",
        json={"title": "New Title", "custom_properties": {"status": "final"}},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert put_resp.status_code == 200
    data = put_resp.json()["data"]
    assert data["title"] == "New Title"
    assert data["custom_properties"]["status"] == "final"


@pytest.mark.asyncio
async def test_list_documents_pagination(async_client: AsyncClient, admin_token: str):
    """Pagination: 3 docs with page_size=2 returns 2 results and total_count=3."""
    for i in range(3):
        await _upload_file(async_client, admin_token, title=f"PagDoc {i}")

    resp = await async_client.get(
        "/api/v1/documents?page=1&page_size=2",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) == 2
    assert body["meta"]["total_count"] == 3


@pytest.mark.asyncio
async def test_list_documents_filter_by_title(
    async_client: AsyncClient, admin_token: str
):
    """Filter by partial title match returns only matching documents."""
    await _upload_file(async_client, admin_token, title="Alpha Report")
    await _upload_file(async_client, admin_token, title="Beta Summary")
    await _upload_file(async_client, admin_token, title="Alpha Draft")

    resp = await async_client.get(
        "/api/v1/documents?title=Alpha",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 2
    titles = {d["title"] for d in data}
    assert titles == {"Alpha Report", "Alpha Draft"}


# ── DOC-08: MinIO Integration ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_minio_stores_content(
    async_client: AsyncClient, admin_token: str, mock_minio: dict
):
    """Upload stores file bytes in the mock MinIO storage dict."""
    file_bytes = b"stored in minio"
    resp = await _upload_file(async_client, admin_token, content=file_bytes)
    assert resp.status_code == 201

    # The storage dict should have exactly one entry with the correct content
    assert len(mock_minio) == 1
    stored_content = list(mock_minio.values())[0]
    assert stored_content == file_bytes


@pytest.mark.asyncio
async def test_download_returns_minio_content(
    async_client: AsyncClient, admin_token: str
):
    """Upload then download returns identical bytes."""
    file_bytes = b"roundtrip content check"
    resp = await _upload_file(async_client, admin_token, content=file_bytes)
    doc_id = resp.json()["data"]["id"]

    ver_resp = await async_client.get(
        f"/api/v1/documents/{doc_id}/versions",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    version_id = ver_resp.json()["data"][0]["id"]

    dl_resp = await async_client.get(
        f"/api/v1/documents/{doc_id}/versions/{version_id}/download",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert dl_resp.status_code == 200
    assert dl_resp.content == file_bytes


# ── Audit Trail ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upload_creates_audit_record(
    async_client: AsyncClient, admin_token: str, db_session: AsyncSession
):
    """Upload produces an audit record with action='upload'."""
    await _upload_file(async_client, admin_token)

    result = await db_session.execute(
        select(AuditLog).where(AuditLog.action == "upload")
    )
    records = list(result.scalars().all())
    assert len(records) >= 1
    assert records[0].entity_type == "document"


@pytest.mark.asyncio
async def test_checkout_creates_audit_record(
    async_client: AsyncClient, admin_token: str, db_session: AsyncSession
):
    """Checkout produces an audit record with action='checkout'."""
    resp = await _upload_file(async_client, admin_token)
    doc_id = resp.json()["data"]["id"]

    await _checkout(async_client, admin_token, doc_id)

    result = await db_session.execute(
        select(AuditLog).where(AuditLog.action == "checkout")
    )
    records = list(result.scalars().all())
    assert len(records) >= 1


@pytest.mark.asyncio
async def test_checkin_creates_audit_record(
    async_client: AsyncClient, admin_token: str, db_session: AsyncSession
):
    """Checkin produces an audit record with action='checkin'."""
    resp = await _upload_file(async_client, admin_token, content=b"audit-v1")
    doc_id = resp.json()["data"]["id"]

    await _checkout(async_client, admin_token, doc_id)
    await _checkin(async_client, admin_token, doc_id, content=b"audit-v2")

    result = await db_session.execute(
        select(AuditLog).where(AuditLog.action == "checkin")
    )
    records = list(result.scalars().all())
    assert len(records) >= 1
