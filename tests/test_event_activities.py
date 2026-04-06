"""Tests for event-driven activities (Phase 19).

EVTACT-01: EVENT activity type with event_type_filter and event_filter_config
EVTACT-02: EVENT activities auto-complete on matching domain events
EVTACT-03: EVENT activities ignore non-matching events and don't block parallel branches
"""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import (
    ActivityState,
    ActivityType,
    ProcessState,
    WorkflowState,
    WorkItemState,
)
from app.models.workflow import (
    ActivityInstance,
    ActivityTemplate,
    FlowTemplate,
    ProcessTemplate,
    ProcessVariable,
    WorkflowInstance,
    WorkItem,
)


# ---------------------------------------------------------------------------
# Helper to build and install a simple template via ORM (no API calls needed)
# ---------------------------------------------------------------------------


async def _create_installed_template(
    db: AsyncSession,
    name: str,
    activities_spec: list[dict],
    flows_spec: list[tuple[int, int]],
    variables: list[dict] | None = None,
    user_id: str = "test-user",
) -> dict:
    """Create, validate, and install a template directly via ORM.

    activities_spec: list of dicts with keys: name, activity_type, and optionally
        sub_template_id, variable_mapping, performer_type, performer_id, method_name,
        event_type_filter, event_filter_config
    flows_spec: list of (source_idx, target_idx) tuples referencing activities_spec indices

    Returns dict with template, activity objects, etc.
    """
    from app.services.template_service import install_template, validate_template

    template = ProcessTemplate(
        id=uuid.uuid4(),
        name=name,
        description=f"{name} template",
        version=1,
        state=ProcessState.DRAFT,
        is_installed=False,
        created_by=user_id,
    )
    db.add(template)
    await db.flush()

    activity_objs = []
    for spec in activities_spec:
        a = ActivityTemplate(
            id=uuid.uuid4(),
            process_template_id=template.id,
            name=spec["name"],
            activity_type=ActivityType(spec["activity_type"]),
            performer_type=spec.get("performer_type"),
            performer_id=spec.get("performer_id"),
            method_name=spec.get("method_name"),
            sub_template_id=spec.get("sub_template_id"),
            variable_mapping=spec.get("variable_mapping"),
            event_type_filter=spec.get("event_type_filter"),
            event_filter_config=spec.get("event_filter_config"),
            created_by=user_id,
        )
        db.add(a)
        activity_objs.append(a)
    await db.flush()

    for src_idx, tgt_idx in flows_spec:
        f = FlowTemplate(
            id=uuid.uuid4(),
            process_template_id=template.id,
            source_activity_id=activity_objs[src_idx].id,
            target_activity_id=activity_objs[tgt_idx].id,
            created_by=user_id,
        )
        db.add(f)
    await db.flush()

    if variables:
        for var_spec in variables:
            pv = ProcessVariable(
                id=uuid.uuid4(),
                process_template_id=template.id,
                name=var_spec["name"],
                variable_type=var_spec.get("variable_type", "string"),
                string_value=var_spec.get("default_value"),
                created_by=user_id,
            )
            db.add(pv)
        await db.flush()

    is_valid, errors = await validate_template(db, template.id, user_id)
    assert is_valid, f"Template validation failed: {errors}"

    await install_template(db, template.id, user_id)
    await db.flush()

    return {
        "template": template,
        "activities": activity_objs,
    }


# ---------------------------------------------------------------------------
# Task 1 Tests: Model, Schema, Validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_event_activity_template(db_session: AsyncSession):
    """EVTACT-01: Create an ActivityTemplate with type EVENT and event_type_filter."""
    template = ProcessTemplate(
        id=uuid.uuid4(),
        name="Event Process",
        description="Process with event activity",
    )
    db_session.add(template)
    await db_session.flush()

    activity = ActivityTemplate(
        id=uuid.uuid4(),
        process_template_id=template.id,
        name="Wait for Upload",
        activity_type=ActivityType.EVENT,
        event_type_filter="document.uploaded",
        event_filter_config={"document_type": "contract"},
    )
    db_session.add(activity)
    await db_session.commit()

    await db_session.refresh(activity)
    assert activity.activity_type == ActivityType.EVENT
    assert activity.event_type_filter == "document.uploaded"
    assert activity.event_filter_config == {"document_type": "contract"}


