import json
import uuid
from collections import deque
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import ActivityType, ProcessState, TriggerType
from app.models.workflow import (
    ActivityTemplate,
    FlowTemplate,
    ProcessTemplate,
    ProcessVariable,
)
from app.schemas.template import (
    ActivityTemplateCreate,
    ActivityTemplateUpdate,
    FlowTemplateCreate,
    FlowTemplateUpdate,
    ProcessTemplateCreate,
    ProcessTemplateUpdate,
    ProcessVariableCreate,
    ProcessVariableUpdate,
)
from app.services.audit_service import create_audit_record


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def get_template_with_relations(
    db: AsyncSession, template_id: UUID
) -> ProcessTemplate | None:
    """Fetch a template with all sub-entities eagerly loaded."""
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
    return result.scalar_one_or_none()


async def _reset_to_draft_if_validated(
    db: AsyncSession, template: ProcessTemplate
) -> None:
    """Reset template state to Draft if it is currently Validated."""
    if template.state == ProcessState.VALIDATED:
        template.state = ProcessState.DRAFT


async def _get_template_or_raise(
    db: AsyncSession, template_id: UUID
) -> ProcessTemplate:
    """Get template with relations or raise ValueError."""
    template = await get_template_with_relations(db, template_id)
    if template is None:
        raise ValueError("Template not found")
    return template


def _check_not_active(template: ProcessTemplate) -> None:
    """Raise if template is installed/active (immutable)."""
    if template.state == ProcessState.ACTIVE:
        raise ValueError(
            "Cannot modify installed template. Create a new version first."
        )


# ---------------------------------------------------------------------------
# ProcessTemplate CRUD
# ---------------------------------------------------------------------------


async def create_template(
    db: AsyncSession,
    data: ProcessTemplateCreate,
    user_id: str,
) -> ProcessTemplate:
    """Create a new process template in Draft state."""
    template = ProcessTemplate(
        name=data.name,
        description=data.description,
        version=1,
        state=ProcessState.DRAFT,
        is_installed=False,
        created_by=user_id,
    )
    db.add(template)
    await db.flush()

    await create_audit_record(
        db,
        entity_type="process_template",
        entity_id=str(template.id),
        action="create",
        user_id=user_id,
        after_state={"name": template.name, "version": template.version},
    )

    return template


async def get_template(
    db: AsyncSession, template_id: UUID
) -> ProcessTemplate | None:
    """Get a single template with all relations."""
    return await get_template_with_relations(db, template_id)


