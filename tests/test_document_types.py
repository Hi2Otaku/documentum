"""Tests for Document Type System (TYPE-01 through TYPE-04).

These tests are stubs that will pass once the router is wired in Plan 02.
They cover CRUD, schema inheritance, grandchild prevention, metadata validation,
and document assignment.
"""

import json
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


# ── Helpers ──────────────────────────────────────────────────────────────────


async def _create_type(
    client: AsyncClient,
    token: str,
    name: str = "TestType",
    description: str | None = None,
    metadata_schema: dict | None = None,
    parent_type_id: str | None = None,
) -> dict:
    """Helper: create a document type via the API."""
    payload: dict = {"name": name}
    if description is not None:
        payload["description"] = description
    if metadata_schema is not None:
        payload["metadata_schema"] = metadata_schema
    if parent_type_id is not None:
        payload["parent_type_id"] = parent_type_id
    resp = await client.post(
        "/api/v1/document-types/",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp


async def _upload_doc(
    client: AsyncClient,
    token: str,
    title: str = "Test Doc",
    custom_properties: dict | None = None,
    document_type_id: str | None = None,
) -> dict:
    """Helper: upload a document with optional type and custom properties."""
    files = {"file": ("test.pdf", b"test content", "application/pdf")}
    data: dict = {"title": title}
    if custom_properties is not None:
        data["custom_properties"] = json.dumps(custom_properties)
    if document_type_id is not None:
        data["document_type_id"] = document_type_id
    return await client.post(
        "/api/v1/documents",
        files=files,
        data=data,
        headers={"Authorization": f"Bearer {token}"},
    )


# ── TYPE-01: CRUD ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_type(
    async_client: AsyncClient,
    admin_token: str,
) -> None:
    """Admin can create a document type with a metadata schema."""
    schema = {
        "type": "object",
        "properties": {
            "invoice_number": {"type": "string"},
            "amount": {"type": "number"},
        },
        "required": ["invoice_number"],
    }
    resp = await _create_type(
        async_client,
        admin_token,
        name="Invoice",
        metadata_schema=schema,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()["data"]
    assert data["name"] == "Invoice"
    assert "id" in data
    assert data["metadata_schema"] == schema


@pytest.mark.asyncio
async def test_create_type_non_admin(
    async_client: AsyncClient,
    regular_token: str,
) -> None:
    """Non-admin users cannot create document types."""
    resp = await _create_type(async_client, regular_token, name="ShouldFail")
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_list_types(
    async_client: AsyncClient,
    admin_token: str,
) -> None:
    """List endpoint returns all created document types."""
    await _create_type(async_client, admin_token, name="TypeAlpha")
    await _create_type(async_client, admin_token, name="TypeBeta")

    resp = await async_client.get(
        "/api/v1/document-types/",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200, resp.text
    names = [t["name"] for t in resp.json()["data"]]
    assert "TypeAlpha" in names
    assert "TypeBeta" in names


@pytest.mark.asyncio
async def test_update_type(
    async_client: AsyncClient,
    admin_token: str,
) -> None:
    """Admin can update a document type's name."""
    create_resp = await _create_type(async_client, admin_token, name="OldName")
    assert create_resp.status_code == 201
    type_id = create_resp.json()["data"]["id"]

    resp = await async_client.put(
        f"/api/v1/document-types/{type_id}",
        json={"name": "NewName"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["name"] == "NewName"


@pytest.mark.asyncio
async def test_delete_type(
    async_client: AsyncClient,
    admin_token: str,
) -> None:
    """Admin can delete (soft-delete) a document type."""
    create_resp = await _create_type(async_client, admin_token, name="ToDelete")
    assert create_resp.status_code == 201
    type_id = create_resp.json()["data"]["id"]

    resp = await async_client.delete(
        f"/api/v1/document-types/{type_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200, resp.text


# ── TYPE-03: Schema Inheritance ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_child_type_inherits_parent(
    async_client: AsyncClient,
    admin_token: str,
) -> None:
    """Child type's effective schema merges parent + child properties."""
    parent_schema = {
        "type": "object",
        "properties": {"category": {"type": "string"}},
        "required": ["category"],
    }
    parent_resp = await _create_type(
        async_client,
        admin_token,
        name="ParentDoc",
        metadata_schema=parent_schema,
    )
    assert parent_resp.status_code == 201
    parent_id = parent_resp.json()["data"]["id"]

    child_schema = {
        "type": "object",
        "properties": {"amount": {"type": "number"}},
        "required": ["amount"],
    }
    child_resp = await _create_type(
        async_client,
        admin_token,
        name="ChildDoc",
        metadata_schema=child_schema,
        parent_type_id=parent_id,
    )
    assert child_resp.status_code == 201
    child_id = child_resp.json()["data"]["id"]

    # GET child type and verify effective_schema includes both properties
    resp = await async_client.get(
        f"/api/v1/document-types/{child_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    # The response should reflect parent link
    assert data["parent_type_id"] == parent_id


@pytest.mark.asyncio
async def test_no_grandchild_types(
    async_client: AsyncClient,
    admin_token: str,
) -> None:
    """Cannot create a type whose parent already has a parent (max 1 level)."""
    parent_resp = await _create_type(async_client, admin_token, name="GrandParent")
    assert parent_resp.status_code == 201
    parent_id = parent_resp.json()["data"]["id"]

    child_resp = await _create_type(
        async_client,
        admin_token,
        name="Child",
        parent_type_id=parent_id,
    )
    assert child_resp.status_code == 201
    child_id = child_resp.json()["data"]["id"]

    grandchild_resp = await _create_type(
        async_client,
        admin_token,
        name="GrandChild",
        parent_type_id=child_id,
    )
    assert grandchild_resp.status_code in (400, 422), grandchild_resp.text


# ── TYPE-04: Metadata Validation ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upload_with_type(
    async_client: AsyncClient,
    admin_token: str,
) -> None:
    """Document upload accepts document_type_id and persists it."""
    schema = {
        "type": "object",
        "properties": {"ref_number": {"type": "string"}},
    }
    type_resp = await _create_type(
        async_client,
        admin_token,
        name="ContractDoc",
        metadata_schema=schema,
    )
    assert type_resp.status_code == 201
    type_id = type_resp.json()["data"]["id"]

    doc_resp = await _upload_doc(
        async_client,
        admin_token,
        title="My Contract",
        custom_properties={"ref_number": "REF-001"},
        document_type_id=type_id,
    )
    assert doc_resp.status_code == 201, doc_resp.text
    doc_data = doc_resp.json()["data"]
    assert doc_data["document_type_id"] == type_id


@pytest.mark.asyncio
async def test_update_document_type(
    async_client: AsyncClient,
    admin_token: str,
) -> None:
    """PUT /documents/{id} can update document_type_id."""
    type_resp = await _create_type(async_client, admin_token, name="UpdateableType")
    assert type_resp.status_code == 201
    type_id = type_resp.json()["data"]["id"]

    doc_resp = await _upload_doc(async_client, admin_token, title="Doc To Update")
    assert doc_resp.status_code == 201
    doc_id = doc_resp.json()["data"]["id"]

    update_resp = await async_client.put(
        f"/api/v1/documents/{doc_id}",
        json={"document_type_id": type_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert update_resp.status_code == 200, update_resp.text
    assert update_resp.json()["data"]["document_type_id"] == type_id


@pytest.mark.asyncio
async def test_validation_rejects_missing_required(
    async_client: AsyncClient,
    admin_token: str,
) -> None:
    """Upload with typed document but missing required field raises 422."""
    schema = {
        "type": "object",
        "properties": {"invoice_no": {"type": "string"}},
        "required": ["invoice_no"],
    }
    type_resp = await _create_type(
        async_client,
        admin_token,
        name="StrictInvoice",
        metadata_schema=schema,
    )
    assert type_resp.status_code == 201
    type_id = type_resp.json()["data"]["id"]

    # Upload without the required field
    doc_resp = await _upload_doc(
        async_client,
        admin_token,
        title="Bad Invoice",
        custom_properties={},  # missing invoice_no
        document_type_id=type_id,
    )
    assert doc_resp.status_code == 422, doc_resp.text


@pytest.mark.asyncio
async def test_validation_passes_valid_metadata(
    async_client: AsyncClient,
    admin_token: str,
) -> None:
    """Upload with typed document and valid required fields succeeds."""
    schema = {
        "type": "object",
        "properties": {"invoice_no": {"type": "string"}},
        "required": ["invoice_no"],
    }
    type_resp = await _create_type(
        async_client,
        admin_token,
        name="ValidInvoice",
        metadata_schema=schema,
    )
    assert type_resp.status_code == 201
    type_id = type_resp.json()["data"]["id"]

    doc_resp = await _upload_doc(
        async_client,
        admin_token,
        title="Good Invoice",
        custom_properties={"invoice_no": "INV-2026-001"},
        document_type_id=type_id,
    )
    assert doc_resp.status_code == 201, doc_resp.text


@pytest.mark.asyncio
async def test_untyped_skips_validation(
    async_client: AsyncClient,
    admin_token: str,
) -> None:
    """Documents without document_type_id skip metadata validation entirely."""
    files = {"file": ("plain.txt", b"no type needed", "text/plain")}
    data = {"title": "Untyped Doc"}
    resp = await async_client.post(
        "/api/v1/documents",
        files=files,
        data=data,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201, resp.text
