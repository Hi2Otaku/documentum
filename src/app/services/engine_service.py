"""Core process engine service.

Implements workflow instantiation from installed templates, iterative token-based
advancement through sequential and parallel paths, work item creation for manual
activities, and expression-based conditional routing.
"""
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import (
    ActivityState,
    ActivityType,
    FlowType,
    TriggerType,
    WorkflowState,
    WorkItemState,
)
from app.models.workflow import (
    ActivityInstance,
    ActivityTemplate,
    ExecutionToken,
    FlowTemplate,
    ProcessTemplate,
    ProcessVariable,
    WorkflowInstance,
    WorkflowPackage,
    WorkItem,
)
from app.core.config import settings
from app.services.audit_service import create_audit_record
from app.services.event_bus import event_bus
from app.services.expression_evaluator import evaluate_expression

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Section 1: State transition maps and enforcement (per D-07, D-09)
# ---------------------------------------------------------------------------

WORKFLOW_TRANSITIONS: set[tuple[WorkflowState, WorkflowState]] = {
    (WorkflowState.DORMANT, WorkflowState.RUNNING),
    (WorkflowState.RUNNING, WorkflowState.HALTED),
    (WorkflowState.RUNNING, WorkflowState.FAILED),
    (WorkflowState.RUNNING, WorkflowState.FINISHED),
    (WorkflowState.HALTED, WorkflowState.RUNNING),
    (WorkflowState.HALTED, WorkflowState.FAILED),
    (WorkflowState.FAILED, WorkflowState.DORMANT),
}

ACTIVITY_TRANSITIONS: set[tuple[ActivityState, ActivityState]] = {
    (ActivityState.DORMANT, ActivityState.ACTIVE),
    (ActivityState.ACTIVE, ActivityState.COMPLETE),
    (ActivityState.ACTIVE, ActivityState.PAUSED),
    (ActivityState.ACTIVE, ActivityState.ERROR),
    (ActivityState.PAUSED, ActivityState.ACTIVE),
    (ActivityState.ERROR, ActivityState.ACTIVE),
    (ActivityState.COMPLETE, ActivityState.ACTIVE),  # Reject flow reactivation (D-04)
}

WORK_ITEM_TRANSITIONS: set[tuple[WorkItemState, WorkItemState]] = {
    (WorkItemState.AVAILABLE, WorkItemState.ACQUIRED),
    (WorkItemState.ACQUIRED, WorkItemState.AVAILABLE),
    (WorkItemState.ACQUIRED, WorkItemState.COMPLETE),
    (WorkItemState.ACQUIRED, WorkItemState.REJECTED),
    (WorkItemState.AVAILABLE, WorkItemState.SUSPENDED),
    (WorkItemState.ACQUIRED, WorkItemState.SUSPENDED),
    (WorkItemState.SUSPENDED, WorkItemState.AVAILABLE),
}


def _enforce_workflow_transition(
    current: WorkflowState, target: WorkflowState
) -> None:
    """Raise ValueError on invalid workflow state transition."""
    if (current, target) not in WORKFLOW_TRANSITIONS:
        raise ValueError(
            f"Invalid state transition: {current.value} -> {target.value}"
        )


def _enforce_activity_transition(
    current: ActivityState, target: ActivityState
) -> None:
    """Raise ValueError on invalid activity state transition."""
    if (current, target) not in ACTIVITY_TRANSITIONS:
        raise ValueError(
            f"Invalid state transition: {current.value} -> {target.value}"
        )


# ---------------------------------------------------------------------------
# Section 2: Variable resolution helper
# ---------------------------------------------------------------------------


def _resolve_variable_value(pv: ProcessVariable) -> Any:
    """Extract typed value from ProcessVariable based on variable_type."""
    match pv.variable_type:
        case "string":
            return pv.string_value
        case "int":
            return pv.int_value
        case "boolean":
            return pv.bool_value
        case "date":
            return pv.date_value
        case _:
            return pv.string_value


def _build_variable_context(variables: list[ProcessVariable]) -> dict[str, Any]:
    """Build a dict of variable name -> resolved value for expression evaluation."""
    return {pv.name: _resolve_variable_value(pv) for pv in variables}


def _set_variable_value(pv: ProcessVariable, value: Any) -> None:
    """Set the correct typed column on a ProcessVariable based on its variable_type."""
    match pv.variable_type:
        case "string":
            pv.string_value = str(value) if value is not None else None
        case "int":
            pv.int_value = int(value) if value is not None else None
        case "boolean":
            pv.bool_value = bool(value) if value is not None else None
        case "date":
            pv.date_value = value
        case _:
            pv.string_value = str(value) if value is not None else None


# ---------------------------------------------------------------------------
# Section 2b-0: Due date computation (Phase 17 - Timer/Escalation)
# ---------------------------------------------------------------------------


def _compute_due_date(activity_template) -> datetime | None:
    """Calculate work item due date from activity template deadline config."""
    if activity_template and activity_template.expected_duration_hours is not None:
        return datetime.now(timezone.utc) + timedelta(
            hours=activity_template.expected_duration_hours
        )
    return None


# ---------------------------------------------------------------------------
# Section 2b: Performer resolution (per D-07)
# ---------------------------------------------------------------------------


