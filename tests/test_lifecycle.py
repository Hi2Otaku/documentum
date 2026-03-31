"""Integration tests for document lifecycle management (LIFE-01 through LIFE-04).

Covers:
  LIFE-01: Valid and invalid lifecycle state transitions
  LIFE-02: Workflow-triggered lifecycle transitions on package documents
  LIFE-03: Audit trail for lifecycle changes
  LIFE-04: ACL changes on lifecycle state transitions
"""
import json
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.acl import DocumentACL, LifecycleACLRule
from app.models.audit import AuditLog
from app.models.enums import LifecycleState, PermissionLevel
from app.models.user import User
from app.models.workflow import ActivityTemplate


# ── Helpers ──────────────────────────────────────────────────────────────────


async def _upload_file(
    client: AsyncClient,
    token: str,
    title: str = "Lifecycle Doc",
    filename: str = "doc.pdf",
    content: bytes = b"lifecycle test content",
):
    """Upload a document and return the response."""
    files = {"file": (filename, content, "application/pdf")}
    data = {"title": title}
    return await client.post(
        "/api/v1/documents",
        files=files,
        data=data,
        headers={"Authorization": f"Bearer {token}"},
    )


async def _transition(
    client: AsyncClient,
    token: str,
    doc_id: str,
    target_state: str,
):
    """Transition a document lifecycle state and return the response."""
    return await client.post(
        f"/api/v1/documents/{doc_id}/lifecycle/transition",
        json={"target_state": target_state},
        headers={"Authorization": f"Bearer {token}"},
    )


async def _get_lifecycle(client: AsyncClient, token: str, doc_id: str):
    """Get the current lifecycle state of a document."""
    return await client.get(
        f"/api/v1/documents/{doc_id}/lifecycle",
        headers={"Authorization": f"Bearer {token}"},
    )


async def _create_workflow_with_lifecycle_action(
    client: AsyncClient,
    token: str,
    admin_user: User,
    db: AsyncSession,
    lifecycle_action: str,
) -> dict:
    """Create an installed template with a manual activity that has a lifecycle_action.

    Returns dict with template_id, manual_activity_id.
    Since lifecycle_action is not in the API schema, we set it directly in the DB.
    """
    headers = {"Authorization": f"Bearer {token}"}

    # Create template
    resp = await client.post(
        "/api/v1/templates/",
        json={"name": "Lifecycle Workflow", "description": "With lifecycle action"},
        headers=headers,
    )
    assert resp.status_code == 201
    template_id = resp.json()["data"]["id"]

    # Start activity
    resp = await client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={"name": "Start", "activity_type": "start"},
        headers=headers,
    )
    start_id = resp.json()["data"]["id"]

    # Manual activity (lifecycle_action set later via DB)
    resp = await client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={
            "name": "Review Task",
            "activity_type": "manual",
            "performer_type": "user",
            "performer_id": str(admin_user.id),
        },
        headers=headers,
    )
    manual_id = resp.json()["data"]["id"]

    # End activity
    resp = await client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={"name": "End", "activity_type": "end"},
        headers=headers,
    )
    end_id = resp.json()["data"]["id"]

    # Flows: start -> manual -> end
    await client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={"source_activity_id": start_id, "target_activity_id": manual_id},
        headers=headers,
    )
    await client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={"source_activity_id": manual_id, "target_activity_id": end_id},
        headers=headers,
    )

    # Set lifecycle_action directly in DB (not exposed in API schema)
    result = await db.execute(
        select(ActivityTemplate).where(ActivityTemplate.id == uuid.UUID(manual_id))
    )
    activity = result.scalar_one()
    activity.lifecycle_action = lifecycle_action
    await db.flush()

    # Validate and install
    resp = await client.post(
        f"/api/v1/templates/{template_id}/validate", headers=headers
    )
    assert resp.status_code == 200, f"Validate failed: {resp.json()}"
    resp = await client.post(
        f"/api/v1/templates/{template_id}/install", headers=headers
    )
    assert resp.status_code == 200, f"Install failed: {resp.json()}"

    return {"template_id": template_id, "manual_id": manual_id}


# ── LIFE-01: Valid lifecycle transitions ─────────────────────────────────────