@pytest.mark.asyncio
async def test_event_activity_response_includes_fields(db_session: AsyncSession):
    """EVTACT-01: ActivityTemplateResponse includes event_type_filter and event_filter_config."""
    from app.schemas.template import ActivityTemplateResponse

    template = ProcessTemplate(
        id=uuid.uuid4(),
        name="Event Response Test",
    )
    db_session.add(template)
    await db_session.flush()

    activity = ActivityTemplate(
        id=uuid.uuid4(),
        process_template_id=template.id,
        name="Wait for Lifecycle",
        activity_type=ActivityType.EVENT,
        event_type_filter="lifecycle.changed",
        event_filter_config={"target_state": "approved"},
    )
    db_session.add(activity)
    await db_session.commit()
    await db_session.refresh(activity)

    response = ActivityTemplateResponse.model_validate(activity)
    assert response.event_type_filter == "lifecycle.changed"
    assert response.event_filter_config == {"target_state": "approved"}


@pytest.mark.asyncio
async def test_validate_event_missing_filter(db_session: AsyncSession):
    """EVTACT-01: Template validation rejects EVENT activity without event_type_filter."""
    from app.services.template_service import validate_template

    user_id = str(uuid.uuid4())

    template = ProcessTemplate(
        id=uuid.uuid4(),
        name="Invalid Event Process",
        version=1,
        state=ProcessState.DRAFT,
        is_installed=False,
        created_by=user_id,
    )
    db_session.add(template)
    await db_session.flush()

    activities = [
        ActivityTemplate(
            id=uuid.uuid4(),
            process_template_id=template.id,
            name="Start",
            activity_type=ActivityType.START,
            created_by=user_id,
        ),
        ActivityTemplate(
            id=uuid.uuid4(),
            process_template_id=template.id,
            name="Bad Event",
            activity_type=ActivityType.EVENT,
            # No event_type_filter -- should fail validation
            created_by=user_id,
        ),
        ActivityTemplate(
            id=uuid.uuid4(),
            process_template_id=template.id,
            name="End",
            activity_type=ActivityType.END,
            created_by=user_id,
        ),
    ]
    for a in activities:
        db_session.add(a)
    await db_session.flush()

    flows = [
        FlowTemplate(
            id=uuid.uuid4(),
            process_template_id=template.id,
            source_activity_id=activities[0].id,
            target_activity_id=activities[1].id,
            created_by=user_id,
        ),
        FlowTemplate(
            id=uuid.uuid4(),
            process_template_id=template.id,
            source_activity_id=activities[1].id,
            target_activity_id=activities[2].id,
            created_by=user_id,
        ),
    ]
    for f in flows:
        db_session.add(f)
    await db_session.flush()

    is_valid, errors = await validate_template(db_session, template.id, user_id)
    assert not is_valid
    error_codes = [e["code"] for e in errors]
    assert "MISSING_EVENT_TYPE" in error_codes


# ---------------------------------------------------------------------------
# Task 2 Tests: Engine Dispatch & Event Bus Handlers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_event_activity_stays_active(db_session: AsyncSession):
    """EVTACT-02: ENGINE -- when workflow reaches EVENT activity, it stays ACTIVE (no work items)."""
    from app.services.engine_service import start_workflow

    # Ensure event handlers are registered
    import app.services.event_handlers  # noqa: F401

    user_id = str(uuid.uuid4())

    data = await _create_installed_template(
        db_session,
        "Event Wait Workflow",
        [
            {"name": "Start", "activity_type": "start"},
            {"name": "Wait Upload", "activity_type": "event", "event_type_filter": "document.uploaded"},
            {"name": "End", "activity_type": "end"},
        ],
        [(0, 1), (1, 2)],
        user_id=user_id,
    )

    wf = await start_workflow(db_session, data["template"].id, user_id)
    await db_session.flush()

    # Find the EVENT activity instance
    ai_result = await db_session.execute(
        select(ActivityInstance).where(
            ActivityInstance.workflow_instance_id == wf.id
        )
    )
    all_ais = list(ai_result.scalars().all())

    event_ai = None
    for ai in all_ais:
        at_result = await db_session.execute(
            select(ActivityTemplate).where(ActivityTemplate.id == ai.activity_template_id)
        )
        at = at_result.scalar_one()
        if at.activity_type == ActivityType.EVENT:
            event_ai = ai
            break

    assert event_ai is not None
    assert event_ai.state == ActivityState.ACTIVE

    # No work items should be created for EVENT activity
    wi_result = await db_session.execute(
        select(WorkItem).where(WorkItem.activity_instance_id == event_ai.id)
    )
    work_items = list(wi_result.scalars().all())
    assert len(work_items) == 0

    # Workflow should still be RUNNING (not FINISHED)
    await db_session.refresh(wf)
    assert wf.state == WorkflowState.RUNNING


