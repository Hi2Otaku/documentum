"""Tests for admin query interface service functions.

Tests the query_service directly since the worktree's new modules
aren't visible through the editable install. The HTTP layer is trivial.
"""
import importlib
import pathlib
import sys
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.document import Document
from app.models.enums import (
    ActivityState,
    ActivityType,
    LifecycleState,
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

# ---------------------------------------------------------------------------
# Load worktree modules
# ---------------------------------------------------------------------------

_worktree_src = pathlib.Path(__file__).resolve().parent.parent / "src"


def _load_worktree_module(dotted: str):
    parts = dotted.split(".")
    fpath = _worktree_src / (("/".join(parts)) + ".py")
    if not fpath.exists():
        return importlib.import_module(dotted)
    spec = importlib.util.spec_from_file_location(dotted, str(fpath))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[dotted] = mod
    spec.loader.exec_module(mod)
    return mod


_query_schemas = _load_worktree_module("app.schemas.query")
_query_service = _load_worktree_module("app.services.query_service")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _seed_workflows(db: AsyncSession, admin_user):
    """Seed 1 template, 3 workflows (running/finished/halted), 1 work item."""
    tmpl = ProcessTemplate(name="Query Test WF", version=1, is_installed=True)
    db.add(tmpl)
    await db.flush()

    at = ActivityTemplate(
        process_template_id=tmpl.id,
        name="Task",
        activity_type=ActivityType.MANUAL,
    )
    db.add(at)
    await db.flush()

    now = datetime.now(timezone.utc)

    wf_running = WorkflowInstance(
        process_template_id=tmpl.id,
        state=WorkflowState.RUNNING,
        started_at=now - timedelta(hours=2),
        supervisor_id=admin_user.id,
    )
    wf_finished = WorkflowInstance(
        process_template_id=tmpl.id,
        state=WorkflowState.FINISHED,
        started_at=now - timedelta(hours=5),
        completed_at=now - timedelta(hours=1),
    )
    wf_halted = WorkflowInstance(
        process_template_id=tmpl.id,
        state=WorkflowState.HALTED,
        started_at=now - timedelta(hours=3),
    )
    db.add_all([wf_running, wf_finished, wf_halted])
    await db.flush()

    ai = ActivityInstance(
        workflow_instance_id=wf_running.id,
        activity_template_id=at.id,
        state=ActivityState.ACTIVE,
        started_at=now,
    )
    db.add(ai)
    await db.flush()

    wi = WorkItem(
        activity_instance_id=ai.id,
        performer_id=admin_user.id,
        state=WorkItemState.AVAILABLE,
        priority=3,
    )
    db.add(wi)
    await db.flush()

    await db.commit()
    return {
        "template": tmpl,
        "wf_running": wf_running,
        "wf_finished": wf_finished,
        "wf_halted": wf_halted,
        "work_item": wi,
    }


# ---------------------------------------------------------------------------
# Query workflows
# ---------------------------------------------------------------------------


async def test_query_workflows_no_filters(
    db_session: AsyncSession, admin_user,
):
    """Query all workflows without filters returns all."""
    await _seed_workflows(db_session, admin_user)
    filters = _query_schemas.WorkflowQueryRequest()
    results, total = await _query_service.query_workflows(db_session, filters)
    assert total == 3
    assert len(results) == 3


async def test_query_workflows_by_state(
    db_session: AsyncSession, admin_user,
):
    """Query workflows filtered by state."""
    await _seed_workflows(db_session, admin_user)
    filters = _query_schemas.WorkflowQueryRequest(state="running")
    results, total = await _query_service.query_workflows(db_session, filters)
    assert total == 1
    assert results[0].state == "running"


async def test_query_workflows_by_template(
    db_session: AsyncSession, admin_user,
):
    """Query workflows filtered by template_id."""
    data = await _seed_workflows(db_session, admin_user)
    tmpl_id = data["template"].id
    filters = _query_schemas.WorkflowQueryRequest(template_id=tmpl_id)
    results, total = await _query_service.query_workflows(db_session, filters)
    assert total == 3
    for r in results:
        assert r.process_template_id == tmpl_id


async def test_query_workflows_by_supervisor(
    db_session: AsyncSession, admin_user,
):
    """Query workflows filtered by supervisor_id."""
    await _seed_workflows(db_session, admin_user)
    filters = _query_schemas.WorkflowQueryRequest(supervisor_id=admin_user.id)
    results, total = await _query_service.query_workflows(db_session, filters)
    assert total == 1
    assert results[0].state == "running"


async def test_query_workflows_pagination(
    db_session: AsyncSession, admin_user,
):
    """Query workflows with pagination."""
    await _seed_workflows(db_session, admin_user)
    filters = _query_schemas.WorkflowQueryRequest(skip=0, limit=2)
    results, total = await _query_service.query_workflows(db_session, filters)
    assert len(results) == 2
    assert total == 3


async def test_query_workflows_by_date_range(
    db_session: AsyncSession, admin_user,
):
    """Query workflows filtered by started_after."""
    await _seed_workflows(db_session, admin_user)
    now = datetime.now(timezone.utc)
    filters = _query_schemas.WorkflowQueryRequest(
        started_after=now - timedelta(hours=2, minutes=30)
    )
    results, total = await _query_service.query_workflows(db_session, filters)
    # Only the running (2h ago) workflow should match
    assert total == 1


# ---------------------------------------------------------------------------
# Query work items
# ---------------------------------------------------------------------------


async def test_query_work_items_no_filters(
    db_session: AsyncSession, admin_user,
):
    """Query all work items."""
    await _seed_workflows(db_session, admin_user)
    filters = _query_schemas.WorkItemQueryRequest()
    results, total = await _query_service.query_work_items(db_session, filters)
    assert total == 1


async def test_query_work_items_by_performer(
    db_session: AsyncSession, admin_user,
):
    """Query work items by performer_id."""
    await _seed_workflows(db_session, admin_user)
    filters = _query_schemas.WorkItemQueryRequest(performer_id=admin_user.id)
    results, total = await _query_service.query_work_items(db_session, filters)
    assert total == 1
    assert results[0].performer_id == admin_user.id


async def test_query_work_items_by_state(
    db_session: AsyncSession, admin_user,
):
    """Query work items by state."""
    await _seed_workflows(db_session, admin_user)
    filters = _query_schemas.WorkItemQueryRequest(state="available")
    results, total = await _query_service.query_work_items(db_session, filters)
    assert total == 1

    filters = _query_schemas.WorkItemQueryRequest(state="complete")
    results, total = await _query_service.query_work_items(db_session, filters)
    assert total == 0


async def test_query_work_items_by_priority(
    db_session: AsyncSession, admin_user,
):
    """Query work items by priority range."""
    await _seed_workflows(db_session, admin_user)
    # Seeded work item has priority=3
    filters = _query_schemas.WorkItemQueryRequest(priority_min=1, priority_max=5)
    results, total = await _query_service.query_work_items(db_session, filters)
    assert total == 1

    filters = _query_schemas.WorkItemQueryRequest(priority_min=5)
    results, total = await _query_service.query_work_items(db_session, filters)
    assert total == 0


# ---------------------------------------------------------------------------
# Query documents
# ---------------------------------------------------------------------------


async def test_query_documents_no_filters(db_session: AsyncSession):
    """Query documents returns all docs."""
    doc = Document(
        title="Contract v1",
        filename="contract.pdf",
        content_type="application/pdf",
        author="alice",
        lifecycle_state=LifecycleState.DRAFT,
    )
    db_session.add(doc)
    await db_session.commit()

    filters = _query_schemas.DocumentQueryRequest()
    results, total = await _query_service.query_documents(db_session, filters)
    assert total == 1
    assert results[0].title == "Contract v1"


async def test_query_documents_by_title(db_session: AsyncSession):
    """Query documents with title_contains filter."""
    db_session.add(Document(title="Meeting Notes", filename="notes.txt", content_type="text/plain"))
    db_session.add(Document(title="Contract Draft", filename="contract.pdf", content_type="application/pdf"))
    await db_session.commit()

    filters = _query_schemas.DocumentQueryRequest(title_contains="Contract")
    results, total = await _query_service.query_documents(db_session, filters)
    assert total == 1
    assert "Contract" in results[0].title


async def test_query_documents_by_lifecycle_state(db_session: AsyncSession):
    """Query documents by lifecycle state."""
    db_session.add(Document(
        title="Approved Doc", filename="a.pdf",
        content_type="application/pdf", lifecycle_state=LifecycleState.APPROVED,
    ))
    db_session.add(Document(
        title="Draft Doc", filename="d.pdf",
        content_type="application/pdf", lifecycle_state=LifecycleState.DRAFT,
    ))
    await db_session.commit()

    filters = _query_schemas.DocumentQueryRequest(lifecycle_state="approved")
    results, total = await _query_service.query_documents(db_session, filters)
    assert total == 1
    assert results[0].title == "Approved Doc"


async def test_query_documents_by_author(db_session: AsyncSession):
    """Query documents by author."""
    db_session.add(Document(title="Doc A", filename="a.pdf", content_type="application/pdf", author="alice"))
    db_session.add(Document(title="Doc B", filename="b.pdf", content_type="application/pdf", author="bob"))
    await db_session.commit()

    filters = _query_schemas.DocumentQueryRequest(author="alice")
    results, total = await _query_service.query_documents(db_session, filters)
    assert total == 1
    assert results[0].title == "Doc A"


# ---------------------------------------------------------------------------
# Query audit logs
# ---------------------------------------------------------------------------


async def test_query_audit_logs_no_filters(db_session: AsyncSession):
    """Query audit logs returns all records."""
    log = AuditLog(
        entity_type="workflow", entity_id="test-123",
        action="started", user_id="user-1",
    )
    db_session.add(log)
    await db_session.commit()

    filters = _query_schemas.AuditLogQueryRequest()
    results, total = await _query_service.query_audit_logs(db_session, filters)
    assert total == 1
    assert results[0].entity_type == "workflow"
    assert results[0].action == "started"


async def test_query_audit_logs_by_entity_type(db_session: AsyncSession):
    """Query audit logs filtered by entity_type."""
    db_session.add(AuditLog(entity_type="workflow", entity_id="w1", action="started"))
    db_session.add(AuditLog(entity_type="document", entity_id="d1", action="created"))
    db_session.add(AuditLog(entity_type="workflow", entity_id="w2", action="completed"))
    await db_session.commit()

    filters = _query_schemas.AuditLogQueryRequest(entity_type="workflow")
    results, total = await _query_service.query_audit_logs(db_session, filters)
    assert total == 2
    assert all(r.entity_type == "workflow" for r in results)


async def test_query_audit_logs_by_action(db_session: AsyncSession):
    """Query audit logs filtered by action."""
    db_session.add(AuditLog(entity_type="workflow", entity_id="w1", action="started"))
    db_session.add(AuditLog(entity_type="workflow", entity_id="w2", action="completed"))
    await db_session.commit()

    filters = _query_schemas.AuditLogQueryRequest(action="completed")
    results, total = await _query_service.query_audit_logs(db_session, filters)
    assert total == 1
    assert results[0].action == "completed"


async def test_query_audit_logs_by_date_range(db_session: AsyncSession):
    """Query audit logs within a date range."""
    now = datetime.now(timezone.utc)
    old = AuditLog(
        entity_type="workflow", entity_id="w1", action="old",
        timestamp=now - timedelta(days=10),
    )
    recent = AuditLog(
        entity_type="workflow", entity_id="w2", action="recent",
        timestamp=now - timedelta(hours=1),
    )
    db_session.add_all([old, recent])
    await db_session.commit()

    cutoff = now - timedelta(days=1)
    filters = _query_schemas.AuditLogQueryRequest(after=cutoff)
    results, total = await _query_service.query_audit_logs(db_session, filters)
    assert total == 1
    assert results[0].action == "recent"


async def test_query_audit_logs_by_user_id(db_session: AsyncSession):
    """Query audit logs filtered by user_id."""
    db_session.add(AuditLog(entity_type="workflow", entity_id="w1", action="started", user_id="u1"))
    db_session.add(AuditLog(entity_type="workflow", entity_id="w2", action="started", user_id="u2"))
    await db_session.commit()

    filters = _query_schemas.AuditLogQueryRequest(user_id="u1")
    results, total = await _query_service.query_audit_logs(db_session, filters)
    assert total == 1
    assert results[0].user_id == "u1"
