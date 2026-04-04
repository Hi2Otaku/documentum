"""Tests for BAM dashboard service functions.

Tests the dashboard_service directly since the worktree's new modules
aren't visible through the editable install. The HTTP layer is trivial
(router calls service, wraps in EnvelopeResponse).
"""
import importlib
import pathlib
import sys
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import (
    ActivityState,
    ActivityType,
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
# Load worktree modules that aren't in the editable install yet
# ---------------------------------------------------------------------------

_worktree_src = pathlib.Path(__file__).resolve().parent.parent / "src"


def _load_worktree_module(dotted: str):
    """Load a module from the worktree src directory."""
    parts = dotted.split(".")
    fpath = _worktree_src / (("/".join(parts)) + ".py")
    if not fpath.exists():
        return importlib.import_module(dotted)
    spec = importlib.util.spec_from_file_location(dotted, str(fpath))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[dotted] = mod
    spec.loader.exec_module(mod)
    return mod


# Pre-load schemas before service (service imports schemas)
_dashboard_schemas = _load_worktree_module("app.schemas.dashboard")
_dashboard_service = _load_worktree_module("app.services.dashboard_service")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_template(db: AsyncSession, name: str = "Test WF") -> ProcessTemplate:
    t = ProcessTemplate(name=name, version=1, is_installed=True)
    db.add(t)
    await db.flush()
    return t


async def _create_activity_template(
    db: AsyncSession, template: ProcessTemplate, name: str = "Review"
) -> ActivityTemplate:
    at = ActivityTemplate(
        process_template_id=template.id,
        name=name,
        activity_type=ActivityType.MANUAL,
    )
    db.add(at)
    await db.flush()
    return at


async def _create_workflow(
    db: AsyncSession,
    template: ProcessTemplate,
    state: WorkflowState = WorkflowState.RUNNING,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
    supervisor_id: uuid.UUID | None = None,
) -> WorkflowInstance:
    now = datetime.now(timezone.utc)
    w = WorkflowInstance(
        process_template_id=template.id,
        state=state,
        started_at=started_at or now,
        completed_at=completed_at,
        supervisor_id=supervisor_id,
    )
    db.add(w)
    await db.flush()
    return w


async def _create_activity_instance(
    db: AsyncSession,
    workflow: WorkflowInstance,
    activity_template: ActivityTemplate,
    state: ActivityState = ActivityState.ACTIVE,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
) -> ActivityInstance:
    now = datetime.now(timezone.utc)
    ai = ActivityInstance(
        workflow_instance_id=workflow.id,
        activity_template_id=activity_template.id,
        state=state,
        started_at=started_at or now,
        completed_at=completed_at,
    )
    db.add(ai)
    await db.flush()
    return ai


async def _create_work_item(
    db: AsyncSession,
    activity_instance: ActivityInstance,
    performer_id: uuid.UUID,
    state: WorkItemState = WorkItemState.AVAILABLE,
) -> WorkItem:
    wi = WorkItem(
        activity_instance_id=activity_instance.id,
        performer_id=performer_id,
        state=state,
    )
    db.add(wi)
    await db.flush()
    return wi


# ---------------------------------------------------------------------------
# Dashboard summary
# ---------------------------------------------------------------------------


async def test_workflow_summary_empty(db_session: AsyncSession):
    """Summary returns zeros when no workflows exist."""
    summary = await _dashboard_service.get_workflow_summary(db_session)
    assert summary.total == 0
    assert summary.by_state == []
    assert summary.avg_completion_seconds is None


async def test_workflow_summary_with_data(db_session: AsyncSession):
    """Summary returns correct counts by state."""
    tmpl = await _create_template(db_session)
    now = datetime.now(timezone.utc)

    await _create_workflow(db_session, tmpl, WorkflowState.RUNNING)
    await _create_workflow(db_session, tmpl, WorkflowState.RUNNING)
    await _create_workflow(
        db_session, tmpl, WorkflowState.FINISHED,
        started_at=now - timedelta(hours=1), completed_at=now,
    )
    await db_session.commit()

    summary = await _dashboard_service.get_workflow_summary(db_session)
    assert summary.total == 3

    state_map = {item.state: item.count for item in summary.by_state}
    assert state_map.get("running") == 2
    assert state_map.get("finished") == 1


async def test_workflow_summary_avg_completion(db_session: AsyncSession):
    """Summary computes average completion time for finished workflows."""
    tmpl = await _create_template(db_session)
    now = datetime.now(timezone.utc)

    # Two finished workflows: 1h and 3h
    await _create_workflow(
        db_session, tmpl, WorkflowState.FINISHED,
        started_at=now - timedelta(hours=1), completed_at=now,
    )
    await _create_workflow(
        db_session, tmpl, WorkflowState.FINISHED,
        started_at=now - timedelta(hours=3), completed_at=now,
    )
    await db_session.commit()

    summary = await _dashboard_service.get_workflow_summary(db_session)
    assert summary.avg_completion_seconds is not None
    # Average of 1h and 3h = 2h = 7200 seconds
    assert abs(summary.avg_completion_seconds - 7200) < 60  # Allow small rounding


# ---------------------------------------------------------------------------
# Bottleneck activities
# ---------------------------------------------------------------------------


async def test_bottleneck_empty(db_session: AsyncSession):
    """Bottleneck returns empty list when no activities exist."""
    result = await _dashboard_service.get_bottleneck_activities(db_session)
    assert result == []


async def test_bottleneck_with_data(db_session: AsyncSession):
    """Bottleneck identifies slow activities."""
    tmpl = await _create_template(db_session)
    at_slow = await _create_activity_template(db_session, tmpl, "Slow Review")
    at_fast = await _create_activity_template(db_session, tmpl, "Fast Review")

    now = datetime.now(timezone.utc)
    wf = await _create_workflow(db_session, tmpl)

    # Slow activity: 2 hours
    await _create_activity_instance(
        db_session, wf, at_slow,
        state=ActivityState.COMPLETE,
        started_at=now - timedelta(hours=2),
        completed_at=now,
    )
    # Fast activity: 10 minutes
    await _create_activity_instance(
        db_session, wf, at_fast,
        state=ActivityState.COMPLETE,
        started_at=now - timedelta(minutes=10),
        completed_at=now,
    )
    await db_session.commit()

    bottlenecks = await _dashboard_service.get_bottleneck_activities(db_session)
    assert len(bottlenecks) == 2
    # Slow should be first (highest avg duration)
    assert bottlenecks[0].activity_name == "Slow Review"
    assert bottlenecks[0].avg_duration_seconds > bottlenecks[1].avg_duration_seconds


async def test_bottleneck_limit(db_session: AsyncSession):
    """Bottleneck respects the limit parameter."""
    tmpl = await _create_template(db_session)
    now = datetime.now(timezone.utc)
    wf = await _create_workflow(db_session, tmpl)

    for i in range(5):
        at = await _create_activity_template(db_session, tmpl, f"Activity {i}")
        await _create_activity_instance(
            db_session, wf, at,
            state=ActivityState.COMPLETE,
            started_at=now - timedelta(hours=i + 1),
            completed_at=now,
        )
    await db_session.commit()

    result = await _dashboard_service.get_bottleneck_activities(db_session, limit=3)
    assert len(result) == 3


# ---------------------------------------------------------------------------
# User workload
# ---------------------------------------------------------------------------


async def test_user_workload_empty(db_session: AsyncSession):
    """Workload returns empty when no pending items."""
    result = await _dashboard_service.get_user_workload(db_session)
    assert result == []


async def test_user_workload_with_data(
    db_session: AsyncSession, admin_user,
):
    """Workload counts pending items per user."""
    tmpl = await _create_template(db_session)
    at = await _create_activity_template(db_session, tmpl)
    wf = await _create_workflow(db_session, tmpl)
    ai = await _create_activity_instance(db_session, wf, at)

    # 2 available + 1 acquired for admin
    await _create_work_item(db_session, ai, admin_user.id, WorkItemState.AVAILABLE)
    await _create_work_item(db_session, ai, admin_user.id, WorkItemState.AVAILABLE)
    await _create_work_item(db_session, ai, admin_user.id, WorkItemState.ACQUIRED)
    # 1 completed (should NOT count)
    await _create_work_item(db_session, ai, admin_user.id, WorkItemState.COMPLETE)
    await db_session.commit()

    workload = await _dashboard_service.get_user_workload(db_session)
    assert len(workload) == 1
    assert workload[0].username == "admin"
    assert workload[0].available_count == 2
    assert workload[0].acquired_count == 1
    assert workload[0].total_pending == 3


# ---------------------------------------------------------------------------
# Template metrics
# ---------------------------------------------------------------------------


async def test_template_metrics_empty(db_session: AsyncSession):
    """Template metrics returns empty when no workflows exist."""
    result = await _dashboard_service.get_template_metrics(db_session)
    assert result == []


async def test_template_metrics_with_data(db_session: AsyncSession):
    """Template metrics breaks down instances by state per template."""
    tmpl = await _create_template(db_session, "Approval WF")
    now = datetime.now(timezone.utc)

    await _create_workflow(db_session, tmpl, WorkflowState.RUNNING)
    await _create_workflow(
        db_session, tmpl, WorkflowState.FINISHED,
        started_at=now - timedelta(hours=1), completed_at=now,
    )
    await _create_workflow(db_session, tmpl, WorkflowState.FAILED)
    await db_session.commit()

    metrics = await _dashboard_service.get_template_metrics(db_session)
    assert len(metrics) == 1
    m = metrics[0]
    assert m.template_name == "Approval WF"
    assert m.total_instances == 3
    assert m.running == 1
    assert m.finished == 1
    assert m.failed == 1