async def resolve_performers(
    db: AsyncSession,
    performer_type: str | None,
    performer_id: str | None,
    workflow: WorkflowInstance,
) -> list[uuid.UUID]:
    """Resolve performer config to actual user IDs (per D-07).

    SUPERVISOR -> workflow.supervisor_id
    USER -> specific user UUID from performer_id
    GROUP -> all members of group via user_groups table
    """
    if not performer_type:
        return []
    match performer_type.lower():
        case "supervisor":
            if workflow.supervisor_id:
                return [workflow.supervisor_id]
            return []
        case "user":
            if performer_id:
                return [uuid.UUID(performer_id)]
            return []
        case "group":
            if not performer_id:
                return []
            from app.models.user import user_groups
            result = await db.execute(
                select(user_groups.c.user_id).where(
                    user_groups.c.group_id == uuid.UUID(performer_id)
                )
            )
            return [row[0] for row in result.all()]
        case "alias":
            if not performer_id:
                return []
            snapshot = getattr(workflow, 'alias_snapshot', None) or {}
            target_id = snapshot.get(performer_id)
            if target_id:
                return [uuid.UUID(target_id)]
            return []
        case "queue":
            # Queue items use special creation path -- return empty list
            # The caller creates ONE work item with performer_id=None and queue_id set
            return []
        case "sequential":
            # Handled specially in advancement loop (initial work item creation)
            return []
        case "runtime_selection":
            # Handled via next_performer_id in completion
            return []
        case _:
            return []


async def _apply_delegation(
    db: AsyncSession,
    user_ids: list[uuid.UUID],
    user_id_for_audit: str,
    workflow_instance_id: uuid.UUID | None = None,
) -> list[uuid.UUID]:
    """Replace unavailable users with their delegates (one level only per anti-pattern rule)."""
    if not user_ids:
        return user_ids
    from app.models.user import User
    result = await db.execute(
        select(User).where(User.id.in_(user_ids))
    )
    users_map = {u.id: u for u in result.scalars().all()}
    resolved = []
    for uid in user_ids:
        user = users_map.get(uid)
        if user and not user.is_available and user.delegate_id:
            resolved.append(user.delegate_id)
            await create_audit_record(
                db,
                entity_type="work_item",
                entity_id="",
                action="work_item_delegated",
                user_id=user_id_for_audit,
                after_state={
                    "original_performer": str(uid),
                    "delegated_to": str(user.delegate_id),
                    "workflow_instance_id": str(workflow_instance_id),
                },
            )
            await event_bus.emit(
                db,
                event_type="work_item.delegated",
                entity_type="work_item",
                entity_id=None,
                actor_id=uuid.UUID(user_id_for_audit) if user_id_for_audit else None,
                payload={
                    "original_performer": str(uid),
                    "delegate_id": str(user.delegate_id),
                    "workflow_instance_id": str(workflow_instance_id),
                },
            )
        else:
            resolved.append(uid)
    return resolved


# ---------------------------------------------------------------------------
# Section 3: start_workflow (per D-06: immediate start)
# ---------------------------------------------------------------------------


async def start_workflow(
    db: AsyncSession,
    template_id: uuid.UUID,
    user_id: str,
    document_ids: list[uuid.UUID] | None = None,
    performer_overrides: dict[str, str] | None = None,
    initial_variables: dict[str, Any] | None = None,
) -> WorkflowInstance:
    """Start a new workflow instance from an installed template.

    Creates the instance, activity instances, copies variables, attaches
    documents, then auto-advances through the start activity.
    """
    # 1. Load installed template with relations
    result = await db.execute(
        select(ProcessTemplate)
        .options(
            selectinload(ProcessTemplate.activity_templates),
            selectinload(ProcessTemplate.flow_templates),
            selectinload(ProcessTemplate.process_variables),
        )
        .where(
            ProcessTemplate.id == template_id,
            ProcessTemplate.is_deleted == False,  # noqa: E712
        )
    )
    template = result.scalar_one_or_none()
    if template is None or not template.is_installed:
        raise ValueError("Template not found or not installed")

    # 2. Create WorkflowInstance
    now = datetime.now(timezone.utc)
    instance = WorkflowInstance(
        process_template_id=template.id,
        state=WorkflowState.RUNNING,
        started_at=now,
        supervisor_id=uuid.UUID(user_id),
        created_by=user_id,
    )
    db.add(instance)
    await db.flush()

    # 3. Resolve alias snapshot at workflow start (D-06)
    if template.alias_set_id:
        from app.services import alias_service
        snapshot = await alias_service.resolve_alias_snapshot(db, template.alias_set_id)
        if performer_overrides:
            for alias_name, override_id in performer_overrides.items():
                if alias_name in snapshot:
                    snapshot[alias_name] = override_id
        instance.alias_snapshot = snapshot

    # 4. Create ActivityInstance for each ActivityTemplate
    template_to_instance: dict[uuid.UUID, ActivityInstance] = {}
    for at in template.activity_templates:
        if at.is_deleted:
            continue
        ai = ActivityInstance(
            workflow_instance_id=instance.id,
            activity_template_id=at.id,
            state=ActivityState.DORMANT,
            created_by=user_id,
        )
        db.add(ai)
        template_to_instance[at.id] = ai

    # 5. Copy ProcessVariables from template to instance
    instance_variables: list[ProcessVariable] = []
    for tv in template.process_variables:
        if tv.is_deleted:
            continue
        pv = ProcessVariable(
            workflow_instance_id=instance.id,
            process_template_id=None,
            name=tv.name,
            variable_type=tv.variable_type,
            string_value=tv.string_value,
            int_value=tv.int_value,
            bool_value=tv.bool_value,
            date_value=tv.date_value,
            created_by=user_id,
        )
        # Apply initial_variables overrides
        if initial_variables and tv.name in initial_variables:
            _set_variable_value(pv, initial_variables[tv.name])
        db.add(pv)
        instance_variables.append(pv)

    # 6. Create WorkflowPackage for each document_id
    if document_ids:
        for doc_id in document_ids:
            pkg = WorkflowPackage(
                workflow_instance_id=instance.id,
                document_id=doc_id,
                created_by=user_id,
            )
            db.add(pkg)

    # 7. Flush to get all IDs
    await db.flush()

    # 8. Find start activity template
    start_template = None
    for at in template.activity_templates:
        if not at.is_deleted and at.activity_type == ActivityType.START:
            start_template = at
            break
    if start_template is None:
        raise ValueError("Template has no start activity")

    # 9. Advance from start activity
    await _advance_from_activity(
        db,
        instance,
        template_to_instance[start_template.id],
        template,
        template_to_instance,
        user_id,
        performer_overrides=performer_overrides,
        instance_variables=instance_variables,
    )

    # 10. Create audit record
    await create_audit_record(
        db,
        entity_type="workflow_instance",
        entity_id=str(instance.id),
        action="workflow_started",
        user_id=user_id,
        after_state={
            "template_id": str(template.id),
            "template_name": template.name,
            "state": instance.state.value,
        },
    )

    # 11. Emit domain event
    await event_bus.emit(
        db,
        event_type="workflow.started",
        entity_type="workflow_instance",
        entity_id=instance.id,
        actor_id=uuid.UUID(user_id),
        payload={
            "template_id": str(template.id),
            "template_name": template.name,
        },
    )

    return instance