@pytest.mark.asyncio
async def test_transition_draft_to_review(
    async_client: AsyncClient, admin_token: str
):
    """LIFE-01: Document transitions from DRAFT to REVIEW."""
    resp = await _upload_file(async_client, admin_token)
    assert resp.status_code == 201
    doc_id = resp.json()["data"]["id"]

    resp = await _transition(async_client, admin_token, doc_id, "review")
    assert resp.status_code == 200
    assert resp.json()["data"]["lifecycle_state"] == "review"


@pytest.mark.asyncio
async def test_transition_review_to_approved(
    async_client: AsyncClient, admin_token: str
):
    """LIFE-01: Document transitions from REVIEW to APPROVED."""
    resp = await _upload_file(async_client, admin_token)
    doc_id = resp.json()["data"]["id"]

    await _transition(async_client, admin_token, doc_id, "review")
    resp = await _transition(async_client, admin_token, doc_id, "approved")
    assert resp.status_code == 200
    assert resp.json()["data"]["lifecycle_state"] == "approved"


@pytest.mark.asyncio
async def test_transition_approved_to_archived(
    async_client: AsyncClient, admin_token: str
):
    """LIFE-01: Full chain DRAFT -> REVIEW -> APPROVED -> ARCHIVED."""
    resp = await _upload_file(async_client, admin_token)
    doc_id = resp.json()["data"]["id"]

    await _transition(async_client, admin_token, doc_id, "review")
    await _transition(async_client, admin_token, doc_id, "approved")
    resp = await _transition(async_client, admin_token, doc_id, "archived")
    assert resp.status_code == 200
    assert resp.json()["data"]["lifecycle_state"] == "archived"


@pytest.mark.asyncio
async def test_transition_review_to_draft_reject(
    async_client: AsyncClient, admin_token: str
):
    """LIFE-01: Reject back from REVIEW to DRAFT is a valid transition (D-02)."""
    resp = await _upload_file(async_client, admin_token)
    doc_id = resp.json()["data"]["id"]

    await _transition(async_client, admin_token, doc_id, "review")
    resp = await _transition(async_client, admin_token, doc_id, "draft")
    assert resp.status_code == 200
    assert resp.json()["data"]["lifecycle_state"] == "draft"


@pytest.mark.asyncio
async def test_invalid_transition_draft_to_approved(
    async_client: AsyncClient, admin_token: str
):
    """LIFE-01: Skipping REVIEW (DRAFT -> APPROVED) returns 400."""
    resp = await _upload_file(async_client, admin_token)
    doc_id = resp.json()["data"]["id"]

    resp = await _transition(async_client, admin_token, doc_id, "approved")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_invalid_transition_archived_to_draft(
    async_client: AsyncClient, admin_token: str
):
    """LIFE-01: ARCHIVED -> DRAFT is invalid, returns 400."""
    resp = await _upload_file(async_client, admin_token)
    doc_id = resp.json()["data"]["id"]

    await _transition(async_client, admin_token, doc_id, "review")
    await _transition(async_client, admin_token, doc_id, "approved")
    await _transition(async_client, admin_token, doc_id, "archived")

    resp = await _transition(async_client, admin_token, doc_id, "draft")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_invalid_transition_draft_to_archived(
    async_client: AsyncClient, admin_token: str
):
    """LIFE-01: DRAFT -> ARCHIVED directly is invalid, returns 400."""
    resp = await _upload_file(async_client, admin_token)
    doc_id = resp.json()["data"]["id"]

    resp = await _transition(async_client, admin_token, doc_id, "archived")
    assert resp.status_code == 400


# ── LIFE-02: Workflow-triggered lifecycle transition ─────────────────────────


