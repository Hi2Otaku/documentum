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

from app.models.enums import ActivityState, WorkflowState
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
