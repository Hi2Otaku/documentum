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


# ---------------------------------------------------------------------------
# SLA compliance
# ---------------------------------------------------------------------------


async def test_sla_data_empty(db_session: AsyncSession):
    """SLA returns empty when no activities have expected_duration_hours set."""
    tmpl = await _create_template(db_session)
    at = await _create_activity_template(db_session, tmpl, "No SLA")
    # expected_duration_hours is None by default
    wf = await _create_workflow(db_session, tmpl)
    ai = await _create_activity_instance(db_session, wf, at)
    await db_session.commit()

    result = await _dashboard_service.get_sla_data(db_session)
    assert result == []


async def test_sla_data_with_on_time_and_overdue(
    db_session: AsyncSession, admin_user,
):
    """SLA correctly computes on_time vs overdue work items."""
    tmpl = await _create_template(db_session)
    at = await _create_activity_template(db_session, tmpl, "Review")
    at.expected_duration_hours = 2.0
    await db_session.flush()

    wf = await _create_workflow(db_session, tmpl)
    ai = await _create_activity_instance(db_session, wf, at)

    now = datetime.now(timezone.utc)

    # On-time work item: completed in 1 hour (within 2h SLA)
    wi_on_time = WorkItem(
        activity_instance_id=ai.id,
        performer_id=admin_user.id,
        state=WorkItemState.COMPLETE,
        completed_at=now,
    )
    wi_on_time.created_at = now - timedelta(hours=1)
    db_session.add(wi_on_time)

    # Overdue work item: completed in 3 hours (exceeds 2h SLA)
    wi_overdue = WorkItem(
        activity_instance_id=ai.id,
        performer_id=admin_user.id,
        state=WorkItemState.COMPLETE,
        completed_at=now,
    )
    wi_overdue.created_at = now - timedelta(hours=3)
    db_session.add(wi_overdue)

    # Another on-time work item
    wi_on_time2 = WorkItem(
        activity_instance_id=ai.id,
        performer_id=admin_user.id,
        state=WorkItemState.COMPLETE,
        completed_at=now,
    )
    wi_on_time2.created_at = now - timedelta(minutes=30)
    db_session.add(wi_on_time2)

    await db_session.flush()
    await db_session.commit()

    sla = await _dashboard_service.get_sla_data(db_session)
    assert len(sla) == 1
    assert sla[0].activity_name == "Review"
    assert sla[0].on_time == 2
    assert sla[0].overdue == 1
    assert abs(sla[0].compliance_percent - 66.67) < 0.1


# ---------------------------------------------------------------------------
# KPI metrics
# ---------------------------------------------------------------------------


async def test_kpi_metrics_shape(db_session: AsyncSession):
    """KPI metrics returns correct shape with all fields."""
    tmpl = await _create_template(db_session)
    now = datetime.now(timezone.utc)

    await _create_workflow(db_session, tmpl, WorkflowState.RUNNING)
    await _create_workflow(db_session, tmpl, WorkflowState.RUNNING)
    await _create_workflow(db_session, tmpl, WorkflowState.HALTED)
    await _create_workflow(
        db_session, tmpl, WorkflowState.FINISHED,
        started_at=now - timedelta(hours=2), completed_at=now,
    )
    await _create_workflow(db_session, tmpl, WorkflowState.FAILED)
    await db_session.commit()

    kpi = await _dashboard_service.get_kpi_metrics(db_session)
    assert kpi.running == 2
    assert kpi.halted == 1
    assert kpi.finished == 1
    assert kpi.failed == 1
    assert kpi.avg_completion_hours > 0


async def test_kpi_metrics_empty(db_session: AsyncSession):
    """KPI metrics returns zeros when no workflows exist."""
    kpi = await _dashboard_service.get_kpi_metrics(db_session)
    assert kpi.running == 0
    assert kpi.halted == 0
    assert kpi.finished == 0
    assert kpi.failed == 0
    assert kpi.avg_completion_hours == 0.0


# ---------------------------------------------------------------------------
# Unified metrics (get_all_metrics)
# ---------------------------------------------------------------------------


async def test_all_metrics_shape(db_session: AsyncSession, admin_user):
    """get_all_metrics returns DashboardMetrics with all four sections."""
    tmpl = await _create_template(db_session)
    at = await _create_activity_template(db_session, tmpl, "Review")
    at.expected_duration_hours = 1.0
    await db_session.flush()

    now = datetime.now(timezone.utc)
    wf = await _create_workflow(
        db_session, tmpl, WorkflowState.FINISHED,
        started_at=now - timedelta(hours=1), completed_at=now,
    )
    ai = await _create_activity_instance(
        db_session, wf, at,
        state=ActivityState.COMPLETE,
        started_at=now - timedelta(hours=1),
        completed_at=now,
    )

    # Create a completed work item (on-time)
    wi = WorkItem(
        activity_instance_id=ai.id,
        performer_id=admin_user.id,
        state=WorkItemState.COMPLETE,
        completed_at=now,
    )
    wi.created_at = now - timedelta(minutes=30)
    db_session.add(wi)
    await db_session.flush()
    await db_session.commit()

    metrics = await _dashboard_service.get_all_metrics(db_session)
    # Check shape
    assert hasattr(metrics, "kpi")
    assert hasattr(metrics, "bottleneck_activities")
    assert hasattr(metrics, "workload")
    assert hasattr(metrics, "sla_compliance")

    # KPI
    assert metrics.kpi.finished == 1

    # SLA
    assert len(metrics.sla_compliance) == 1
    assert metrics.sla_compliance[0].activity_name == "Review"
    assert metrics.sla_compliance[0].on_time == 1