# ---------------------------------------------------------------------------
# Section 4: _advance_from_activity -- iterative loop (per D-03)
# ---------------------------------------------------------------------------


async def _advance_from_activity(
    db: AsyncSession,
    workflow: WorkflowInstance,
    completed_activity: ActivityInstance,
    template: ProcessTemplate,
    template_to_instance: dict[uuid.UUID, ActivityInstance],
    user_id: str,
    performer_overrides: dict[str, str] | None = None,
    instance_variables: list[ProcessVariable] | None = None,
    selected_path: str | None = None,
    next_performer_id: str | None = None,
) -> None:
    """Iterative advancement loop using token-based Petri-net model.

    Marks the completed activity as COMPLETE, then processes outgoing flows,
    placing tokens and activating target activities when join conditions are met.
    Uses a queue for breadth-first traversal (no recursion per D-03).
    """
    now = datetime.now(timezone.utc)

    # Mark completed activity
    if completed_activity.state == ActivityState.DORMANT:
        _enforce_activity_transition(completed_activity.state, ActivityState.ACTIVE)
        completed_activity.state = ActivityState.ACTIVE
    _enforce_activity_transition(completed_activity.state, ActivityState.COMPLETE)
    completed_activity.state = ActivityState.COMPLETE
    completed_activity.completed_at = now
    if completed_activity.started_at is None:
        completed_activity.started_at = now

    # Lifecycle action hook (Phase 7) — per D-11: fires after completion, before advancing
    current_at_for_lifecycle = None
    for at in template.activity_templates:
        if not at.is_deleted and at.id == completed_activity.activity_template_id:
            current_at_for_lifecycle = at
            break

    if current_at_for_lifecycle and getattr(current_at_for_lifecycle, 'lifecycle_action', None):
        try:
            from app.services import lifecycle_service
            await lifecycle_service.execute_lifecycle_action(
                db, workflow, current_at_for_lifecycle.lifecycle_action, user_id
            )
        except Exception:
            logger.warning(
                "Lifecycle action failed for activity %s, continuing advancement",
                completed_activity.id,
            )

    # Build variable context for condition evaluation
    variables = instance_variables if instance_variables is not None else workflow.process_variables
    var_context = _build_variable_context(variables)

    # Build activity template map for lookups
    activity_template_map: dict[uuid.UUID, ActivityTemplate] = {
        at.id: at
        for at in template.activity_templates
        if not at.is_deleted
    }

    queue: list[ActivityInstance] = [completed_activity]
    _created_work_items: list[WorkItem] = []  # Track for event emission

    while queue:
        current = queue.pop(0)

        # If already in terminal state (workflow finished), stop processing
        if workflow.state == WorkflowState.FINISHED:
            break

        # Get outgoing NORMAL flows from current activity's template
        outgoing_flows = [
            f
            for f in template.flow_templates
            if not f.is_deleted
            and f.source_activity_id == current.activity_template_id
            and f.flow_type == FlowType.NORMAL
        ]

        # Routing type dispatch (D-02)
        current_at = activity_template_map.get(current.activity_template_id)
        routing_type = getattr(current_at, 'routing_type', None) or "conditional"

        match routing_type:
            case "broadcast":
                flows_to_fire = outgoing_flows  # Fire ALL, ignore conditions
            case "performer_chosen":
                if not selected_path:
                    raise ValueError("Performer-chosen activity requires selected_path")
                flows_to_fire = [f for f in outgoing_flows if f.display_label == selected_path]
                if not flows_to_fire:
                    raise ValueError(f"No flow with label '{selected_path}'")
            case "conditional" | _:
                # Existing behavior: evaluate condition_expression
                flows_to_fire = []
                for flow in outgoing_flows:
                    if flow.condition_expression:
                        try:
                            if not evaluate_expression(flow.condition_expression, var_context):
                                continue
                        except Exception:
                            logger.warning(
                                "Condition evaluation failed for flow %s, skipping",
                                flow.id,
                            )
                            continue
                    flows_to_fire.append(flow)

        # After first activity in queue, clear selected_path so subsequent
        # auto-completing activities use default routing
        selected_path = None

        any_flow_fired = False

        for flow in flows_to_fire:
            any_flow_fired = True

            # Place token
            token = ExecutionToken(
                workflow_instance_id=workflow.id,
                flow_template_id=flow.id,
                source_activity_instance_id=current.id,
                target_activity_template_id=flow.target_activity_id,
                is_consumed=False,
                created_by=user_id,
            )
            db.add(token)
            await db.flush()

            # Check if target should activate
            target_at = activity_template_map.get(flow.target_activity_id)
            if target_at is None:
                continue

            should_fire = await _should_activate(
                db,
                workflow.id,
                flow.target_activity_id,
                target_at.trigger_type,
                template.flow_templates,
            )

            if should_fire:
                target_ai = template_to_instance.get(flow.target_activity_id)
                if target_ai is None:
                    continue

                # OR-join double-activation guard: only activate DORMANT targets
                if target_ai.state != ActivityState.DORMANT:
                    logger.debug(
                        "Skipping activation of %s: already %s",
                        target_ai.activity_template_id,
                        target_ai.state.value,
                    )
                    continue

                # Consume all unconsumed tokens for this target
                token_result = await db.execute(
                    select(ExecutionToken).where(
                        ExecutionToken.workflow_instance_id == workflow.id,
                        ExecutionToken.target_activity_template_id == flow.target_activity_id,
                        ExecutionToken.is_consumed == False,  # noqa: E712
                    )
                )
                for t in token_result.scalars().all():
                    t.is_consumed = True

                # Activate target
                target_ai.state = ActivityState.ACTIVE
                target_ai.started_at = datetime.now(timezone.utc)

                # Handle by activity type
                if target_at.activity_type in (ActivityType.START, ActivityType.END):
                    # Auto-complete start/end activities
                    target_ai.state = ActivityState.COMPLETE
                    target_ai.completed_at = datetime.now(timezone.utc)
                    queue.append(target_ai)

                elif target_at.activity_type == ActivityType.AUTO:
                    # Leave as ACTIVE for Celery Workflow Agent to pick up (per D-04).
                    # Do NOT auto-complete and do NOT create work items.
                    # The poll task in Plan 02 will find ACTIVE AUTO activities
                    # and dispatch them as Celery tasks.
                    pass

                elif target_at.activity_type == ActivityType.EVENT:
                    # Leave as ACTIVE -- event bus handler will complete when matching event fires.
                    # No work items created, no Celery task dispatched.
                    pass

                elif target_at.activity_type == ActivityType.SUB_WORKFLOW:
                    # Resolve variable mapping from parent to child
                    variable_mapping = target_at.variable_mapping or {}
                    child_initial_vars: dict[str, Any] = {}
                    for parent_var, child_var in variable_mapping.items():
                        parent_val = var_context.get(parent_var)
                        if parent_val is not None:
                            child_initial_vars[child_var] = parent_val

                    # Check runtime depth limit
                    current_depth = workflow.nesting_depth or 0
                    max_depth = settings.max_sub_workflow_depth
                    if current_depth + 1 > max_depth:
                        target_ai.state = ActivityState.ERROR
                        logger.error(
                            "Sub-workflow depth limit exceeded: depth=%d, max=%d",
                            current_depth, max_depth,
                        )
                        continue

                    # Spawn child workflow
                    child_wf = await start_workflow(
                        db,
                        target_at.sub_template_id,
                        user_id,
                        initial_variables=child_initial_vars if child_initial_vars else None,
                    )
                    child_wf.parent_workflow_id = workflow.id
                    child_wf.parent_activity_instance_id = target_ai.id
                    child_wf.nesting_depth = current_depth + 1
                    # Parent activity stays ACTIVE -- event handler resumes it

                elif target_at.activity_type == ActivityType.MANUAL:
                    # Per D-06/D-07: resolve performers then create one work item per performer
                    # Special handling for sequential, runtime_selection, and queue
                    if target_at.performer_type == "queue" and target_at.performer_id:
                        # Queue: create ONE work item with performer_id=None and queue_id set
                        work_item = WorkItem(
                            activity_instance_id=target_ai.id,
                            performer_id=None,
                            queue_id=uuid.UUID(target_at.performer_id),
                            state=WorkItemState.AVAILABLE,
                            created_by=user_id,
                            due_date=_compute_due_date(target_at),
                        )
                        db.add(work_item)
                    elif target_at.performer_type == "sequential":
                        performer_list = target_at.performer_list or []
                        if performer_list:
                            target_ai.current_performer_index = 0
                            performers = [uuid.UUID(performer_list[0])]
                        else:
                            performers = [None]
                        # Apply delegation for sequential performers
                        performers = await _apply_delegation(
                            db, [p for p in performers if p is not None],
                            user_id, workflow.id,
                        ) or performers
                        for perf_id in performers:
                            work_item = WorkItem(
                                activity_instance_id=target_ai.id,
                                performer_id=perf_id,
                                state=WorkItemState.AVAILABLE,
                                created_by=user_id,
                                due_date=_compute_due_date(target_at),
                            )
                            db.add(work_item)
                    elif target_at.performer_type == "runtime_selection" and next_performer_id:
                        performers = [uuid.UUID(next_performer_id)]
                        next_performer_id = None  # Consumed, don't carry forward
                        # Apply delegation
                        performers = await _apply_delegation(db, performers, user_id, workflow.id)
                        for perf_id in performers:
                            work_item = WorkItem(
                                activity_instance_id=target_ai.id,
                                performer_id=perf_id,
                                state=WorkItemState.AVAILABLE,
                                created_by=user_id,
                                due_date=_compute_due_date(target_at),
                            )
                            db.add(work_item)
                    else:
                        performers = await resolve_performers(
                            db, target_at.performer_type, target_at.performer_id, workflow
                        )
                        # Check performer_overrides first
                        if performer_overrides and str(target_at.id) in performer_overrides:
                            performers = [uuid.UUID(performer_overrides[str(target_at.id)])]
                        # Apply delegation to resolved performers
                        if performers:
                            performers = await _apply_delegation(db, performers, user_id, workflow.id)
                        # If no performers resolved, create unassigned work item
                        if not performers:
                            performers = [None]
                        for perf_id in performers:
                            work_item = WorkItem(
                                activity_instance_id=target_ai.id,
                                performer_id=perf_id,
                                state=WorkItemState.AVAILABLE,
                                created_by=user_id,
                                due_date=_compute_due_date(target_at),
                            )
                            db.add(work_item)

        # If no flows fired and current is END type, mark workflow FINISHED
        if not any_flow_fired:
            current_at = activity_template_map.get(current.activity_template_id)
            if current_at and current_at.activity_type == ActivityType.END:
                _enforce_workflow_transition(workflow.state, WorkflowState.FINISHED)
                workflow.state = WorkflowState.FINISHED
                workflow.completed_at = datetime.now(timezone.utc)

    await db.flush()

    # Emit work_item.assigned events for all work items created during advancement.
    # Query for AVAILABLE work items on activity instances that were just activated.
    from sqlalchemy import and_
    new_wi_result = await db.execute(
        select(WorkItem).join(ActivityInstance).where(
            and_(
                ActivityInstance.workflow_instance_id == workflow.id,
                WorkItem.state == WorkItemState.AVAILABLE,
                WorkItem.performer_id.isnot(None),
                WorkItem.created_at >= workflow.updated_at,
            )
        )
    )
    for wi in new_wi_result.scalars().all():
        try:
            # Look up activity name for a better notification message
            at_result = await db.execute(
                select(ActivityTemplate).where(
                    ActivityTemplate.id == ActivityInstance.__table__.c.activity_template_id
                ).where(ActivityInstance.id == wi.activity_instance_id)
            )
            at_row = at_result.scalar_one_or_none()
            activity_name = at_row.name if at_row else "Unknown activity"
        except Exception:
            activity_name = "Unknown activity"

        await event_bus.emit(
            db,
            event_type="work_item.assigned",
            entity_type="work_item",
            entity_id=wi.id,
            actor_id=uuid.UUID(user_id) if user_id else None,
            payload={
                "performer_id": str(wi.performer_id),
                "workflow_id": str(workflow.id),
                "activity_name": activity_name,
            },
        )


