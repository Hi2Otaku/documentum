"""Tests for timer activities and escalation (TIMER-01 through TIMER-04, NOTIF-03).

Covers deadline configuration on activity templates, due-date computation on
work items, overdue detection via Beat task, escalation actions (priority bump),
and approaching-deadline notifications.
"""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import (
    ActivityState,
    ActivityType,
    ProcessState,
    TriggerType,
    WorkflowState,
    WorkItemState,
)
from app.models.user import User
from app.models.workflow import (
    ActivityInstance,
    ActivityTemplate,
    ProcessTemplate,
    WorkflowInstance,
    WorkItem,
)
from app.services.engine_service import _compute_due_date

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helper to build the full object chain needed for work items in the DB
# ---------------------------------------------------------------------------


async def _create_work_item_chain(
    db: AsyncSession,
    user: User,
    *,
    expected_duration_hours: float | None = 24.0,
    escalation_action: str | None = "priority_bump",
    warning_threshold_hours: float | None = 4.0,
    due_date: datetime | None = None,
    priority: int = 5,
    is_escalated: bool = False,
    deadline_warning_sent: bool = False,
    wi_state: WorkItemState = WorkItemState.AVAILABLE,
) -> tuple[WorkItem, ActivityTemplate]:
    """Create ProcessTemplate -> ActivityTemplate -> WorkflowInstance ->
    ActivityInstance -> WorkItem chain and return (work_item, activity_template)."""
    pt = ProcessTemplate(
        id=uuid.uuid4(),
        name="Timer Test Template",
        state=ProcessState.DRAFT,
        created_by=str(user.id),
    )
    db.add(pt)
    await db.flush()

    at = ActivityTemplate(
        id=uuid.uuid4(),
        process_template_id=pt.id,
        name="Timed Review",
        activity_type=ActivityType.MANUAL,
        trigger_type=TriggerType.OR_JOIN,
        expected_duration_hours=expected_duration_hours,
        escalation_action=escalation_action,
        warning_threshold_hours=warning_threshold_hours,
        created_by=str(user.id),
    )
    db.add(at)
    await db.flush()

    wi_inst = WorkflowInstance(
        id=uuid.uuid4(),
        process_template_id=pt.id,
        state=WorkflowState.RUNNING,
        supervisor_id=user.id,
        started_at=datetime.now(timezone.utc),
        created_by=str(user.id),
    )
    db.add(wi_inst)
    await db.flush()

    ai = ActivityInstance(
        id=uuid.uuid4(),
        workflow_instance_id=wi_inst.id,
        activity_template_id=at.id,
        state=ActivityState.ACTIVE,
        started_at=datetime.now(timezone.utc),
        created_by=str(user.id),
    )
    db.add(ai)
    await db.flush()

    wi = WorkItem(
        id=uuid.uuid4(),
        activity_instance_id=ai.id,
        performer_id=user.id,
        state=wi_state,
        priority=priority,
        is_escalated=is_escalated,
        deadline_warning_sent=deadline_warning_sent,
        due_date=due_date,
        created_by=str(user.id),
    )
    db.add(wi)
    await db.flush()

    return wi, at


# ---------------------------------------------------------------------------
# TIMER-01: Activity template deadline config via API
# ---------------------------------------------------------------------------


async def test_activity_template_deadline_config(
    async_client: AsyncClient, admin_token: str, admin_user: User
) -> None:
    """TIMER-01: Creating/updating an activity template with expected_duration_hours,
    escalation_action, and warning_threshold_hours persists and returns the values
    via the API."""
    # Create a process template first
    headers = {"Authorization": f"Bearer {admin_token}"}
    pt_resp = await async_client.post(
        "/api/v1/templates/",
        json={"name": "Deadline Test", "description": "Test deadline fields"},
        headers=headers,
    )
    assert pt_resp.status_code in (200, 201), pt_resp.text
    pt_id = pt_resp.json()["data"]["id"]

    # Create an activity template with deadline fields
    at_resp = await async_client.post(
        f"/api/v1/templates/{pt_id}/activities",
        json={
            "name": "Review Step",
            "activity_type": "manual",
            "expected_duration_hours": 24,
            "escalation_action": "priority_bump",
            "warning_threshold_hours": 4,
        },
        headers=headers,
    )
    assert at_resp.status_code in (200, 201), at_resp.text
    at_data = at_resp.json()["data"]
    assert at_data["expected_duration_hours"] == 24
    assert at_data["escalation_action"] == "priority_bump"
    assert at_data["warning_threshold_hours"] == 4


# ---------------------------------------------------------------------------
# TIMER-02: Due date computation unit test
# ---------------------------------------------------------------------------


