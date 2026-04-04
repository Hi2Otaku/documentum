"""Integration tests for admin query interface (QUERY-01, QUERY-02, QUERY-03)."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.enums import (
    ActivityState,
    ActivityType,
    LifecycleState,
    ProcessState,
    WorkflowState,
    WorkItemState,
)
from app.models.workflow import (
    ActivityInstance,
    ActivityTemplate,
    ProcessTemplate,
    WorkflowInstance,
    WorkItem,
)

pytestmark = pytest.mark.asyncio


# ---- Helpers ----

async def _create_template(db: AsyncSession, name: str = "Template A") -> ProcessTemplate:
    """Create a minimal process template with one activity template."""
    tmpl = ProcessTemplate(
        id=uuid.uuid4(),
        name=name,
        version=1,
        state=ProcessState.ACTIVE,
        is_installed=True,
    )
    db.add(tmpl)
    await db.flush()

    act = ActivityTemplate(
        id=uuid.uuid4(),
        process_template_id=tmpl.id,
        name="Start",
        activity_type=ActivityType.START,
    )
    db.add(act)
    await db.flush()
    return tmpl


async def _create_workflow(
    db: AsyncSession,
    template: ProcessTemplate,
    state: WorkflowState = WorkflowState.RUNNING,
    supervisor_id: uuid.UUID | None = None,
    created_at: datetime | None = None,
) -> WorkflowInstance:
    """Create a workflow instance tied to a template."""
    wf = WorkflowInstance(
        id=uuid.uuid4(),
        process_template_id=template.id,
        state=state,
        supervisor_id=supervisor_id,
        started_at=created_at or datetime.now(timezone.utc),
    )
    if created_at:
        wf.created_at = created_at
    db.add(wf)
    await db.flush()
    return wf


async def _create_activity_instance(
    db: AsyncSession,
    workflow: WorkflowInstance,
    template: ProcessTemplate,
    state: ActivityState = ActivityState.ACTIVE,
) -> ActivityInstance:
    """Create an activity instance for a workflow."""
    # Get the first activity template from the process template
    act_tmpl = ActivityTemplate(
        id=uuid.uuid4(),
        process_template_id=template.id,
        name="Review",
        activity_type=ActivityType.MANUAL,
    )
    db.add(act_tmpl)
    await db.flush()

    ai = ActivityInstance(
        id=uuid.uuid4(),
        workflow_instance_id=workflow.id,
        activity_template_id=act_tmpl.id,
        state=state,
    )
    db.add(ai)
    await db.flush()
    return ai


async def _create_work_item(
    db: AsyncSession,
    activity_instance: ActivityInstance,
    performer_id: uuid.UUID | None = None,
    state: WorkItemState = WorkItemState.AVAILABLE,
    priority: int = 5,
) -> WorkItem:
    """Create a work item for an activity instance."""
    wi = WorkItem(
        id=uuid.uuid4(),
        activity_instance_id=activity_instance.id,
        performer_id=performer_id,
        state=state,
        priority=priority,
    )
    db.add(wi)
    await db.flush()
    return wi


async def _create_document(
    db: AsyncSession,
    title: str = "Doc A",
    lifecycle_state: LifecycleState = LifecycleState.DRAFT,
    custom_properties: dict | None = None,
    major: int = 0,
    minor: int = 1,
) -> Document:
    """Create a document with metadata."""
    doc = Document(
        id=uuid.uuid4(),
        title=title,
        filename=f"{title.lower().replace(' ', '_')}.pdf",
        content_type="application/pdf",
        lifecycle_state=lifecycle_state,
        custom_properties=custom_properties or {},
        current_major_version=major,
        current_minor_version=minor,
    )
    db.add(doc)
    await db.flush()
    return doc


# ---- QUERY-01: Workflow queries ----


async def test_query_workflows_no_filter(
    async_client: AsyncClient, admin_token: str, db_session: AsyncSession
):
    """QUERY-01: Query all workflows without filters returns all items."""
    tmpl = await _create_template(db_session, "WF Template")
    await _create_workflow(db_session, tmpl)
    await _create_workflow(db_session, tmpl, state=WorkflowState.FINISHED)
    await db_session.commit()

    resp = await async_client.get(
        "/api/v1/query/workflows",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) == 2
    assert body["meta"]["total_count"] == 2


async def test_query_workflows_by_state(
    async_client: AsyncClient, admin_token: str, db_session: AsyncSession
):
    """QUERY-01: Filter workflows by state returns only matching."""
    tmpl = await _create_template(db_session)
    await _create_workflow(db_session, tmpl, state=WorkflowState.RUNNING)
    await _create_workflow(db_session, tmpl, state=WorkflowState.FINISHED)
    await _create_workflow(db_session, tmpl, state=WorkflowState.RUNNING)
    await db_session.commit()

    resp = await async_client.get(
        "/api/v1/query/workflows?state=running",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["meta"]["total_count"] == 2
    for item in body["data"]:
        assert item["state"] == "running"


async def test_query_workflows_by_template(
    async_client: AsyncClient, admin_token: str, db_session: AsyncSession
):
    """QUERY-01: Filter by template_id returns only that template's workflows."""
    tmpl_a = await _create_template(db_session, "Template A")
    tmpl_b = await _create_template(db_session, "Template B")
    await _create_workflow(db_session, tmpl_a)
    await _create_workflow(db_session, tmpl_b)
    await _create_workflow(db_session, tmpl_a)
    await db_session.commit()

    resp = await async_client.get(
        f"/api/v1/query/workflows?template_id={tmpl_a.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["meta"]["total_count"] == 2


async def test_query_workflows_by_date_range(
    async_client: AsyncClient, admin_token: str, db_session: AsyncSession
):
    """QUERY-01: Filter by date range returns only workflows in range."""
    tmpl = await _create_template(db_session)
    now = datetime.now(timezone.utc)
    old = now - timedelta(days=30)
    recent = now - timedelta(days=1)

    await _create_workflow(db_session, tmpl, created_at=old)
    await _create_workflow(db_session, tmpl, created_at=recent)
    await db_session.commit()

    date_from = (now - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%S")
    date_to = now.strftime("%Y-%m-%dT%H:%M:%S")
    resp = await async_client.get(
        f"/api/v1/query/workflows?date_from={date_from}&date_to={date_to}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["meta"]["total_count"] == 1


async def test_query_workflows_by_started_by(
    async_client: AsyncClient,
    admin_token: str,
    admin_user,
    regular_user,
    db_session: AsyncSession,
):
    """QUERY-01: Filter by started_by (supervisor_id) returns only that user's workflows."""
    tmpl = await _create_template(db_session)
    await _create_workflow(db_session, tmpl, supervisor_id=admin_user.id)
    await _create_workflow(db_session, tmpl, supervisor_id=regular_user.id)
    await db_session.commit()

    resp = await async_client.get(
        f"/api/v1/query/workflows?started_by={admin_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["meta"]["total_count"] == 1


async def test_query_workflows_pagination(
    async_client: AsyncClient, admin_token: str, db_session: AsyncSession
):
    """QUERY-01: Pagination with limit=2 on 5 workflows returns correct page info."""
    tmpl = await _create_template(db_session)
    for _ in range(5):
        await _create_workflow(db_session, tmpl)
    await db_session.commit()

    resp = await async_client.get(
        "/api/v1/query/workflows?limit=2",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) == 2
    assert body["meta"]["total_count"] == 5
    assert body["meta"]["total_pages"] == 3


# ---- QUERY-02: Work item queries ----


async def test_query_work_items_no_filter(
    async_client: AsyncClient, admin_token: str, db_session: AsyncSession
):
    """QUERY-02: Query all work items without filters."""
    tmpl = await _create_template(db_session)
    wf = await _create_workflow(db_session, tmpl)
    ai = await _create_activity_instance(db_session, wf, tmpl)
    await _create_work_item(db_session, ai)
    await _create_work_item(db_session, ai)
    await db_session.commit()

    resp = await async_client.get(
        "/api/v1/query/work-items",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) == 2
    assert body["meta"]["total_count"] == 2


async def test_query_work_items_by_assignee(
    async_client: AsyncClient,
    admin_token: str,
    admin_user,
    regular_user,
    db_session: AsyncSession,
):
    """QUERY-02: Filter work items by assignee returns only matching."""
    tmpl = await _create_template(db_session)
    wf = await _create_workflow(db_session, tmpl)
    ai = await _create_activity_instance(db_session, wf, tmpl)
    await _create_work_item(db_session, ai, performer_id=admin_user.id)
    await _create_work_item(db_session, ai, performer_id=regular_user.id)
    await db_session.commit()

    resp = await async_client.get(
        f"/api/v1/query/work-items?assignee_id={admin_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["meta"]["total_count"] == 1


async def test_query_work_items_by_state(
    async_client: AsyncClient, admin_token: str, db_session: AsyncSession
):
    """QUERY-02: Filter work items by state."""
    tmpl = await _create_template(db_session)
    wf = await _create_workflow(db_session, tmpl)
    ai = await _create_activity_instance(db_session, wf, tmpl)
    await _create_work_item(db_session, ai, state=WorkItemState.AVAILABLE)
    await _create_work_item(db_session, ai, state=WorkItemState.COMPLETE)
    await db_session.commit()

    resp = await async_client.get(
        "/api/v1/query/work-items?state=available",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["meta"]["total_count"] == 1
    assert body["data"][0]["state"] == "available"


async def test_query_work_items_by_priority(
    async_client: AsyncClient, admin_token: str, db_session: AsyncSession
):
    """QUERY-02: Filter work items by priority."""
    tmpl = await _create_template(db_session)
    wf = await _create_workflow(db_session, tmpl)
    ai = await _create_activity_instance(db_session, wf, tmpl)
    await _create_work_item(db_session, ai, priority=1)
    await _create_work_item(db_session, ai, priority=5)
    await _create_work_item(db_session, ai, priority=1)
    await db_session.commit()

    resp = await async_client.get(
        "/api/v1/query/work-items?priority=1",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["meta"]["total_count"] == 2
    for item in body["data"]:
        assert item["priority"] == 1


# ---- QUERY-03: Document queries ----


async def test_query_documents_no_filter(
    async_client: AsyncClient, admin_token: str, db_session: AsyncSession
):
    """QUERY-03: Query all documents without filters."""
    await _create_document(db_session, "Doc 1")
    await _create_document(db_session, "Doc 2")
    await db_session.commit()

    resp = await async_client.get(
        "/api/v1/query/documents",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) == 2
    assert body["meta"]["total_count"] == 2


async def test_query_documents_by_lifecycle(
    async_client: AsyncClient, admin_token: str, db_session: AsyncSession
):
    """QUERY-03: Filter documents by lifecycle state."""
    await _create_document(db_session, "Draft Doc", lifecycle_state=LifecycleState.DRAFT)
    await _create_document(db_session, "Approved Doc", lifecycle_state=LifecycleState.APPROVED)
    await db_session.commit()

    resp = await async_client.get(
        "/api/v1/query/documents?lifecycle_state=draft",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["meta"]["total_count"] == 1
    assert body["data"][0]["lifecycle_state"] == "draft"


async def test_query_documents_by_metadata(
    async_client: AsyncClient, admin_token: str, db_session: AsyncSession
):
    """QUERY-03: Filter documents by custom metadata key/value."""
    await _create_document(
        db_session, "Contract", custom_properties={"department": "legal", "author": "John"}
    )
    await _create_document(
        db_session, "Report", custom_properties={"department": "finance"}
    )
    await db_session.commit()

    resp = await async_client.get(
        "/api/v1/query/documents?metadata_key=author&metadata_value=John",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["meta"]["total_count"] == 1
    assert body["data"][0]["title"] == "Contract"


async def test_query_requires_admin(
    async_client: AsyncClient, regular_token: str
):
    """All query endpoints require admin authentication."""
    headers = {"Authorization": f"Bearer {regular_token}"}

    resp_wf = await async_client.get("/api/v1/query/workflows", headers=headers)
    assert resp_wf.status_code == 403

    resp_wi = await async_client.get("/api/v1/query/work-items", headers=headers)
    assert resp_wi.status_code == 403

    resp_doc = await async_client.get("/api/v1/query/documents", headers=headers)
    assert resp_doc.status_code == 403