# ---------------------------------------------------------------------------
# Section 5: _should_activate -- token check (per D-02)
# ---------------------------------------------------------------------------


async def _should_activate(
    db: AsyncSession,
    workflow_id: uuid.UUID,
    target_activity_template_id: uuid.UUID,
    trigger_type: TriggerType,
    flow_templates: list[FlowTemplate],
) -> bool:
    """Check whether a target activity should be activated based on token count.

    AND-join: requires tokens from ALL incoming flows.
    OR-join: requires at least 1 token.
    """
    # Count incoming NORMAL flows for the target
    incoming_flows = [
        f
        for f in flow_templates
        if not f.is_deleted
        and f.target_activity_id == target_activity_template_id
        and f.flow_type == FlowType.NORMAL
    ]

    # Count unconsumed tokens targeting this activity
    result = await db.execute(
        select(func.count()).select_from(ExecutionToken).where(
            ExecutionToken.workflow_instance_id == workflow_id,
            ExecutionToken.target_activity_template_id == target_activity_template_id,
            ExecutionToken.is_consumed == False,  # noqa: E712
        )
    )
    token_count = result.scalar_one()

    if trigger_type == TriggerType.AND_JOIN:
        return token_count >= len(incoming_flows)
    else:  # OR_JOIN
        return token_count >= 1