async def test_work_item_due_date_computed(
    async_client: AsyncClient, admin_token: str, admin_user: User
) -> None:
    """TIMER-02: _compute_due_date returns now + expected_duration_hours."""
    # Test with duration set
    mock_at = MagicMock()
    mock_at.expected_duration_hours = 24.0
    before = datetime.now(timezone.utc)
    result = _compute_due_date(mock_at)
    after = datetime.now(timezone.utc)

    assert result is not None
    expected_min = before + timedelta(hours=24)
    expected_max = after + timedelta(hours=24)
    assert expected_min <= result <= expected_max

    # Test with no duration
    mock_at_none = MagicMock()
    mock_at_none.expected_duration_hours = None
    assert _compute_due_date(mock_at_none) is None

    # Test with None template
    assert _compute_due_date(None) is None


# ---------------------------------------------------------------------------
# TIMER-03: Deadline checker finds overdue items
# ---------------------------------------------------------------------------


async def test_deadline_checker_finds_overdue(
    async_client: AsyncClient, admin_token: str, admin_user: User, db_session
) -> None:
    """TIMER-03: The _check_deadlines_async periodic task finds work items past
    their due_date and triggers the configured escalation action."""
    # Create a work item that is overdue (due_date in the past)
    wi, at = await _create_work_item_chain(
        db_session,
        admin_user,
        due_date=datetime.now(timezone.utc) - timedelta(hours=1),
        escalation_action="priority_bump",
        is_escalated=False,
    )
    await db_session.commit()

    # Patch create_task_session_factory to return our test session
    # Real flow: create_task_session_factory() -> factory; factory() -> async CM -> session
    wi_id = wi.id

    class _FakeSessionCM:
        async def __aenter__(self):
            return db_session

        async def __aexit__(self, *args):
            return False

    class _FakeFactory:
        def __call__(self):
            return _FakeSessionCM()

    with patch(
        "app.core.database.create_task_session_factory",
        return_value=_FakeFactory(),
    ):
        from app.tasks.notification import _check_deadlines_async

        await _check_deadlines_async()

    # Refresh and check
    await db_session.refresh(wi)
    assert wi.is_escalated is True
    assert wi.priority == 3  # priority_bump: 5 - 2 = 3


# ---------------------------------------------------------------------------
# TIMER-04: Escalation priority bump
# ---------------------------------------------------------------------------


async def test_escalation_priority_bump(
    async_client: AsyncClient, admin_token: str, admin_user: User, db_session
) -> None:
    """TIMER-04: When escalation_action='priority_bump', an overdue work item's
    priority is decreased from 5 (normal) to 3 (high), and is_escalated is set
    to True."""
    wi, at = await _create_work_item_chain(
        db_session,
        admin_user,
        due_date=datetime.now(timezone.utc) - timedelta(hours=2),
        escalation_action="priority_bump",
        priority=5,
    )
    await db_session.commit()

    from app.tasks.notification import _escalate_work_item

    await _escalate_work_item(db_session, wi, at)
    await db_session.flush()

    assert wi.priority == 3
    assert wi.is_escalated is True


# ---------------------------------------------------------------------------
# NOTIF-03: Approaching deadline notification
# ---------------------------------------------------------------------------


async def test_approaching_deadline_notification(
    async_client: AsyncClient, admin_token: str, admin_user: User, db_session
) -> None:
    """NOTIF-03: A work item within the warning_threshold_hours of its due_date
    gets a notification created for the performer, and deadline_warning_sent is
    set to True to prevent duplicate warnings."""
    # Due in 1 hour, warning threshold 2 hours => should trigger
    wi, at = await _create_work_item_chain(
        db_session,
        admin_user,
        due_date=datetime.now(timezone.utc) + timedelta(hours=1),
        warning_threshold_hours=2.0,
        expected_duration_hours=8.0,
        deadline_warning_sent=False,
    )
    await db_session.commit()

    class _FakeSessionCM:
        async def __aenter__(self):
            return db_session

        async def __aexit__(self, *args):
            return False

    class _FakeFactory:
        def __call__(self):
            return _FakeSessionCM()

    with patch(
        "app.core.database.create_task_session_factory",
        return_value=_FakeFactory(),
    ):
        from app.tasks.notification import _check_deadlines_async

        await _check_deadlines_async()

    await db_session.refresh(wi)
    assert wi.deadline_warning_sent is True

    # Verify a notification was created
    from sqlalchemy import select

    from app.models.notification import Notification

    notif_result = await db_session.execute(
        select(Notification).where(
            Notification.entity_id == wi.id,
            Notification.notification_type == "deadline_approaching",
        )
    )
    notification = notif_result.scalar_one_or_none()
    assert notification is not None
    assert "Timed Review" in notification.title or "Deadline" in notification.title