@pytest.mark.asyncio
async def test_event_activity_completes_on_document_uploaded(db_session: AsyncSession):
    """EVTACT-02: EVENT activity completes when matching document.uploaded event fires."""
    from app.services.engine_service import start_workflow
    from app.services.event_bus import event_bus

    import app.services.event_handlers  # noqa: F401

    user_id = str(uuid.uuid4())

    data = await _create_installed_template(
        db_session,
        "Doc Upload Event",
        [
            {"name": "Start", "activity_type": "start"},
            {"name": "Wait Upload", "activity_type": "event", "event_type_filter": "document.uploaded"},
            {"name": "End", "activity_type": "end"},
        ],
        [(0, 1), (1, 2)],
        user_id=user_id,
    )

    wf = await start_workflow(db_session, data["template"].id, user_id)
    await db_session.flush()

    # Emit matching event
    await event_bus.emit(
        db_session,
        event_type="document.uploaded",
        entity_type="document",
        entity_id=uuid.uuid4(),
        actor_id=uuid.UUID(user_id),
        payload={"filename": "contract.pdf"},
    )
    await db_session.flush()

    # Workflow should now be FINISHED (EVENT -> END)
    await db_session.refresh(wf)
    assert wf.state == WorkflowState.FINISHED


@pytest.mark.asyncio
async def test_event_activity_completes_on_lifecycle_changed(db_session: AsyncSession):
    """EVTACT-02: EVENT activity completes when matching lifecycle.changed event fires."""
    from app.services.engine_service import start_workflow
    from app.services.event_bus import event_bus

    import app.services.event_handlers  # noqa: F401

    user_id = str(uuid.uuid4())

    data = await _create_installed_template(
        db_session,
        "Lifecycle Event",
        [
            {"name": "Start", "activity_type": "start"},
            {"name": "Wait Lifecycle", "activity_type": "event", "event_type_filter": "lifecycle.changed"},
            {"name": "End", "activity_type": "end"},
        ],
        [(0, 1), (1, 2)],
        user_id=user_id,
    )

    wf = await start_workflow(db_session, data["template"].id, user_id)
    await db_session.flush()

    await event_bus.emit(
        db_session,
        event_type="lifecycle.changed",
        entity_type="document",
        entity_id=uuid.uuid4(),
        actor_id=uuid.UUID(user_id),
        payload={"new_state": "approved"},
    )
    await db_session.flush()

    await db_session.refresh(wf)
    assert wf.state == WorkflowState.FINISHED


@pytest.mark.asyncio
async def test_event_activity_completes_on_workflow_completed(db_session: AsyncSession):
    """EVTACT-02: EVENT activity completes when matching workflow.completed event fires."""
    from app.services.engine_service import start_workflow
    from app.services.event_bus import event_bus

    import app.services.event_handlers  # noqa: F401

    user_id = str(uuid.uuid4())

    data = await _create_installed_template(
        db_session,
        "WF Complete Event",
        [
            {"name": "Start", "activity_type": "start"},
            {"name": "Wait WF Done", "activity_type": "event", "event_type_filter": "workflow.completed"},
            {"name": "End", "activity_type": "end"},
        ],
        [(0, 1), (1, 2)],
        user_id=user_id,
    )

    wf = await start_workflow(db_session, data["template"].id, user_id)
    await db_session.flush()

    # Emit workflow.completed for some other workflow
    await event_bus.emit(
        db_session,
        event_type="workflow.completed",
        entity_type="workflow_instance",
        entity_id=uuid.uuid4(),  # some other workflow
        actor_id=uuid.UUID(user_id),
        payload={"template_name": "Other Workflow"},
    )
    await db_session.flush()

    await db_session.refresh(wf)
    assert wf.state == WorkflowState.FINISHED