# ---------------------------------------------------------------------------
# Section 6: complete_work_item
# ---------------------------------------------------------------------------


async def complete_work_item(
    db: AsyncSession,
    workflow_id: uuid.UUID,
    work_item_id: uuid.UUID,
    user_id: str,
    output_variables: dict[str, Any] | None = None,
    selected_path: str | None = None,
    next_performer_id: str | None = None,
) -> WorkItem:
    """Complete a work item and advance the workflow.

    Marks the work item as complete, optionally updates process variables,
    then triggers the advancement loop from the completed activity.
    """
    # 1. Load workflow instance
    wf_result = await db.execute(
        select(WorkflowInstance).where(
            WorkflowInstance.id == workflow_id,
            WorkflowInstance.is_deleted == False,  # noqa: E712
        )
    )
    workflow = wf_result.scalar_one_or_none()
    if workflow is None:
        raise ValueError("Workflow not found")
    if workflow.state != WorkflowState.RUNNING:
        raise ValueError("Workflow is not running")

    # 2. Load work item with activity instance
    wi_result = await db.execute(
        select(WorkItem)
        .options(selectinload(WorkItem.activity_instance))
        .where(
            WorkItem.id == work_item_id,
            WorkItem.is_deleted == False,  # noqa: E712
        )
    )
    work_item = wi_result.scalar_one_or_none()
    if work_item is None:
        raise ValueError("Work item not found")
    if work_item.state == WorkItemState.COMPLETE:
        raise ValueError("Work item is already complete")

    # 3. Mark work item complete
    work_item.state = WorkItemState.COMPLETE
    work_item.completed_at = datetime.now(timezone.utc)

    # 4. Update output variables if provided
    if output_variables:
        var_result = await db.execute(
            select(ProcessVariable).where(
                ProcessVariable.workflow_instance_id == workflow_id,
                ProcessVariable.is_deleted == False,  # noqa: E712
            )
        )
        instance_vars = list(var_result.scalars().all())
        var_map = {v.name: v for v in instance_vars}
        for var_name, var_value in output_variables.items():
            if var_name in var_map:
                _set_variable_value(var_map[var_name], var_value)

    # 5. Load full template with relations and rebuild mapping
    template_result = await db.execute(
        select(ProcessTemplate)
        .options(
            selectinload(ProcessTemplate.activity_templates),
            selectinload(ProcessTemplate.flow_templates),
            selectinload(ProcessTemplate.process_variables),
        )
        .where(ProcessTemplate.id == workflow.process_template_id)
    )
    template = template_result.scalar_one()

    # Rebuild template_to_instance mapping
    ai_result = await db.execute(
        select(ActivityInstance).where(
            ActivityInstance.workflow_instance_id == workflow_id
        )
    )
    all_instances = list(ai_result.scalars().all())
    template_to_instance: dict[uuid.UUID, ActivityInstance] = {
        ai.activity_template_id: ai for ai in all_instances
    }

    # Reload workflow process variables
    pv_result = await db.execute(
        select(ProcessVariable).where(
            ProcessVariable.workflow_instance_id == workflow_id,
            ProcessVariable.is_deleted == False,  # noqa: E712
        )
    )
    current_variables = list(pv_result.scalars().all())

    # Build activity template map for sequential/runtime checks
    activity_template_map: dict[uuid.UUID, ActivityTemplate] = {
        at.id: at for at in template.activity_templates if not at.is_deleted
    }

    # 6. Check sequential performer handling (D-07, Pitfall 3)
    activity_instance = work_item.activity_instance
    activity_template = activity_template_map.get(activity_instance.activity_template_id)
    if activity_template and activity_template.performer_type == "sequential":
        performer_list = activity_template.performer_list or []
        current_index = activity_instance.current_performer_index or 0
        if current_index < len(performer_list) - 1:
            # Not the last performer -- create next work item, DON'T advance
            activity_instance.current_performer_index = current_index + 1
            next_perf_id = uuid.UUID(performer_list[current_index + 1])
            new_wi = WorkItem(
                activity_instance_id=activity_instance.id,
                performer_id=next_perf_id,
                state=WorkItemState.AVAILABLE,
                created_by=user_id,
                due_date=_compute_due_date(activity_template),
            )
            db.add(new_wi)
            await db.flush()
            await create_audit_record(
                db,
                entity_type="work_item",
                entity_id=str(work_item.id),
                action="work_item_completed",
                user_id=user_id,
                after_state={
                    "workflow_id": str(workflow_id),
                    "sequential_index": current_index,
                },
            )
            return work_item

    # 6b. Validate runtime selection (D-08)
    if activity_template and activity_template.performer_type == "runtime_selection":
        if not next_performer_id:
            raise ValueError("Runtime selection activity requires next_performer_id")
        # Validate next_performer_id is in the candidate group
        from app.models.user import user_groups
        group_id = uuid.UUID(activity_template.performer_id)
        group_result = await db.execute(
            select(user_groups.c.user_id).where(
                user_groups.c.group_id == group_id,
                user_groups.c.user_id == uuid.UUID(next_performer_id),
            )
        )
        if group_result.scalar_one_or_none() is None:
            raise ValueError("Selected performer is not a member of the candidate group")

    # 7. Advance from completed activity
    await _advance_from_activity(
        db,
        workflow,
        activity_instance,
        template,
        template_to_instance,
        user_id,
        instance_variables=current_variables,
        selected_path=selected_path,
        next_performer_id=next_performer_id,
    )

    # 7. Audit
    await create_audit_record(
        db,
        entity_type="work_item",
        entity_id=str(work_item.id),
        action="work_item_completed",
        user_id=user_id,
        after_state={
            "workflow_id": str(workflow_id),
            "activity_template_id": str(activity_instance.activity_template_id),
        },
    )

    # 8. Emit domain event for work item completed
    await event_bus.emit(
        db,
        event_type="work_item.completed",
        entity_type="work_item",
        entity_id=work_item.id,
        actor_id=uuid.UUID(user_id),
        payload={
            "workflow_id": str(workflow_id),
            "activity_template_id": str(activity_instance.activity_template_id),
        },
    )

    # Check if workflow just finished
    await db.refresh(workflow)
    if workflow.state == WorkflowState.FINISHED:
        await event_bus.emit(
            db,
            event_type="workflow.completed",
            entity_type="workflow_instance",
            entity_id=workflow.id,
            actor_id=uuid.UUID(user_id),
            payload={"template_id": str(workflow.process_template_id)},
        )

    return work_item


