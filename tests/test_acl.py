"""Integration tests for ACL (Access Control List) management (ACL-01 through ACL-04).

Covers:
  ACL-01: Documents have ACLs (CRUD, permission hierarchy, no-ACL fallback)
  ACL-02: Workflow activities modify ACLs via lifecycle rules
  ACL-03: ACL changes in audit trail
  ACL-04: Permission enforcement on API operations (403 on unauthorized access)
"""
import json
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.acl import DocumentACL, LifecycleACLRule
from app.models.audit import AuditLog
from app.models.enums import LifecycleState, PermissionLevel
from app.models.user import Group, User, user_groups
from app.models.workflow import ActivityTemplate


# ── Helpers ──────────────────────────────────────────────────────────────────


async def _upload_file(
    client: AsyncClient,
    token: str,
    title: str = "ACL Doc",
    content: bytes = b"acl test content",
):
    """Upload a document and return the response."""
    files = {"file": ("doc.pdf", content, "application/pdf")}
    data = {"title": title}
    return await client.post(
        "/api/v1/documents",
        files=files,
        data=data,
        headers={"Authorization": f"Bearer {token}"},
    )


async def _create_user2(db_session: AsyncSession) -> tuple[User, str]:
    """Create a second regular user and return (user, token)."""
    user = User(
        id=uuid.uuid4(),
        username="user2",
        hashed_password=hash_password("user2pass123"),
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    token = create_access_token({"sub": str(user.id), "username": user.username})
    return user, token


async def _transition(
    client: AsyncClient,
    token: str,
    doc_id: str,
    target_state: str,
):
    """Transition a document lifecycle state."""
    return await client.post(
        f"/api/v1/documents/{doc_id}/lifecycle/transition",
        json={"target_state": target_state},
        headers={"Authorization": f"Bearer {token}"},
    )


# ── ACL-01: Documents have ACLs ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_acl_entry(
    async_client: AsyncClient, admin_token: str, db_session: AsyncSession
):
    """ACL-01: Create an ACL entry for a document."""
    resp = await _upload_file(async_client, admin_token)
    doc_id = resp.json()["data"]["id"]

    user2, _ = await _create_user2(db_session)

    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await async_client.post(
        f"/api/v1/documents/{doc_id}/acl",
        json={
            "document_id": doc_id,
            "principal_id": str(user2.id),
            "principal_type": "user",
            "permission_level": "read",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["principal_id"] == str(user2.id)
    assert data["permission_level"] == "read"


@pytest.mark.asyncio
async def test_list_acl_entries(
    async_client: AsyncClient, admin_token: str
):
    """ACL-01: List ACL entries returns at least the creator's ADMIN entry."""
    resp = await _upload_file(async_client, admin_token)
    doc_id = resp.json()["data"]["id"]

    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await async_client.get(
        f"/api/v1/documents/{doc_id}/acl", headers=headers
    )
    assert resp.status_code == 200
    entries = resp.json()["data"]
    assert len(entries) >= 1
    # Creator should have ADMIN ACL
    admin_entries = [e for e in entries if e["permission_level"] == "admin"]
    assert len(admin_entries) >= 1


@pytest.mark.asyncio
async def test_delete_acl_entry(
    async_client: AsyncClient, admin_token: str, db_session: AsyncSession
):
    """ACL-01: Delete an ACL entry reduces the entry count."""
    resp = await _upload_file(async_client, admin_token)
    doc_id = resp.json()["data"]["id"]

    user2, _ = await _create_user2(db_session)

    headers = {"Authorization": f"Bearer {admin_token}"}
    # Add an ACL entry
    resp = await async_client.post(
        f"/api/v1/documents/{doc_id}/acl",
        json={
            "document_id": doc_id,
            "principal_id": str(user2.id),
            "principal_type": "user",
            "permission_level": "read",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    acl_id = resp.json()["data"]["id"]

    # List and count
    resp = await async_client.get(
        f"/api/v1/documents/{doc_id}/acl", headers=headers
    )
    initial_count = len(resp.json()["data"])

    # Delete
    resp = await async_client.delete(
        f"/api/v1/documents/{doc_id}/acl/{acl_id}", headers=headers
    )
    assert resp.status_code == 200

    # Verify count decreased
    resp = await async_client.get(
        f"/api/v1/documents/{doc_id}/acl", headers=headers
    )
    assert len(resp.json()["data"]) == initial_count - 1


@pytest.mark.asyncio
async def test_acl_permission_hierarchy(
    async_client: AsyncClient, admin_token: str, admin_user: User
):
    """ACL-01 (D-06): ADMIN permission grants access to READ, WRITE, and DELETE operations."""
    # Upload as admin (gets ADMIN ACL)
    resp = await _upload_file(async_client, admin_token)
    doc_id = resp.json()["data"]["id"]

    headers = {"Authorization": f"Bearer {admin_token}"}

    # GET (requires READ) should succeed
    resp = await async_client.get(
        f"/api/v1/documents/{doc_id}", headers=headers
    )
    assert resp.status_code == 200

    # PUT (requires WRITE) should succeed
    resp = await async_client.put(
        f"/api/v1/documents/{doc_id}",
        json={"title": "Updated"},
        headers=headers,
    )
    assert resp.status_code == 200

    # Checkout (requires WRITE) should succeed
    resp = await async_client.post(
        f"/api/v1/documents/{doc_id}/checkout", headers=headers
    )
    assert resp.status_code == 200

    # Checkin (requires WRITE) should succeed
    files = {"file": ("doc.pdf", b"updated content", "application/pdf")}
    resp = await async_client.post(
        f"/api/v1/documents/{doc_id}/checkin",
        files=files,
        headers=headers,
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_no_acl_entries_means_open_access(
    async_client: AsyncClient, admin_token: str, db_session: AsyncSession
):
    """ACL-01: Document with NO ACL entries is accessible by any authenticated user (backward compat)."""
    # Upload a document
    resp = await _upload_file(async_client, admin_token)
    doc_id = resp.json()["data"]["id"]

    # Delete all ACL entries for this document
    result = await db_session.execute(
        select(DocumentACL).where(
            DocumentACL.document_id == uuid.UUID(doc_id),
            DocumentACL.is_deleted == False,  # noqa: E712
        )
    )
    for entry in result.scalars().all():
        await db_session.delete(entry)
    await db_session.flush()

    # Create a second user
    user2, token2 = await _create_user2(db_session)

    # User2 should be able to access the document (open access)
    resp = await async_client.get(
        f"/api/v1/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert resp.status_code == 200


# ── ACL-02: Workflow activities modify ACLs via lifecycle ────────────────────


@pytest.mark.asyncio
async def test_workflow_acl_modification(
    async_client: AsyncClient,
    admin_token: str,
    admin_user: User,
    db_session: AsyncSession,
):
    """ACL-02: Workflow-triggered lifecycle transition applies ACL rules."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Seed ACL rule: REVIEW -> APPROVED removes WRITE for non_admin
    rule = LifecycleACLRule(
        from_state=LifecycleState.REVIEW.value,
        to_state=LifecycleState.APPROVED.value,
        action="remove",
        permission_level=PermissionLevel.WRITE.value,
        principal_filter="non_admin",
    )
    db_session.add(rule)
    await db_session.flush()

    # Create template with lifecycle_action="transition_to:approved"
    resp = await async_client.post(
        "/api/v1/templates/",
        json={"name": "ACL Workflow", "description": "Lifecycle ACL test"},
        headers=headers,
    )
    template_id = resp.json()["data"]["id"]

    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={"name": "Start", "activity_type": "start"},
        headers=headers,
    )
    start_id = resp.json()["data"]["id"]

    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={
            "name": "Approve Task",
            "activity_type": "manual",
            "performer_type": "user",
            "performer_id": str(admin_user.id),
        },
        headers=headers,
    )
    manual_id = resp.json()["data"]["id"]

    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={"name": "End", "activity_type": "end"},
        headers=headers,
    )
    end_id = resp.json()["data"]["id"]

    await async_client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={"source_activity_id": start_id, "target_activity_id": manual_id},
        headers=headers,
    )
    await async_client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={"source_activity_id": manual_id, "target_activity_id": end_id},
        headers=headers,
    )

    # Set lifecycle_action in DB
    result = await db_session.execute(
        select(ActivityTemplate).where(ActivityTemplate.id == uuid.UUID(manual_id))
    )
    activity = result.scalar_one()
    activity.lifecycle_action = "transition_to:approved"
    await db_session.flush()

    # Validate and install
    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/validate", headers=headers
    )
    assert resp.status_code == 200
    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/install", headers=headers
    )
    assert resp.status_code == 200

    # Upload document and add WRITE ACL for user2
    user2, _ = await _create_user2(db_session)

    resp = await _upload_file(async_client, admin_token)
    doc_id = resp.json()["data"]["id"]

    resp = await async_client.post(
        f"/api/v1/documents/{doc_id}/acl",
        json={
            "document_id": doc_id,
            "principal_id": str(user2.id),
            "principal_type": "user",
            "permission_level": "write",
        },
        headers=headers,
    )
    assert resp.status_code == 201

    # Transition document to REVIEW first (manually, as lifecycle_action triggers REVIEW->APPROVED)
    await _transition(async_client, admin_token, doc_id, "review")

    # Start workflow with document
    resp = await async_client.post(
        "/api/v1/workflows",
        json={
            "template_id": template_id,
            "document_ids": [doc_id],
        },
        headers=headers,
    )
    assert resp.status_code == 201
    wf_id = resp.json()["data"]["id"]

    # Complete the work item (triggers REVIEW -> APPROVED with lifecycle_action)
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}/work-items", headers=headers
    )
    available = [wi for wi in resp.json()["data"] if wi["state"] == "available"]
    assert len(available) == 1

    resp = await async_client.post(
        f"/api/v1/workflows/{wf_id}/work-items/{available[0]['id']}/complete",
        json={},
        headers=headers,
    )
    assert resp.status_code == 200

    # User2's WRITE ACL should be removed by the lifecycle rule
    result = await db_session.execute(
        select(DocumentACL).where(
            DocumentACL.document_id == uuid.UUID(doc_id),
            DocumentACL.principal_id == user2.id,
            DocumentACL.permission_level == PermissionLevel.WRITE.value,
            DocumentACL.is_deleted == False,  # noqa: E712
        )
    )
    assert result.scalar_one_or_none() is None, "WRITE ACL for user2 should be removed"


# ── ACL-03: ACL changes in audit trail ───────────────────────────────────────


@pytest.mark.asyncio
async def test_acl_grant_creates_audit_record(
    async_client: AsyncClient,
    admin_token: str,
    db_session: AsyncSession,
):
    """ACL-03: Adding an ACL entry creates an audit record with action=acl_granted."""
    resp = await _upload_file(async_client, admin_token)
    doc_id = resp.json()["data"]["id"]

    user2, _ = await _create_user2(db_session)

    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await async_client.post(
        f"/api/v1/documents/{doc_id}/acl",
        json={
            "document_id": doc_id,
            "principal_id": str(user2.id),
            "principal_type": "user",
            "permission_level": "read",
        },
        headers=headers,
    )
    assert resp.status_code == 201

    # Check audit record
    result = await db_session.execute(
        select(AuditLog).where(
            AuditLog.entity_type == "document_acl",
            AuditLog.entity_id == doc_id,
            AuditLog.action == "acl_granted",
        )
    )
    records = list(result.scalars().all())
    # At least 2: one for creator ADMIN, one for user2 READ
    assert len(records) >= 2


@pytest.mark.asyncio
async def test_acl_removal_creates_audit_record(
    async_client: AsyncClient,
    admin_token: str,
    db_session: AsyncSession,
):
    """ACL-03: Removing an ACL entry creates an audit record with action=acl_revoked."""
    resp = await _upload_file(async_client, admin_token)
    doc_id = resp.json()["data"]["id"]

    user2, _ = await _create_user2(db_session)

    headers = {"Authorization": f"Bearer {admin_token}"}
    # Add ACL
    resp = await async_client.post(
        f"/api/v1/documents/{doc_id}/acl",
        json={
            "document_id": doc_id,
            "principal_id": str(user2.id),
            "principal_type": "user",
            "permission_level": "read",
        },
        headers=headers,
    )
    acl_id = resp.json()["data"]["id"]

    # Delete ACL
    resp = await async_client.delete(
        f"/api/v1/documents/{doc_id}/acl/{acl_id}", headers=headers
    )
    assert resp.status_code == 200

    # Check audit record for revocation
    result = await db_session.execute(
        select(AuditLog).where(
            AuditLog.entity_type == "document_acl",
            AuditLog.entity_id == doc_id,
            AuditLog.action == "acl_revoked",
        )
    )
    records = list(result.scalars().all())
    assert len(records) >= 1


# ── ACL-04: Permission enforcement on API operations ────────────────────────


@pytest.mark.asyncio
async def test_get_document_requires_read_permission(
    async_client: AsyncClient, admin_token: str, db_session: AsyncSession
):
    """ACL-04: GET /documents/{id} returns 403 for user without ACL entry."""
    # Upload as admin (creates ADMIN ACL for admin)
    resp = await _upload_file(async_client, admin_token)
    doc_id = resp.json()["data"]["id"]

    # User2 has no ACL entry but entries exist on the document (enforcement active)
    user2, token2 = await _create_user2(db_session)

    resp = await async_client.get(
        f"/api/v1/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_document_requires_write_permission(
    async_client: AsyncClient, admin_token: str, db_session: AsyncSession
):
    """ACL-04: PUT /documents/{id} returns 403 when user only has READ permission."""
    resp = await _upload_file(async_client, admin_token)
    doc_id = resp.json()["data"]["id"]

    user2, token2 = await _create_user2(db_session)

    # Grant READ only to user2
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await async_client.post(
        f"/api/v1/documents/{doc_id}/acl",
        json={
            "document_id": doc_id,
            "principal_id": str(user2.id),
            "principal_type": "user",
            "permission_level": "read",
        },
        headers=headers,
    )
    assert resp.status_code == 201

    # User2 tries to update (requires WRITE) -> 403
    resp = await async_client.put(
        f"/api/v1/documents/{doc_id}",
        json={"title": "Hacked"},
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_checkout_requires_write_permission(
    async_client: AsyncClient, admin_token: str, db_session: AsyncSession
):
    """ACL-04: POST /documents/{id}/checkout returns 403 when user only has READ."""
    resp = await _upload_file(async_client, admin_token)
    doc_id = resp.json()["data"]["id"]

    user2, token2 = await _create_user2(db_session)

    # Grant READ only
    headers = {"Authorization": f"Bearer {admin_token}"}
    await async_client.post(
        f"/api/v1/documents/{doc_id}/acl",
        json={
            "document_id": doc_id,
            "principal_id": str(user2.id),
            "principal_type": "user",
            "permission_level": "read",
        },
        headers=headers,
    )

    resp = await async_client.post(
        f"/api/v1/documents/{doc_id}/checkout",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_upload_does_not_require_permission(
    async_client: AsyncClient, db_session: AsyncSession
):
    """ACL-04: Any authenticated user can upload (no document_id to check against)."""
    user2, token2 = await _create_user2(db_session)

    resp = await _upload_file(async_client, token2, title="User2 Upload")
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_list_documents_no_permission_check(
    async_client: AsyncClient, admin_token: str, db_session: AsyncSession
):
    """ACL-04: GET /documents/ returns 200 for any authenticated user (no per-document ACL)."""
    user2, token2 = await _create_user2(db_session)

    resp = await async_client.get(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_admin_permission_grants_all_access(
    async_client: AsyncClient, admin_token: str
):
    """ACL-04: User with ADMIN ACL can perform all operations."""
    resp = await _upload_file(async_client, admin_token)
    doc_id = resp.json()["data"]["id"]

    headers = {"Authorization": f"Bearer {admin_token}"}

    # GET
    resp = await async_client.get(f"/api/v1/documents/{doc_id}", headers=headers)
    assert resp.status_code == 200

    # PUT
    resp = await async_client.put(
        f"/api/v1/documents/{doc_id}",
        json={"title": "Admin Update"},
        headers=headers,
    )
    assert resp.status_code == 200

    # Checkout
    resp = await async_client.post(
        f"/api/v1/documents/{doc_id}/checkout", headers=headers
    )
    assert resp.status_code == 200

    # Checkin
    files = {"file": ("doc.pdf", b"new content", "application/pdf")}
    resp = await async_client.post(
        f"/api/v1/documents/{doc_id}/checkin", files=files, headers=headers
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_group_based_permission(
    async_client: AsyncClient,
    admin_token: str,
    admin_user: User,
    db_session: AsyncSession,
):
    """ACL-04: Group-based ACL grants access to group members."""
    # Create a group and add user2 to it
    group = Group(
        id=uuid.uuid4(),
        name="reviewers",
        description="Document reviewers",
    )
    db_session.add(group)
    await db_session.flush()

    user2, token2 = await _create_user2(db_session)

    # Add user2 to the group
    await db_session.execute(
        user_groups.insert().values(user_id=user2.id, group_id=group.id)
    )
    await db_session.flush()

    # Upload document as admin
    resp = await _upload_file(async_client, admin_token)
    doc_id = resp.json()["data"]["id"]

    # Add READ ACL with principal_type="group" for the group
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await async_client.post(
        f"/api/v1/documents/{doc_id}/acl",
        json={
            "document_id": doc_id,
            "principal_id": str(group.id),
            "principal_type": "group",
            "permission_level": "read",
        },
        headers=headers,
    )
    assert resp.status_code == 201

    # User2 should be able to read the document via group membership
    resp = await async_client.get(
        f"/api/v1/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert resp.status_code == 200