@pytest.mark.asyncio
async def test_event_activity_ignores_non_matching_event(db_session: AsyncSession):
    """EVTACT-03: EVENT activity ignores events of a different type."""
    from app.services.engine_service import start_workflow
    from app.services.event_bus import event_bus

    import app.services.event_handlers  # noqa: F401

    user_id = str(uuid.uuid4())

    data = await _create_installed_template(
        db_session,
        "Ignore Mismatch",
        [
            {"name": "Start", "activity_type": "start"},
            {"name": "Wait Upload", "activity_type": "event", "event_type_filter": "document.uploaded"},
            {"name": "End", "activity_type": "end"},
        ],
        [(0, 1), (1, 2)],
        user_id=user_id,
    )

    wf = await start_workflow(db_session, data["template"].id, user_id)
    await db_session.flush()

    # Emit lifecycle.changed -- should NOT complete the document.uploaded listener
    await event_bus.emit(
        db_session,
        event_type="lifecycle.changed",
        entity_type="document",
        entity_id=uuid.uuid4(),
        actor_id=uuid.UUID(user_id),
        payload={"new_state": "approved"},
    )
    await db_session.flush()

    await db_session.refresh(wf)
    assert wf.state == WorkflowState.RUNNING  # Still waiting


@pytest.mark.asyncio
async def test_event_activity_filter_config_matching(db_session: AsyncSession):
    """EVTACT-02: EVENT with event_filter_config only completes when payload matches filter."""
    from app.services.engine_service import start_workflow
    from app.services.event_bus import event_bus

    import app.services.event_handlers  # noqa: F401

    user_id = str(uuid.uuid4())

    data = await _create_installed_template(
        db_session,
        "Filter Config",
        [
            {"name": "Start", "activity_type": "start"},
            {
                "name": "Wait Approved",
                "activity_type": "event",
                "event_type_filter": "lifecycle.changed",
                "event_filter_config": {"new_state": "approved"},
            },
            {"name": "End", "activity_type": "end"},
        ],
        [(0, 1), (1, 2)],
        user_id=user_id,
    )

    wf = await start_workflow(db_session, data["template"].id, user_id)
    await db_session.flush()

    # Emit lifecycle.changed but with non-matching payload
    await event_bus.emit(
        db_session,
        event_type="lifecycle.changed",
        entity_type="document",
        entity_id=uuid.uuid4(),
        actor_id=uuid.UUID(user_id),
        payload={"new_state": "draft"},  # Does NOT match filter
    )
    await db_session.flush()

    await db_session.refresh(wf)
    assert wf.state == WorkflowState.RUNNING  # Still waiting

    # Emit lifecycle.changed with matching payload
    await event_bus.emit(
        db_session,
        event_type="lifecycle.changed",
        entity_type="document",
        entity_id=uuid.uuid4(),
        actor_id=uuid.UUID(user_id),
        payload={"new_state": "approved"},  # Matches filter
    )
    await db_session.flush()

    await db_session.refresh(wf)
    assert wf.state == WorkflowState.FINISHED