# ---------------------------------------------------------------------------
# Section 7: reject_work_item (D-03, D-04)
# ---------------------------------------------------------------------------


async def reject_work_item(
    db: AsyncSession,
    workflow_id: uuid.UUID,
    work_item_id: uuid.UUID,
    user_id: str,
    reason: str | None = None,
) -> WorkItem:
    """Reject a work item and traverse reject flows.

    For sequential performers, rejection goes back to the previous performer.
    For regular activities, rejection follows REJECT flow edges, resetting
    target activities from COMPLETE to ACTIVE with new work items.
    """
    # 1. Load workflow instance
    wf_result = await db.execute(
        select(WorkflowInstance).where(
            WorkflowInstance.id == workflow_id,
            WorkflowInstance.is_deleted == False,  # noqa: E712
        )
    )
    workflow = wf_result.scalar_one_or_none()
    if workflow is None:
        raise ValueError("Workflow not found")
    if workflow.state != WorkflowState.RUNNING:
        raise ValueError("Workflow is not running")

    # 2. Load work item with activity instance
    wi_result = await db.execute(
        select(WorkItem)
        .options(selectinload(WorkItem.activity_instance))
        .where(
            WorkItem.id == work_item_id,
            WorkItem.is_deleted == False,  # noqa: E712
        )
    )
    work_item = wi_result.scalar_one_or_none()
    if work_item is None:
        raise ValueError("Work item not found")
    if work_item.state != WorkItemState.ACQUIRED:
        raise ValueError(
            f"Cannot reject work item in state '{work_item.state.value}'; must be 'acquired'"
        )

    # 3. Mark work item as REJECTED
    work_item.state = WorkItemState.REJECTED
    work_item.completed_at = datetime.now(timezone.utc)

    activity_instance = work_item.activity_instance

    # 4. Load template with relations
    template_result = await db.execute(
        select(ProcessTemplate)
        .options(
            selectinload(ProcessTemplate.activity_templates),
            selectinload(ProcessTemplate.flow_templates),
        )
        .where(ProcessTemplate.id == workflow.process_template_id)
    )
    template = template_result.scalar_one()

    # Build activity template map
    activity_template_map: dict[uuid.UUID, ActivityTemplate] = {
        at.id: at for at in template.activity_templates if not at.is_deleted
    }
    activity_template = activity_template_map.get(activity_instance.activity_template_id)

    # 5. Check sequential performer rejection (D-07)
    if activity_template and activity_template.performer_type == "sequential":
        performer_list = activity_template.performer_list or []
        current_index = activity_instance.current_performer_index or 0
        if current_index == 0:
            raise ValueError("Cannot reject: already at first performer in sequence")
        # Decrement index and create work item for previous performer
        activity_instance.current_performer_index = current_index - 1
        prev_perf_id = uuid.UUID(performer_list[current_index - 1])
        new_wi = WorkItem(
            activity_instance_id=activity_instance.id,
            performer_id=prev_perf_id,
            state=WorkItemState.AVAILABLE,
            created_by=user_id,
            due_date=_compute_due_date(activity_template),
        )
        db.add(new_wi)
        await db.flush()
        after_state: dict = {"state": WorkItemState.REJECTED.value, "sequential_index": current_index}
        if reason:
            after_state["reason"] = reason
        await create_audit_record(
            db,
            entity_type="work_item",
            entity_id=str(work_item.id),
            action="work_item_rejected",
            user_id=user_id,
            after_state=after_state,
        )
        return work_item

    # 6. Find REJECT flows from current activity template
    reject_flows = [
        f
        for f in template.flow_templates
        if not f.is_deleted
        and f.source_activity_id == activity_instance.activity_template_id
        and f.flow_type == FlowType.REJECT
    ]
    if not reject_flows:
        raise ValueError("No reject flow defined for this activity")

    # 7. Build template_to_instance mapping
    ai_result = await db.execute(
        select(ActivityInstance).where(
            ActivityInstance.workflow_instance_id == workflow_id
        )
    )
    all_instances = list(ai_result.scalars().all())
    template_to_instance: dict[uuid.UUID, ActivityInstance] = {
        ai.activity_template_id: ai for ai in all_instances
    }

    # 8. Traverse reject flows
    for flow in reject_flows:
        target_ai = template_to_instance.get(flow.target_activity_id)
        if target_ai is None:
            continue

        # Reset target activity: COMPLETE -> ACTIVE (D-04)
        _enforce_activity_transition(target_ai.state, ActivityState.ACTIVE)
        target_ai.state = ActivityState.ACTIVE
        target_ai.started_at = datetime.now(timezone.utc)
        target_ai.completed_at = None

        # Resolve performers for the target activity template
        target_at = activity_template_map.get(flow.target_activity_id)
        if target_at:
            performers = await resolve_performers(
                db, target_at.performer_type, target_at.performer_id, workflow
            )
            if not performers:
                performers = [None]
            for perf_id in performers:
                new_wi = WorkItem(
                    activity_instance_id=target_ai.id,
                    performer_id=perf_id,
                    state=WorkItemState.AVAILABLE,
                    created_by=user_id,
                    due_date=_compute_due_date(target_at),
                )
                db.add(new_wi)

        # Place execution token for the reject flow
        token = ExecutionToken(
            workflow_instance_id=workflow.id,
            flow_template_id=flow.id,
            source_activity_instance_id=activity_instance.id,
            target_activity_template_id=flow.target_activity_id,
            is_consumed=True,  # Immediately consumed since we manually activated
            created_by=user_id,
        )
        db.add(token)

    # 9. Audit record
    after_state_audit: dict = {"state": WorkItemState.REJECTED.value}
    if reason:
        after_state_audit["reason"] = reason
    await create_audit_record(
        db,
        entity_type="work_item",
        entity_id=str(work_item.id),
        action="work_item_rejected",
        user_id=user_id,
        after_state=after_state_audit,
    )

    await db.flush()
    return work_item