@pytest.mark.asyncio
async def test_workflow_triggered_transition(
    async_client: AsyncClient,
    admin_token: str,
    admin_user: User,
    db_session: AsyncSession,
):
    """LIFE-02: Completing a workflow activity with lifecycle_action transitions package documents."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Create template with lifecycle_action="transition_to:review"
    tmpl = await _create_workflow_with_lifecycle_action(
        async_client, admin_token, admin_user, db_session, "transition_to:review"
    )

    # Upload a document
    resp = await _upload_file(async_client, admin_token)
    assert resp.status_code == 201
    doc_id = resp.json()["data"]["id"]

    # Start workflow with document in package
    resp = await async_client.post(
        "/api/v1/workflows",
        json={
            "template_id": tmpl["template_id"],
            "document_ids": [doc_id],
        },
        headers=headers,
    )
    assert resp.status_code == 201
    wf_id = resp.json()["data"]["id"]

    # Find and complete the manual activity work item
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

    # Check document lifecycle state is now "review"
    resp = await _get_lifecycle(async_client, admin_token, doc_id)
    assert resp.status_code == 200
    assert resp.json()["data"]["lifecycle_state"] == "review"


@pytest.mark.asyncio
async def test_workflow_lifecycle_action_affects_all_package_documents(
    async_client: AsyncClient,
    admin_token: str,
    admin_user: User,
    db_session: AsyncSession,
):
    """LIFE-02 (D-10): Lifecycle action transitions ALL documents in workflow package."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    tmpl = await _create_workflow_with_lifecycle_action(
        async_client, admin_token, admin_user, db_session, "transition_to:review"
    )

    # Upload TWO documents
    resp1 = await _upload_file(async_client, admin_token, title="Doc One")
    doc1_id = resp1.json()["data"]["id"]
    resp2 = await _upload_file(async_client, admin_token, title="Doc Two")
    doc2_id = resp2.json()["data"]["id"]

    # Start workflow with both documents
    resp = await async_client.post(
        "/api/v1/workflows",
        json={
            "template_id": tmpl["template_id"],
            "document_ids": [doc1_id, doc2_id],
        },
        headers=headers,
    )
    assert resp.status_code == 201
    wf_id = resp.json()["data"]["id"]

    # Complete the work item
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

    # Both documents should now be in "review" state
    resp1 = await _get_lifecycle(async_client, admin_token, doc1_id)
    assert resp1.json()["data"]["lifecycle_state"] == "review"

    resp2 = await _get_lifecycle(async_client, admin_token, doc2_id)
    assert resp2.json()["data"]["lifecycle_state"] == "review"