async def list_templates(
    db: AsyncSession, page: int = 1, page_size: int = 20
) -> tuple[list[ProcessTemplate], int]:
    """List templates with pagination. Returns (templates, total_count)."""
    base_query = select(ProcessTemplate).where(
        ProcessTemplate.is_deleted == False  # noqa: E712
    )

    count_query = select(func.count()).select_from(base_query.subquery())
    count_result = await db.execute(count_query)
    total_count = count_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(
        base_query.options(
            selectinload(ProcessTemplate.activity_templates),
            selectinload(ProcessTemplate.flow_templates),
            selectinload(ProcessTemplate.process_variables),
        )
        .order_by(ProcessTemplate.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    templates = list(result.scalars().all())

    return templates, total_count


async def update_template(
    db: AsyncSession,
    template_id: UUID,
    data: ProcessTemplateUpdate,
    user_id: str,
) -> ProcessTemplate:
    """Update template metadata. Creates new version if template is Active."""
    template = await _get_template_or_raise(db, template_id)

    # If installed/active, create a new version and update that instead
    if template.state == ProcessState.ACTIVE:
        new_template = await create_new_version(db, template_id, user_id)
        # Apply updates to the new version
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(new_template, field, value)
        await db.flush()

        await create_audit_record(
            db,
            entity_type="process_template",
            entity_id=str(new_template.id),
            action="update",
            user_id=user_id,
            after_state={"name": new_template.name},
        )
        return new_template

    before_state = {"name": template.name, "description": template.description}

    await _reset_to_draft_if_validated(db, template)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)

    await db.flush()

    await create_audit_record(
        db,
        entity_type="process_template",
        entity_id=str(template.id),
        action="update",
        user_id=user_id,
        before_state=before_state,
        after_state={"name": template.name, "description": template.description},
    )

    return template


async def delete_template(
    db: AsyncSession,
    template_id: UUID,
    user_id: str,
) -> ProcessTemplate:
    """Soft-delete a template."""
    template = await _get_template_or_raise(db, template_id)

    template.is_deleted = True
    await db.flush()

    await create_audit_record(
        db,
        entity_type="process_template",
        entity_id=str(template.id),
        action="delete",
        user_id=user_id,
    )

    return template


# ---------------------------------------------------------------------------
# ActivityTemplate CRUD
# ---------------------------------------------------------------------------


async def add_activity(
    db: AsyncSession,
    template_id: UUID,
    data: ActivityTemplateCreate,
    user_id: str,
) -> ActivityTemplate:
    """Add an activity to a template."""
    template = await _get_template_or_raise(db, template_id)
    _check_not_active(template)
    await _reset_to_draft_if_validated(db, template)

    activity = ActivityTemplate(
        process_template_id=template_id,
        name=data.name,
        activity_type=data.activity_type,
        description=data.description,
        performer_type=data.performer_type.value if data.performer_type else None,
        performer_id=data.performer_id,
        trigger_type=data.trigger_type,
        method_name=data.method_name,
        position_x=data.position_x,
        position_y=data.position_y,
        created_by=user_id,
    )
    db.add(activity)
    await db.flush()

    await create_audit_record(
        db,
        entity_type="activity_template",
        entity_id=str(activity.id),
        action="create",
        user_id=user_id,
        after_state={"name": activity.name, "activity_type": activity.activity_type.value},
    )

    return activity


async def update_activity(
    db: AsyncSession,
    template_id: UUID,
    activity_id: UUID,
    data: ActivityTemplateUpdate,
    user_id: str,
) -> ActivityTemplate:
    """Update an activity within a template."""
    template = await _get_template_or_raise(db, template_id)
    _check_not_active(template)
    await _reset_to_draft_if_validated(db, template)

    result = await db.execute(
        select(ActivityTemplate).where(
            ActivityTemplate.id == activity_id,
            ActivityTemplate.process_template_id == template_id,
            ActivityTemplate.is_deleted == False,  # noqa: E712
        )
    )
    activity = result.scalar_one_or_none()
    if activity is None:
        raise ValueError("Activity not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "performer_type" and value is not None:
            setattr(activity, field, value.value if hasattr(value, "value") else value)
        else:
            setattr(activity, field, value)

    await db.flush()

    await create_audit_record(
        db,
        entity_type="activity_template",
        entity_id=str(activity.id),
        action="update",
        user_id=user_id,
    )

    return activity


async def delete_activity(
    db: AsyncSession,
    template_id: UUID,
    activity_id: UUID,
    user_id: str,
) -> ActivityTemplate:
    """Soft-delete an activity from a template."""
    template = await _get_template_or_raise(db, template_id)
    _check_not_active(template)
    await _reset_to_draft_if_validated(db, template)

    result = await db.execute(
        select(ActivityTemplate).where(
            ActivityTemplate.id == activity_id,
            ActivityTemplate.process_template_id == template_id,
            ActivityTemplate.is_deleted == False,  # noqa: E712
        )
    )
    activity = result.scalar_one_or_none()
    if activity is None:
        raise ValueError("Activity not found")

    activity.is_deleted = True
    await db.flush()

    await create_audit_record(
        db,
        entity_type="activity_template",
        entity_id=str(activity.id),
        action="delete",
        user_id=user_id,
    )

    return activity


# ---------------------------------------------------------------------------
# FlowTemplate CRUD
# ---------------------------------------------------------------------------


async def add_flow(
    db: AsyncSession,
    template_id: UUID,
    data: FlowTemplateCreate,
    user_id: str,
) -> FlowTemplate:
    """Add a flow connecting two activities in a template."""
    template = await _get_template_or_raise(db, template_id)
    _check_not_active(template)
    await _reset_to_draft_if_validated(db, template)

    # Verify source != target (no self-loops)
    if data.source_activity_id == data.target_activity_id:
        raise ValueError("Self-loops are not allowed: source and target must differ")

    # Verify both activities belong to this template and are not deleted
    for activity_id in [data.source_activity_id, data.target_activity_id]:
        result = await db.execute(
            select(ActivityTemplate).where(
                ActivityTemplate.id == activity_id,
                ActivityTemplate.process_template_id == template_id,
                ActivityTemplate.is_deleted == False,  # noqa: E712
            )
        )
        if result.scalar_one_or_none() is None:
            raise ValueError(
                f"Activity {activity_id} not found in template {template_id}"
            )

    # Serialize condition_expression if it's a dict
    condition_str = None
    if data.condition_expression is not None:
        condition_str = json.dumps(data.condition_expression)

    flow = FlowTemplate(
        process_template_id=template_id,
        source_activity_id=data.source_activity_id,
        target_activity_id=data.target_activity_id,
        flow_type=data.flow_type,
        condition_expression=condition_str,
        created_by=user_id,
    )
    db.add(flow)
    await db.flush()

    await create_audit_record(
        db,
        entity_type="flow_template",
        entity_id=str(flow.id),
        action="create",
        user_id=user_id,
        after_state={
            "source": str(data.source_activity_id),
            "target": str(data.target_activity_id),
            "flow_type": flow.flow_type.value,
        },
    )

    return flow


async def update_flow(
    db: AsyncSession,
    template_id: UUID,
    flow_id: UUID,
    data: FlowTemplateUpdate,
    user_id: str,
) -> FlowTemplate:
    """Update a flow within a template."""
    template = await _get_template_or_raise(db, template_id)
    _check_not_active(template)
    await _reset_to_draft_if_validated(db, template)

    result = await db.execute(
        select(FlowTemplate).where(
            FlowTemplate.id == flow_id,
            FlowTemplate.process_template_id == template_id,
            FlowTemplate.is_deleted == False,  # noqa: E712
        )
    )
    flow = result.scalar_one_or_none()
    if flow is None:
        raise ValueError("Flow not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "condition_expression" and isinstance(value, dict):
            setattr(flow, field, json.dumps(value))
        else:
            setattr(flow, field, value)

    await db.flush()

    await create_audit_record(
        db,
        entity_type="flow_template",
        entity_id=str(flow.id),
        action="update",
        user_id=user_id,
    )

    return flow


async def delete_flow(
    db: AsyncSession,
    template_id: UUID,
    flow_id: UUID,
    user_id: str,
) -> FlowTemplate:
    """Soft-delete a flow from a template."""
    template = await _get_template_or_raise(db, template_id)
    _check_not_active(template)
    await _reset_to_draft_if_validated(db, template)

    result = await db.execute(
        select(FlowTemplate).where(
            FlowTemplate.id == flow_id,
            FlowTemplate.process_template_id == template_id,
            FlowTemplate.is_deleted == False,  # noqa: E712
        )
    )
    flow = result.scalar_one_or_none()
    if flow is None:
        raise ValueError("Flow not found")

    flow.is_deleted = True
    await db.flush()

    await create_audit_record(
        db,
        entity_type="flow_template",
        entity_id=str(flow.id),
        action="delete",
        user_id=user_id,
    )

    return flow


# ---------------------------------------------------------------------------
# ProcessVariable CRUD
# ---------------------------------------------------------------------------


async def add_variable(
    db: AsyncSession,
    template_id: UUID,
    data: ProcessVariableCreate,
    user_id: str,
) -> ProcessVariable:
    """Add a process variable to a template."""
    template = await _get_template_or_raise(db, template_id)
    _check_not_active(template)
    await _reset_to_draft_if_validated(db, template)

    variable = ProcessVariable(
        process_template_id=template_id,
        name=data.name,
        variable_type=data.variable_type,
        string_value=data.default_string_value,
        int_value=data.default_int_value,
        bool_value=data.default_bool_value,
        date_value=data.default_date_value,
        created_by=user_id,
    )
    db.add(variable)
    await db.flush()

    await create_audit_record(
        db,
        entity_type="process_variable",
        entity_id=str(variable.id),
        action="create",
        user_id=user_id,
        after_state={"name": variable.name, "variable_type": variable.variable_type},
    )

    return variable


async def update_variable(
    db: AsyncSession,
    template_id: UUID,
    variable_id: UUID,
    data: ProcessVariableUpdate,
    user_id: str,
) -> ProcessVariable:
    """Update a process variable within a template."""
    template = await _get_template_or_raise(db, template_id)
    _check_not_active(template)
    await _reset_to_draft_if_validated(db, template)

    result = await db.execute(
        select(ProcessVariable).where(
            ProcessVariable.id == variable_id,
            ProcessVariable.process_template_id == template_id,
            ProcessVariable.is_deleted == False,  # noqa: E712
        )
    )
    variable = result.scalar_one_or_none()
    if variable is None:
        raise ValueError("Variable not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        # Map schema field names to model field names
        model_field = field
        if field == "default_string_value":
            model_field = "string_value"
        elif field == "default_int_value":
            model_field = "int_value"
        elif field == "default_bool_value":
            model_field = "bool_value"
        elif field == "default_date_value":
            model_field = "date_value"
        setattr(variable, model_field, value)

    await db.flush()

    await create_audit_record(
        db,
        entity_type="process_variable",
        entity_id=str(variable.id),
        action="update",
        user_id=user_id,
    )

    return variable


async def delete_variable(
    db: AsyncSession,
    template_id: UUID,
    variable_id: UUID,
    user_id: str,
) -> ProcessVariable:
    """Soft-delete a process variable from a template."""
    template = await _get_template_or_raise(db, template_id)
    _check_not_active(template)
    await _reset_to_draft_if_validated(db, template)

    result = await db.execute(
        select(ProcessVariable).where(
            ProcessVariable.id == variable_id,
            ProcessVariable.process_template_id == template_id,
            ProcessVariable.is_deleted == False,  # noqa: E712
        )
    )
    variable = result.scalar_one_or_none()
    if variable is None:
        raise ValueError("Variable not found")

    variable.is_deleted = True
    await db.flush()

    await create_audit_record(
        db,
        entity_type="process_variable",
        entity_id=str(variable.id),
        action="delete",
        user_id=user_id,
    )

    return variable


# ---------------------------------------------------------------------------
# Validation (TMPL-08)
# ---------------------------------------------------------------------------


async def validate_template(
    db: AsyncSession,
    template_id: UUID,
    user_id: str,
) -> tuple[bool, list[dict]]:
    """Validate a template's graph structure and configuration.

    Returns (is_valid, errors_list).
    """
    template = await _get_template_or_raise(db, template_id)

    errors: list[dict] = []

    # Filter out soft-deleted sub-entities
    activities = [a for a in template.activity_templates if not a.is_deleted]
    flows = [f for f in template.flow_templates if not f.is_deleted]
    variables = [v for v in template.process_variables if not v.is_deleted]

    activity_ids = {a.id for a in activities}
    activity_map = {a.id: a for a in activities}

    # 1. INVALID_START_COUNT: Exactly 1 Start activity
    start_activities = [a for a in activities if a.activity_type == ActivityType.START]
    if len(start_activities) != 1:
        errors.append({
            "code": "INVALID_START_COUNT",
            "message": f"Expected exactly 1 Start activity, found {len(start_activities)}",
            "entity_type": "activity_template",
            "entity_id": None,
        })

    # 2. NO_END_ACTIVITY: At least 1 End activity
    end_activities = [a for a in activities if a.activity_type == ActivityType.END]
    if len(end_activities) < 1:
        errors.append({
            "code": "NO_END_ACTIVITY",
            "message": "At least 1 End activity is required",
            "entity_type": "activity_template",
            "entity_id": None,
        })

    # 3. UNREACHABLE_ACTIVITY: BFS from Start
    if len(start_activities) == 1:
        adjacency: dict[UUID, list[UUID]] = {a.id: [] for a in activities}
        for f in flows:
            if f.source_activity_id in adjacency:
                adjacency[f.source_activity_id].append(f.target_activity_id)

        visited: set[UUID] = set()
        queue: deque[UUID] = deque()
        queue.append(start_activities[0].id)
        visited.add(start_activities[0].id)

        while queue:
            current = queue.popleft()
            for neighbor in adjacency.get(current, []):
                if neighbor not in visited and neighbor in activity_ids:
                    visited.add(neighbor)
                    queue.append(neighbor)

        for a in activities:
            if a.id not in visited:
                errors.append({
                    "code": "UNREACHABLE_ACTIVITY",
                    "message": f"Activity '{a.name}' is not reachable from Start",
                    "entity_type": "activity_template",
                    "entity_id": str(a.id),
                })

    # Build incoming/outgoing maps for orphan checks
    incoming: dict[UUID, int] = {a.id: 0 for a in activities}
    outgoing: dict[UUID, int] = {a.id: 0 for a in activities}
    for f in flows:
        if f.target_activity_id in incoming:
            incoming[f.target_activity_id] += 1
        if f.source_activity_id in outgoing:
            outgoing[f.source_activity_id] += 1

    # 4. ORPHAN_FLOW_IN: Non-Start must have >= 1 incoming
    for a in activities:
        if a.activity_type != ActivityType.START and incoming.get(a.id, 0) == 0:
            errors.append({
                "code": "ORPHAN_FLOW_IN",
                "message": f"Activity '{a.name}' has no incoming flows",
                "entity_type": "activity_template",
                "entity_id": str(a.id),
            })

    # 5. ORPHAN_FLOW_OUT: Non-End must have >= 1 outgoing
    for a in activities:
        if a.activity_type != ActivityType.END and outgoing.get(a.id, 0) == 0:
            errors.append({
                "code": "ORPHAN_FLOW_OUT",
                "message": f"Activity '{a.name}' has no outgoing flows",
                "entity_type": "activity_template",
                "entity_id": str(a.id),
            })

    # 6. MISSING_PERFORMER: Every MANUAL activity needs performer_type
    for a in activities:
        if a.activity_type == ActivityType.MANUAL:
            if not a.performer_type:
                errors.append({
                    "code": "MISSING_PERFORMER",
                    "message": f"Manual activity '{a.name}' requires a performer_type",
                    "entity_type": "activity_template",
                    "entity_id": str(a.id),
                })

    # 7. MISSING_METHOD: Every AUTO activity needs method_name
    for a in activities:
        if a.activity_type == ActivityType.AUTO:
            if not a.method_name:
                errors.append({
                    "code": "MISSING_METHOD",
                    "message": f"Auto activity '{a.name}' requires a method_name",
                    "entity_type": "activity_template",
                    "entity_id": str(a.id),
                })

    # 8. SELF_LOOP: No flow where source == target
    for f in flows:
        if f.source_activity_id == f.target_activity_id:
            errors.append({
                "code": "SELF_LOOP",
                "message": "Flow has same source and target activity",
                "entity_type": "flow_template",
                "entity_id": str(f.id),
            })

    # 9. INVALID_CONDITION: Validate condition_expression structure
    variable_names = {v.name for v in variables}
    for f in flows:
        if f.condition_expression:
            try:
                cond = f.condition_expression
                if isinstance(cond, str):
                    cond = json.loads(cond)

                def _validate_condition(c: dict) -> None:
                    if "all" in c or "any" in c:
                        sub_conditions = c.get("all") or c.get("any")
                        if isinstance(sub_conditions, list):
                            for sub in sub_conditions:
                                if isinstance(sub, dict):
                                    _validate_condition(sub)
                    else:
                        if "field" not in c or "operator" not in c:
                            errors.append({
                                "code": "INVALID_CONDITION",
                                "message": f"Condition on flow {f.id} missing 'field' or 'operator'",
                                "entity_type": "flow_template",
                                "entity_id": str(f.id),
                            })
                        elif c["field"] not in variable_names:
                            errors.append({
                                "code": "INVALID_CONDITION",
                                "message": f"Condition references unknown variable '{c['field']}'",
                                "entity_type": "flow_template",
                                "entity_id": str(f.id),
                            })

                if isinstance(cond, dict):
                    _validate_condition(cond)
            except (json.JSONDecodeError, TypeError):
                errors.append({
                    "code": "INVALID_CONDITION",
                    "message": f"Condition expression on flow {f.id} is not valid JSON",
                    "entity_type": "flow_template",
                    "entity_id": str(f.id),
                })

    if not errors:
        template.state = ProcessState.VALIDATED
        await db.flush()

        await create_audit_record(
            db,
            entity_type="process_template",
            entity_id=str(template.id),
            action="validate",
            user_id=user_id,
            details="Template validated successfully",
        )
        return True, []

    return False, errors


# ---------------------------------------------------------------------------
# Installation (TMPL-09)
# ---------------------------------------------------------------------------


async def install_template(
    db: AsyncSession,
    template_id: UUID,
    user_id: str,
) -> ProcessTemplate:
    """Install a validated template, making it Active."""
    template = await _get_template_or_raise(db, template_id)

    if template.state != ProcessState.VALIDATED:
        raise ValueError(
            f"Template must be in VALIDATED state to install (current: {template.state.value})"
        )

    template.state = ProcessState.ACTIVE
    template.is_installed = True
    template.installed_at = datetime.now(timezone.utc)

    # Deprecate other installed versions with the same name
    result = await db.execute(
        select(ProcessTemplate).where(
            ProcessTemplate.name == template.name,
            ProcessTemplate.is_installed == True,  # noqa: E712
            ProcessTemplate.id != template.id,
            ProcessTemplate.is_deleted == False,  # noqa: E712
        )
    )
    old_versions = list(result.scalars().all())
    for old in old_versions:
        old.state = ProcessState.DEPRECATED
        old.is_installed = False

    await db.flush()

    await create_audit_record(
        db,
        entity_type="process_template",
        entity_id=str(template.id),
        action="install",
        user_id=user_id,
        after_state={
            "name": template.name,
            "version": template.version,
            "deprecated_count": len(old_versions),
        },
    )

    return template


# ---------------------------------------------------------------------------
# Versioning -- copy-on-write (TMPL-10)
# ---------------------------------------------------------------------------


async def create_new_version(
    db: AsyncSession,
    template_id: UUID,
    user_id: str,
) -> ProcessTemplate:
    """Create a new draft version by deep-cloning an active template."""
    original = await _get_template_or_raise(db, template_id)

    new_template = ProcessTemplate(
        name=original.name,
        description=original.description,
        version=original.version + 1,
        state=ProcessState.DRAFT,
        is_installed=False,
        created_by=user_id,
    )
    db.add(new_template)
    await db.flush()

    # Clone activities and build ID mapping for flow remapping
    activity_id_map: dict[UUID, UUID] = {}

    for a in original.activity_templates:
        if a.is_deleted:
            continue
        new_activity = ActivityTemplate(
            process_template_id=new_template.id,
            name=a.name,
            activity_type=a.activity_type,
            description=a.description,
            performer_type=a.performer_type,
            performer_id=a.performer_id,
            trigger_type=a.trigger_type,
            method_name=a.method_name,
            position_x=a.position_x,
            position_y=a.position_y,
            created_by=user_id,
        )
        db.add(new_activity)
        await db.flush()
        activity_id_map[a.id] = new_activity.id

    # Clone flows with remapped activity IDs
    for f in original.flow_templates:
        if f.is_deleted:
            continue
        new_source = activity_id_map.get(f.source_activity_id)
        new_target = activity_id_map.get(f.target_activity_id)
        if new_source is None or new_target is None:
            continue  # Skip flows referencing deleted activities

        new_flow = FlowTemplate(
            process_template_id=new_template.id,
            source_activity_id=new_source,
            target_activity_id=new_target,
            flow_type=f.flow_type,
            condition_expression=f.condition_expression,
            created_by=user_id,
        )
        db.add(new_flow)

    # Clone process variables
    for v in original.process_variables:
        if v.is_deleted:
            continue
        new_var = ProcessVariable(
            process_template_id=new_template.id,
            name=v.name,
            variable_type=v.variable_type,
            string_value=v.string_value,
            int_value=v.int_value,
            bool_value=v.bool_value,
            date_value=v.date_value,
            created_by=user_id,
        )
        db.add(new_var)

    await db.flush()

    await create_audit_record(
        db,
        entity_type="process_template",
        entity_id=str(new_template.id),
        action="create_version",
        user_id=user_id,
        details=f"New version {new_template.version} created from version {original.version}",
    )

    return new_template