# ---------------------------------------------------------------------------
# Section 8: Query functions
# ---------------------------------------------------------------------------


async def get_workflow(
    db: AsyncSession, workflow_id: uuid.UUID
) -> WorkflowInstance:
    """Load a workflow instance with activity instances, variables, and packages."""
    result = await db.execute(
        select(WorkflowInstance)
        .options(
            selectinload(WorkflowInstance.activity_instances).selectinload(
                ActivityInstance.activity_template
            ),
            selectinload(WorkflowInstance.work_items),
            selectinload(WorkflowInstance.process_variables),
            selectinload(WorkflowInstance.workflow_packages),
        )
        .where(
            WorkflowInstance.id == workflow_id,
            WorkflowInstance.is_deleted == False,  # noqa: E712
        )
    )
    workflow = result.scalar_one_or_none()
    if workflow is None:
        raise ValueError("Workflow not found")
    return workflow


async def list_workflows(
    db: AsyncSession, skip: int = 0, limit: int = 20
) -> tuple[list[WorkflowInstance], int]:
    """List workflow instances with pagination. Returns (workflows, total_count)."""
    base_query = select(WorkflowInstance).where(
        WorkflowInstance.is_deleted == False  # noqa: E712
    )

    count_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total_count = count_result.scalar_one()

    result = await db.execute(
        base_query.order_by(WorkflowInstance.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    workflows = list(result.scalars().all())

    return workflows, total_count


async def get_workflow_work_items(
    db: AsyncSession, workflow_id: uuid.UUID
) -> list[WorkItem]:
    """Get all work items for a workflow via activity instances."""
    result = await db.execute(
        select(WorkItem)
        .join(ActivityInstance, WorkItem.activity_instance_id == ActivityInstance.id)
        .where(
            ActivityInstance.workflow_instance_id == workflow_id,
            WorkItem.is_deleted == False,  # noqa: E712
        )
        .order_by(WorkItem.created_at.desc())
    )
    return list(result.scalars().all())


async def get_variable(
    db: AsyncSession, workflow_id: uuid.UUID, variable_name: str
) -> ProcessVariable:
    """Get a single process variable from a workflow instance."""
    result = await db.execute(
        select(ProcessVariable).where(
            ProcessVariable.workflow_instance_id == workflow_id,
            ProcessVariable.name == variable_name,
            ProcessVariable.is_deleted == False,  # noqa: E712
        )
    )
    variable = result.scalar_one_or_none()
    if variable is None:
        raise ValueError(f"Variable '{variable_name}' not found")
    return variable


async def update_variable(
    db: AsyncSession,
    workflow_id: uuid.UUID,
    variable_name: str,
    value: Any,
    user_id: str,
) -> ProcessVariable:
    """Update a process variable value on a workflow instance."""
    # Verify workflow exists and is running
    wf_result = await db.execute(
        select(WorkflowInstance).where(
            WorkflowInstance.id == workflow_id,
            WorkflowInstance.is_deleted == False,  # noqa: E712
        )
    )
    workflow = wf_result.scalar_one_or_none()
    if workflow is None:
        raise ValueError("Workflow not found")
    if workflow.state != WorkflowState.RUNNING:
        raise ValueError("Workflow is not running")

    variable = await get_variable(db, workflow_id, variable_name)
    before_value = _resolve_variable_value(variable)
    _set_variable_value(variable, value)

    await db.flush()

    await create_audit_record(
        db,
        entity_type="process_variable",
        entity_id=str(variable.id),
        action="variable_updated",
        user_id=user_id,
        before_state={"name": variable_name, "value": str(before_value)},
        after_state={"name": variable_name, "value": str(value)},
    )

    return variable