@pytest.mark.asyncio
async def test_workflow_lifecycle_action_failure_does_not_halt(
    async_client: AsyncClient,
    admin_token: str,
    admin_user: User,
    db_session: AsyncSession,
):
    """LIFE-02 (D-04): Invalid lifecycle action does not halt the workflow."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Create template with lifecycle_action="transition_to:approved" (invalid from DRAFT)
    tmpl = await _create_workflow_with_lifecycle_action(
        async_client, admin_token, admin_user, db_session, "transition_to:approved"
    )

    # Upload a document (starts in DRAFT)
    resp = await _upload_file(async_client, admin_token)
    doc_id = resp.json()["data"]["id"]

    # Start workflow with document
    resp = await async_client.post(
        "/api/v1/workflows",
        json={
            "template_id": tmpl["template_id"],
            "document_ids": [doc_id],
        },
        headers=headers,
    )
    assert resp.status_code == 201
    wf_id = resp.json()["data"]["id"]

    # Complete the work item (lifecycle action will fail but workflow should continue)
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

    # Workflow should have finished (not stuck)
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}", headers=headers
    )
    assert resp.json()["data"]["state"] == "finished"

    # Document should still be in DRAFT (transition failed)
    resp = await _get_lifecycle(async_client, admin_token, doc_id)
    assert resp.json()["data"]["lifecycle_state"] == "draft"


# ── LIFE-03: Audit trail for lifecycle changes ───────────────────────────────


@pytest.mark.asyncio
async def test_lifecycle_transition_creates_audit_record(
    async_client: AsyncClient,
    admin_token: str,
    db_session: AsyncSession,
):
    """LIFE-03: Successful lifecycle transition creates an audit record."""
    resp = await _upload_file(async_client, admin_token)
    doc_id = resp.json()["data"]["id"]

    await _transition(async_client, admin_token, doc_id, "review")

    # Query audit records
    result = await db_session.execute(
        select(AuditLog).where(
            AuditLog.entity_type == "document",
            AuditLog.entity_id == doc_id,
            AuditLog.action == "lifecycle_transition",
        )
    )
    records = list(result.scalars().all())
    assert len(records) >= 1
    record = records[0]
    assert record.before_state["lifecycle_state"] == "draft"
    assert record.after_state["lifecycle_state"] == "review"


@pytest.mark.asyncio
async def test_failed_transition_creates_audit_record(
    async_client: AsyncClient,
    admin_token: str,
    db_session: AsyncSession,
):
    """LIFE-03: Failed lifecycle transition creates a lifecycle_transition_failed audit record."""
    resp = await _upload_file(async_client, admin_token)
    doc_id = resp.json()["data"]["id"]

    # Attempt invalid transition
    resp = await _transition(async_client, admin_token, doc_id, "approved")
    assert resp.status_code == 400

    # Query audit records
    result = await db_session.execute(
        select(AuditLog).where(
            AuditLog.entity_type == "document",
            AuditLog.entity_id == doc_id,
            AuditLog.action == "lifecycle_transition_failed",
        )
    )
    records = list(result.scalars().all())
    assert len(records) >= 1


# ── LIFE-04: ACL changes on lifecycle transition ─────────────────────────────


@pytest.mark.asyncio
async def test_acl_changes_on_approval(
    async_client: AsyncClient,
    admin_token: str,
    admin_user: User,
    regular_user: User,
    db_session: AsyncSession,
):
    """LIFE-04: ACL rules applied on lifecycle transition remove WRITE for non-admin."""
    # Seed a lifecycle ACL rule: REVIEW -> APPROVED removes WRITE for non_admin
    rule = LifecycleACLRule(
        from_state=LifecycleState.REVIEW.value,
        to_state=LifecycleState.APPROVED.value,
        action="remove",
        permission_level=PermissionLevel.WRITE.value,
        principal_filter="non_admin",
    )
    db_session.add(rule)
    await db_session.flush()

    # Upload document
    resp = await _upload_file(async_client, admin_token)
    doc_id = resp.json()["data"]["id"]

    # Add WRITE ACL for the regular user
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await async_client.post(
        f"/api/v1/documents/{doc_id}/acl",
        json={
            "document_id": doc_id,
            "principal_id": str(regular_user.id),
            "principal_type": "user",
            "permission_level": "write",
        },
        headers=headers,
    )
    assert resp.status_code == 201

    # Verify WRITE ACL exists
    result = await db_session.execute(
        select(DocumentACL).where(
            DocumentACL.document_id == uuid.UUID(doc_id),
            DocumentACL.principal_id == regular_user.id,
            DocumentACL.permission_level == PermissionLevel.WRITE.value,
            DocumentACL.is_deleted == False,  # noqa: E712
        )
    )
    assert result.scalar_one_or_none() is not None

    # Transition DRAFT -> REVIEW -> APPROVED
    await _transition(async_client, admin_token, doc_id, "review")
    resp = await _transition(async_client, admin_token, doc_id, "approved")
    assert resp.status_code == 200

    # The regular user's WRITE ACL should have been removed
    result = await db_session.execute(
        select(DocumentACL).where(
            DocumentACL.document_id == uuid.UUID(doc_id),
            DocumentACL.principal_id == regular_user.id,
            DocumentACL.permission_level == PermissionLevel.WRITE.value,
            DocumentACL.is_deleted == False,  # noqa: E712
        )
    )
    assert result.scalar_one_or_none() is None, "WRITE ACL for regular user should be removed"

    # Admin ACL should still exist
    result = await db_session.execute(
        select(DocumentACL).where(
            DocumentACL.document_id == uuid.UUID(doc_id),
            DocumentACL.principal_id == admin_user.id,
            DocumentACL.permission_level == PermissionLevel.ADMIN.value,
            DocumentACL.is_deleted == False,  # noqa: E712
        )
    )
    assert result.scalar_one_or_none() is not None, "ADMIN ACL for creator should remain"

    # Verify acl_rule_applied audit record exists
    result = await db_session.execute(
        select(AuditLog).where(
            AuditLog.entity_type == "document_acl",
            AuditLog.entity_id == doc_id,
            AuditLog.action == "acl_rule_applied",
        )
    )
    records = list(result.scalars().all())
    assert len(records) >= 1
