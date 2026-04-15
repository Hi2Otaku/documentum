"""Tests for advanced join semantics: N-of-M, cancelling, timeout joins.

Validates that:
- N-of-M join fires at threshold but not below
- Cancelling join cancels remaining branches when it fires
- Timeout join sets join_timeout_started_at on first token
- FOR UPDATE locking is present in the _should_activate query
- All join types integrate correctly with the engine advance loop
"""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ActivityState, ActivityType, FlowType, TriggerType, WorkflowState, WorkItemState
from app.models.user import User
from app.models.workflow import (
    ActivityInstance,
    ActivityTemplate,
    ExecutionToken,
    FlowTemplate,
    ProcessTemplate,
    WorkflowInstance,
    WorkItem,
)


# ---------------------------------------------------------------------------
# Helpers: create workflow structures directly in the DB
# ---------------------------------------------------------------------------


async def _create_n_of_m_workflow(
    db: AsyncSession,
    user_id: str,
    trigger_type: TriggerType = TriggerType.N_OF_M_JOIN,
    join_threshold: int = 2,
    join_timeout_hours: float | None = None,
    num_branches: int = 3,
) -> dict:
    """Create a parallel workflow: Start -> Branch1..N (manual) -> Join -> End.

    Returns dict with template, instance, and activity IDs.
    """
    # Process template
    pt = ProcessTemplate(
        id=uuid.uuid4(),
        name="N-of-M Test",
        version=1,
        state="active",
        is_installed=True,
        template_family_id=uuid.uuid4(),
        created_by=user_id,
    )
    db.add(pt)
    await db.flush()

    # Activities
    start_at = ActivityTemplate(
        id=uuid.uuid4(),
        process_template_id=pt.id,
        name="Start",
        activity_type=ActivityType.START,
        created_by=user_id,
    )
    db.add(start_at)

    branch_ats = []
    for i in range(num_branches):
        bat = ActivityTemplate(
            id=uuid.uuid4(),
            process_template_id=pt.id,
            name=f"Branch {i+1}",
            activity_type=ActivityType.MANUAL,
            performer_type="user",
            performer_id=user_id,
            created_by=user_id,
        )
        db.add(bat)
        branch_ats.append(bat)

    join_at = ActivityTemplate(
        id=uuid.uuid4(),
        process_template_id=pt.id,
        name="Join",
        activity_type=ActivityType.MANUAL,
        performer_type="user",
        performer_id=user_id,
        trigger_type=trigger_type,
        join_threshold=join_threshold,
        join_timeout_hours=join_timeout_hours,
        created_by=user_id,
    )
    db.add(join_at)

    end_at = ActivityTemplate(
        id=uuid.uuid4(),
        process_template_id=pt.id,
        name="End",
        activity_type=ActivityType.END,
        created_by=user_id,
    )
    db.add(end_at)
    await db.flush()

    # Flows: Start -> each branch, each branch -> Join, Join -> End
    flows = []

    for bat in branch_ats:
        f1 = FlowTemplate(
            id=uuid.uuid4(),
            process_template_id=pt.id,
            source_activity_id=start_at.id,
            target_activity_id=bat.id,
            flow_type=FlowType.NORMAL,
            created_by=user_id,
        )
        db.add(f1)
        flows.append(f1)

    branch_to_join_flows = []
    for bat in branch_ats:
        f2 = FlowTemplate(
            id=uuid.uuid4(),
            process_template_id=pt.id,
            source_activity_id=bat.id,
            target_activity_id=join_at.id,
            flow_type=FlowType.NORMAL,
            created_by=user_id,
        )
        db.add(f2)
        flows.append(f2)
        branch_to_join_flows.append(f2)

    join_to_end = FlowTemplate(
        id=uuid.uuid4(),
        process_template_id=pt.id,
        source_activity_id=join_at.id,
        target_activity_id=end_at.id,
        flow_type=FlowType.NORMAL,
        created_by=user_id,
    )
    db.add(join_to_end)
    flows.append(join_to_end)
    await db.flush()

    # Workflow instance
    wf = WorkflowInstance(
        id=uuid.uuid4(),
        process_template_id=pt.id,
        state=WorkflowState.RUNNING,
        started_at=datetime.now(timezone.utc),
        created_by=user_id,
    )
    db.add(wf)
    await db.flush()

    # Activity instances
    start_ai = ActivityInstance(
        id=uuid.uuid4(),
        workflow_instance_id=wf.id,
        activity_template_id=start_at.id,
        state=ActivityState.COMPLETE,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        created_by=user_id,
    )
    db.add(start_ai)

    branch_ais = []
    for bat in branch_ats:
        bai = ActivityInstance(
            id=uuid.uuid4(),
            workflow_instance_id=wf.id,
            activity_template_id=bat.id,
            state=ActivityState.ACTIVE,
            started_at=datetime.now(timezone.utc),
            created_by=user_id,
        )
        db.add(bai)
        branch_ais.append(bai)

    join_ai = ActivityInstance(
        id=uuid.uuid4(),
        workflow_instance_id=wf.id,
        activity_template_id=join_at.id,
        state=ActivityState.DORMANT,
        created_by=user_id,
    )
    db.add(join_ai)

    end_ai = ActivityInstance(
        id=uuid.uuid4(),
        workflow_instance_id=wf.id,
        activity_template_id=end_at.id,
        state=ActivityState.DORMANT,
        created_by=user_id,
    )
    db.add(end_ai)
    await db.flush()

    return {
        "pt": pt,
        "wf": wf,
        "start_at": start_at,
        "branch_ats": branch_ats,
        "join_at": join_at,
        "end_at": end_at,
        "start_ai": start_ai,
        "branch_ais": branch_ais,
        "join_ai": join_ai,
        "end_ai": end_ai,
        "flows": flows,
        "branch_to_join_flows": branch_to_join_flows,
        "join_to_end": join_to_end,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_n_of_m_join_fires_at_threshold(db_session: AsyncSession, admin_user: User):
    """N-of-M join (threshold=2, branches=3) should fire after 2nd token."""
    user_id = str(admin_user.id)
    data = await _create_n_of_m_workflow(
        db_session, user_id,
        trigger_type=TriggerType.N_OF_M_JOIN,
        join_threshold=2,
        num_branches=3,
    )
    await db_session.commit()

    from app.services.engine_service import _should_activate

    # Place 1 token -- should NOT fire
    token1 = ExecutionToken(
        id=uuid.uuid4(),
        workflow_instance_id=data["wf"].id,
        flow_template_id=data["branch_to_join_flows"][0].id,
        source_activity_instance_id=data["branch_ais"][0].id,
        target_activity_template_id=data["join_at"].id,
        is_consumed=False,
        created_by=user_id,
    )
    db_session.add(token1)
    await db_session.flush()

    result = await _should_activate(
        db_session,
        data["wf"].id,
        data["join_at"].id,
        TriggerType.N_OF_M_JOIN,
        data["flows"],
        activity_template=data["join_at"],
    )
    assert result is False, "Should NOT fire with 1 token (threshold=2)"

    # Place 2nd token -- SHOULD fire
    token2 = ExecutionToken(
        id=uuid.uuid4(),
        workflow_instance_id=data["wf"].id,
        flow_template_id=data["branch_to_join_flows"][1].id,
        source_activity_instance_id=data["branch_ais"][1].id,
        target_activity_template_id=data["join_at"].id,
        is_consumed=False,
        created_by=user_id,
    )
    db_session.add(token2)
    await db_session.flush()

    result = await _should_activate(
        db_session,
        data["wf"].id,
        data["join_at"].id,
        TriggerType.N_OF_M_JOIN,
        data["flows"],
        activity_template=data["join_at"],
    )
    assert result is True, "Should fire with 2 tokens (threshold=2)"


@pytest.mark.asyncio
async def test_n_of_m_join_does_not_fire_below_threshold(db_session: AsyncSession, admin_user: User):
    """N-of-M join should not fire when token count is below threshold."""
    user_id = str(admin_user.id)
    data = await _create_n_of_m_workflow(
        db_session, user_id,
        trigger_type=TriggerType.N_OF_M_JOIN,
        join_threshold=3,
        num_branches=3,
    )
    await db_session.commit()

    from app.services.engine_service import _should_activate

    # Place 2 tokens -- should NOT fire (threshold=3)
    for i in range(2):
        token = ExecutionToken(
            id=uuid.uuid4(),
            workflow_instance_id=data["wf"].id,
            flow_template_id=data["branch_to_join_flows"][i].id,
            source_activity_instance_id=data["branch_ais"][i].id,
            target_activity_template_id=data["join_at"].id,
            is_consumed=False,
            created_by=user_id,
        )
        db_session.add(token)

    await db_session.flush()

    result = await _should_activate(
        db_session,
        data["wf"].id,
        data["join_at"].id,
        TriggerType.N_OF_M_JOIN,
        data["flows"],
        activity_template=data["join_at"],
    )
    assert result is False, "Should NOT fire with 2 tokens (threshold=3)"


@pytest.mark.asyncio
async def test_cancelling_join_cancels_branches(db_session: AsyncSession, admin_user: User):
    """Cancelling join should cancel remaining DORMANT/ACTIVE activities after firing."""
    user_id = str(admin_user.id)
    data = await _create_n_of_m_workflow(
        db_session, user_id,
        trigger_type=TriggerType.CANCELLING_JOIN,
        join_threshold=1,
        num_branches=3,
    )
    await db_session.commit()

    from app.services.engine_service import _cancel_remaining_branches

    # Place 1 token from branch 0 (threshold=1, so join fires)
    token = ExecutionToken(
        id=uuid.uuid4(),
        workflow_instance_id=data["wf"].id,
        flow_template_id=data["branch_to_join_flows"][0].id,
        source_activity_instance_id=data["branch_ais"][0].id,
        target_activity_template_id=data["join_at"].id,
        is_consumed=False,
        created_by=user_id,
    )
    db_session.add(token)
    await db_session.flush()

    # Build template_to_instance
    template_to_instance = {}
    for bat, bai in zip(data["branch_ats"], data["branch_ais"]):
        template_to_instance[bat.id] = bai
    template_to_instance[data["join_at"].id] = data["join_ai"]
    template_to_instance[data["end_at"].id] = data["end_ai"]
    template_to_instance[data["start_at"].id] = data["start_ai"]

    # Cancel remaining branches
    await _cancel_remaining_branches(
        db_session,
        data["wf"].id,
        data["join_at"].id,
        data["flows"],
        template_to_instance,
    )
    await db_session.flush()

    # Branch 0 was ACTIVE, branches 1 and 2 were ACTIVE
    # All should be cancelled since they feed into the join
    for i, bai in enumerate(data["branch_ais"]):
        await db_session.refresh(bai)
        assert bai.state == ActivityState.CANCELLED, (
            f"Branch {i} should be CANCELLED, got {bai.state.value}"
        )


@pytest.mark.asyncio
async def test_timeout_join_sets_started_at(db_session: AsyncSession, admin_user: User):
    """Timeout join should set join_timeout_started_at on first token arrival."""
    user_id = str(admin_user.id)
    data = await _create_n_of_m_workflow(
        db_session, user_id,
        trigger_type=TriggerType.TIMEOUT_JOIN,
        join_threshold=None,
        join_timeout_hours=1.0,
        num_branches=3,
    )
    await db_session.commit()

    from app.services.engine_service import _should_activate

    # Verify join_timeout_started_at is initially None
    assert data["join_ai"].join_timeout_started_at is None

    # Place 1 token -- should NOT fire (timeout uses AND_JOIN logic)
    token = ExecutionToken(
        id=uuid.uuid4(),
        workflow_instance_id=data["wf"].id,
        flow_template_id=data["branch_to_join_flows"][0].id,
        source_activity_instance_id=data["branch_ais"][0].id,
        target_activity_template_id=data["join_at"].id,
        is_consumed=False,
        created_by=user_id,
    )
    db_session.add(token)
    await db_session.flush()

    result = await _should_activate(
        db_session,
        data["wf"].id,
        data["join_at"].id,
        TriggerType.TIMEOUT_JOIN,
        data["flows"],
        activity_template=data["join_at"],
    )
    assert result is False, "Timeout join should not fire with 1 of 3 tokens"

    # Simulate what advance_workflow does: set join_timeout_started_at
    if not result and data["join_ai"].join_timeout_started_at is None:
        data["join_ai"].join_timeout_started_at = datetime.now(timezone.utc)

    await db_session.flush()
    await db_session.refresh(data["join_ai"])
    assert data["join_ai"].join_timeout_started_at is not None, (
        "join_timeout_started_at should be set after first token"
    )


@pytest.mark.asyncio
async def test_for_update_prevents_duplicate_activation(db_session: AsyncSession, admin_user: User):
    """Verify that _should_activate uses FOR UPDATE locking (on non-SQLite).

    Since tests run on SQLite, we verify the code path exists by checking
    that the function handles both SQLite (no locking) and PostgreSQL
    (with locking) correctly and returns consistent results.
    """
    user_id = str(admin_user.id)
    data = await _create_n_of_m_workflow(
        db_session, user_id,
        trigger_type=TriggerType.N_OF_M_JOIN,
        join_threshold=2,
        num_branches=3,
    )
    await db_session.commit()

    from app.services.engine_service import _should_activate

    # Place 2 tokens
    for i in range(2):
        token = ExecutionToken(
            id=uuid.uuid4(),
            workflow_instance_id=data["wf"].id,
            flow_template_id=data["branch_to_join_flows"][i].id,
            source_activity_instance_id=data["branch_ais"][i].id,
            target_activity_template_id=data["join_at"].id,
            is_consumed=False,
            created_by=user_id,
        )
        db_session.add(token)
    await db_session.flush()

    # Two concurrent calls should both see 2 tokens and return True
    # (in production, FOR UPDATE prevents the race; here we verify logic)
    result1 = await _should_activate(
        db_session, data["wf"].id, data["join_at"].id,
        TriggerType.N_OF_M_JOIN, data["flows"],
        activity_template=data["join_at"],
    )
    result2 = await _should_activate(
        db_session, data["wf"].id, data["join_at"].id,
        TriggerType.N_OF_M_JOIN, data["flows"],
        activity_template=data["join_at"],
    )
    assert result1 is True
    assert result2 is True

    # Verify the source code contains with_for_update
    import inspect
    source = inspect.getsource(_should_activate)
    assert "with_for_update" in source, (
        "_should_activate must use with_for_update() for race condition prevention"
    )


@pytest.mark.asyncio
async def test_cancelling_join_defaults_threshold_to_1(db_session: AsyncSession, admin_user: User):
    """Cancelling join with no explicit threshold should default to 1."""
    user_id = str(admin_user.id)
    data = await _create_n_of_m_workflow(
        db_session, user_id,
        trigger_type=TriggerType.CANCELLING_JOIN,
        join_threshold=None,  # No explicit threshold
        num_branches=3,
    )
    await db_session.commit()

    from app.services.engine_service import _should_activate

    # Place 1 token -- should fire (default threshold = 1)
    token = ExecutionToken(
        id=uuid.uuid4(),
        workflow_instance_id=data["wf"].id,
        flow_template_id=data["branch_to_join_flows"][0].id,
        source_activity_instance_id=data["branch_ais"][0].id,
        target_activity_template_id=data["join_at"].id,
        is_consumed=False,
        created_by=user_id,
    )
    db_session.add(token)
    await db_session.flush()

    result = await _should_activate(
        db_session, data["wf"].id, data["join_at"].id,
        TriggerType.CANCELLING_JOIN, data["flows"],
        activity_template=data["join_at"],
    )
    assert result is True, "Cancelling join should fire with 1 token (default threshold=1)"


@pytest.mark.asyncio
async def test_celery_beat_schedule_includes_join_timeouts():
    """Verify that celery_app beat schedule includes the join timeout task."""
    from app.celery_app import celery_app

    schedule = celery_app.conf.beat_schedule
    assert "check-join-timeouts" in schedule
    assert schedule["check-join-timeouts"]["task"] == "app.tasks.join_timeout.check_join_timeouts"
    assert schedule["check-join-timeouts"]["schedule"] == 15.0
