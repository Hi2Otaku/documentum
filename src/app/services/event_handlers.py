"""Event handlers that react to domain events.

Handlers are registered on module import, so this module must be imported
at application startup (done in main.py lifespan).
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import ActivityState, ActivityType, WorkflowState
from app.models.event import DomainEvent
from app.models.workflow import (
    ActivityInstance,
    ActivityTemplate,
    ProcessTemplate,
    ProcessVariable,
    WorkflowInstance,
)
from app.services.event_bus import event_bus
from app.services import notification_service

logger = logging.getLogger(__name__)


@event_bus.on("work_item.assigned")
async def _notify_work_item_assigned(db: AsyncSession, event: DomainEvent) -> None:
    """Create an in-app notification when a work item is assigned."""
    payload = event.payload or {}
    performer_id = payload.get("performer_id")
    if not performer_id:
        return

    notification = await notification_service.create_notification(
        db,
        user_id=uuid.UUID(performer_id),
        title="New task assigned",
        message=payload.get("activity_name", "A new task has been assigned to you."),
        notification_type="work_item.assigned",
        entity_type="work_item",
        entity_id=event.entity_id,
    )

    # Dispatch email notification via Celery
    from app.tasks.notification import send_notification_email
    send_notification_email.delay(str(notification.id))


@event_bus.on("work_item.delegated")
async def _notify_work_item_delegated(db: AsyncSession, event: DomainEvent) -> None:
    """Create an in-app notification when a work item is delegated."""
    payload = event.payload or {}
    delegate_id = payload.get("delegate_id")
    if not delegate_id:
        return

    notification = await notification_service.create_notification(
        db,
        user_id=uuid.UUID(delegate_id),
        title="Task delegated to you",
        message=payload.get("activity_name", "A task has been delegated to you."),
        notification_type="work_item.delegated",
        entity_type="work_item",
        entity_id=event.entity_id,
    )

    # Dispatch email notification via Celery
    from app.tasks.notification import send_notification_email
    send_notification_email.delay(str(notification.id))


@event_bus.on("workflow.completed")
async def _resume_parent_on_child_complete(db: AsyncSession, event: DomainEvent) -> None:
    """When a child sub-workflow completes, resume the parent workflow."""
    result = await db.execute(
        select(WorkflowInstance).where(WorkflowInstance.id == event.entity_id)
    )
    child_wf = result.scalar_one_or_none()
    if child_wf is None or child_wf.parent_workflow_id is None:
        return  # Not a sub-workflow

    # Load the parent activity instance
    pai_result = await db.execute(
        select(ActivityInstance).where(
            ActivityInstance.id == child_wf.parent_activity_instance_id
        )
    )
    parent_ai = pai_result.scalar_one_or_none()
    if parent_ai is None or parent_ai.state != ActivityState.ACTIVE:
        return

    # Do NOT mark parent_ai as COMPLETE here -- _advance_from_activity handles that

    # Load parent workflow
    pwf_result = await db.execute(
        select(WorkflowInstance).where(
            WorkflowInstance.id == child_wf.parent_workflow_id
        )
    )
    parent_wf = pwf_result.scalar_one_or_none()
    if parent_wf is None or parent_wf.state != WorkflowState.RUNNING:
        return

    # Load the parent template with relations
    tmpl_result = await db.execute(
        select(ProcessTemplate)
        .options(
            selectinload(ProcessTemplate.activity_templates),
            selectinload(ProcessTemplate.flow_templates),
            selectinload(ProcessTemplate.process_variables),
        )
        .where(ProcessTemplate.id == parent_wf.process_template_id)
    )
    parent_template = tmpl_result.scalar_one()

    # Build template_to_instance mapping
    ai_result = await db.execute(
        select(ActivityInstance).where(
            ActivityInstance.workflow_instance_id == parent_wf.id
        )
    )
    all_instances = list(ai_result.scalars().all())
    template_to_instance: dict[uuid.UUID, ActivityInstance] = {
        ai.activity_template_id: ai for ai in all_instances
    }

    # Reload parent process variables
    pv_result = await db.execute(
        select(ProcessVariable).where(
            ProcessVariable.workflow_instance_id == parent_wf.id,
            ProcessVariable.is_deleted == False,  # noqa: E712
        )
    )
    instance_variables = list(pv_result.scalars().all())

    # Advance parent workflow from the completed sub-workflow activity
    from app.services.engine_service import _advance_from_activity
    await _advance_from_activity(
        db,
        parent_wf,
        parent_ai,
        parent_template,
        template_to_instance,
        user_id=str(parent_wf.supervisor_id) if parent_wf.supervisor_id else "system",
        instance_variables=instance_variables,
    )

    await db.flush()
    logger.info(
        "Parent workflow %s resumed after child %s completed",
        parent_wf.id,
        child_wf.id,
    )


@event_bus.on("workflow.failed")
async def _fail_parent_on_child_failure(db: AsyncSession, event: DomainEvent) -> None:
    """When a child sub-workflow fails, mark the parent activity as ERROR."""
    result = await db.execute(
        select(WorkflowInstance).where(WorkflowInstance.id == event.entity_id)
    )
    child_wf = result.scalar_one_or_none()
    if child_wf is None or child_wf.parent_workflow_id is None:
        return  # Not a sub-workflow

    # Load the parent activity instance
    pai_result = await db.execute(
        select(ActivityInstance).where(
            ActivityInstance.id == child_wf.parent_activity_instance_id
        )
    )
    parent_ai = pai_result.scalar_one_or_none()
    if parent_ai is None or parent_ai.state != ActivityState.ACTIVE:
        return

    parent_ai.state = ActivityState.ERROR
    await db.flush()
    logger.warning(
        "Child workflow %s failed, marking parent activity %s as ERROR",
        child_wf.id,
        parent_ai.id,
    )


# ---------------------------------------------------------------------------
# EVENT activity handlers -- auto-complete on matching domain events
# ---------------------------------------------------------------------------


def _matches_filter(filter_config: dict, payload: dict) -> bool:
    """Check if all key-value pairs in filter_config match the event payload."""
    for key, expected in filter_config.items():
        actual = payload.get(key)
        if str(actual) != str(expected):
            return False
    return True


async def _try_complete_event_activities(
    db: AsyncSession, event: DomainEvent, event_type: str
) -> None:
    """Find all ACTIVE EVENT activities listening for this event_type and complete matches."""
    # Query active EVENT activity instances where the template matches event_type
    stmt = (
        select(ActivityInstance)
        .join(ActivityTemplate, ActivityInstance.activity_template_id == ActivityTemplate.id)
        .join(WorkflowInstance, ActivityInstance.workflow_instance_id == WorkflowInstance.id)
        .where(
            ActivityInstance.state == ActivityState.ACTIVE,
            ActivityTemplate.activity_type == ActivityType.EVENT,
            ActivityTemplate.event_type_filter == event_type,
            WorkflowInstance.state == WorkflowState.RUNNING,
        )
    )
    result = await db.execute(stmt)
    active_event_ais = list(result.scalars().all())

    if not active_event_ais:
        return

    from app.services.engine_service import _advance_from_activity

    for ai in active_event_ais:
        # Load the template for filter config check
        at_result = await db.execute(
            select(ActivityTemplate).where(ActivityTemplate.id == ai.activity_template_id)
        )
        at = at_result.scalar_one()

        # Check filter config if present
        if at.event_filter_config:
            payload = event.payload or {}
            if not _matches_filter(at.event_filter_config, payload):
                continue

        # Load the workflow instance
        wf_result = await db.execute(
            select(WorkflowInstance).where(WorkflowInstance.id == ai.workflow_instance_id)
        )
        wf = wf_result.scalar_one()

        # Load the template with relations
        tmpl_result = await db.execute(
            select(ProcessTemplate)
            .options(
                selectinload(ProcessTemplate.activity_templates),
                selectinload(ProcessTemplate.flow_templates),
                selectinload(ProcessTemplate.process_variables),
            )
            .where(ProcessTemplate.id == wf.process_template_id)
        )
        template = tmpl_result.scalar_one()

        # Build template_to_instance mapping
        ai_all_result = await db.execute(
            select(ActivityInstance).where(
                ActivityInstance.workflow_instance_id == wf.id
            )
        )
        all_instances = list(ai_all_result.scalars().all())
        template_to_instance: dict[uuid.UUID, ActivityInstance] = {
            inst.activity_template_id: inst for inst in all_instances
        }

        # Load instance variables
        pv_result = await db.execute(
            select(ProcessVariable).where(
                ProcessVariable.workflow_instance_id == wf.id,
                ProcessVariable.is_deleted == False,  # noqa: E712
            )
        )
        instance_variables = list(pv_result.scalars().all())

        # Advance from the event activity
        await _advance_from_activity(
            db,
            wf,
            ai,
            template,
            template_to_instance,
            user_id=str(wf.supervisor_id) if wf.supervisor_id else "system",
            instance_variables=instance_variables,
        )

        logger.info(
            "EVENT activity %s completed on %s event for workflow %s",
            ai.id,
            event_type,
            wf.id,
        )

    await db.flush()


@event_bus.on("document.uploaded")
async def _complete_event_activities_on_document_uploaded(
    db: AsyncSession, event: DomainEvent
) -> None:
    """Complete EVENT activities listening for document.uploaded."""
    await _try_complete_event_activities(db, event, "document.uploaded")


@event_bus.on("lifecycle.changed")
async def _complete_event_activities_on_lifecycle_changed(
    db: AsyncSession, event: DomainEvent
) -> None:
    """Complete EVENT activities listening for lifecycle.changed."""
    await _try_complete_event_activities(db, event, "lifecycle.changed")


@event_bus.on("workflow.completed")
async def _complete_event_activities_on_workflow_completed(
    db: AsyncSession, event: DomainEvent
) -> None:
    """Complete EVENT activities listening for workflow.completed."""
    await _try_complete_event_activities(db, event, "workflow.completed")