@pytest.mark.asyncio
async def test_event_activity_does_not_block_parallel_branches(db_session: AsyncSession):
    """EVTACT-03: EVENT activity in parallel branch doesn't block other branches."""
    from app.services.engine_service import complete_work_item, start_workflow
    from app.services.event_bus import event_bus

    import app.services.event_handlers  # noqa: F401

    user_id = str(uuid.uuid4())

    # Build: START -> [EVENT (document.uploaded), MANUAL] -> (AND-join) MANUAL_MERGE -> END
    template = ProcessTemplate(
        id=uuid.uuid4(),
        name="Parallel Event",
        version=1,
        state=ProcessState.DRAFT,
        is_installed=False,
        created_by=user_id,
    )
    db_session.add(template)
    await db_session.flush()

    acts = []
    for spec in [
        {"name": "Start", "activity_type": ActivityType.START},
        {"name": "Wait Upload", "activity_type": ActivityType.EVENT, "event_type_filter": "document.uploaded"},
        {"name": "Manual Review", "activity_type": ActivityType.MANUAL, "performer_type": "user", "performer_id": user_id},
        {"name": "Merge", "activity_type": ActivityType.MANUAL, "performer_type": "user", "performer_id": user_id, "trigger_type": "and_join"},
        {"name": "End", "activity_type": ActivityType.END},
    ]:
        from app.models.enums import TriggerType
        a = ActivityTemplate(
            id=uuid.uuid4(),
            process_template_id=template.id,
            name=spec["name"],
            activity_type=spec["activity_type"] if isinstance(spec["activity_type"], ActivityType) else ActivityType(spec["activity_type"]),
            performer_type=spec.get("performer_type"),
            performer_id=spec.get("performer_id"),
            event_type_filter=spec.get("event_type_filter"),
            trigger_type=TriggerType(spec["trigger_type"]) if spec.get("trigger_type") else TriggerType.OR_JOIN,
            created_by=user_id,
        )
        db_session.add(a)
        acts.append(a)
    await db_session.flush()

    # Flows: Start->WaitUpload, Start->ManualReview, WaitUpload->Merge, ManualReview->Merge, Merge->End
    flow_specs = [(0, 1), (0, 2), (1, 3), (2, 3), (3, 4)]
    for src, tgt in flow_specs:
        f = FlowTemplate(
            id=uuid.uuid4(),
            process_template_id=template.id,
            source_activity_id=acts[src].id,
            target_activity_id=acts[tgt].id,
            created_by=user_id,
        )
        db_session.add(f)
    await db_session.flush()

    from app.services.template_service import install_template, validate_template
    is_valid, errors = await validate_template(db_session, template.id, user_id)
    assert is_valid, f"Validation failed: {errors}"
    await install_template(db_session, template.id, user_id)
    await db_session.flush()

    # Start the workflow
    wf = await start_workflow(db_session, template.id, user_id)
    await db_session.flush()

    # Check both branches are active
    ai_result = await db_session.execute(
        select(ActivityInstance).where(
            ActivityInstance.workflow_instance_id == wf.id
        )
    )
    all_ais = list(ai_result.scalars().all())

    # Find the manual review work item and complete it
    wi_result = await db_session.execute(
        select(WorkItem)
        .join(ActivityInstance)
        .where(ActivityInstance.workflow_instance_id == wf.id)
    )
    work_items = list(wi_result.scalars().all())
    assert len(work_items) >= 1  # Manual review has a work item

    manual_wi = work_items[0]
    manual_wi.state = WorkItemState.ACQUIRED
    await db_session.flush()

    await complete_work_item(db_session, wf.id, manual_wi.id, user_id)
    await db_session.flush()

    # Workflow should still be RUNNING because the EVENT branch hasn't completed
    await db_session.refresh(wf)
    assert wf.state == WorkflowState.RUNNING

    # Now emit the matching event to complete the EVENT branch
    await event_bus.emit(
        db_session,
        event_type="document.uploaded",
        entity_type="document",
        entity_id=uuid.uuid4(),
        actor_id=uuid.UUID(user_id),
        payload={"filename": "doc.pdf"},
    )
    await db_session.flush()

    # Now both branches are complete, AND-join should fire, Merge gets work item
    # Find and complete the Merge work item
    wi_result2 = await db_session.execute(
        select(WorkItem)
        .join(ActivityInstance)
        .where(
            ActivityInstance.workflow_instance_id == wf.id,
            WorkItem.state != WorkItemState.COMPLETE,
        )
    )
    merge_wis = list(wi_result2.scalars().all())
    assert len(merge_wis) >= 1

    merge_wi = merge_wis[0]
    merge_wi.state = WorkItemState.ACQUIRED
    await db_session.flush()

    await complete_work_item(db_session, wf.id, merge_wi.id, user_id)
    await db_session.flush()

    # Now workflow should be FINISHED
    await db_session.refresh(wf)
    assert wf.state == WorkflowState.FINISHED
