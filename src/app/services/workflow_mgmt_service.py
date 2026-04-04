"""Admin workflow management operations.

Separate from engine_service per anti-pattern guidance: admin operations are
distinct from normal advancement. Each operation validates state, transitions
atomically, updates related work items, and audits.
"""
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import ActivityState, WorkflowState, WorkItemState
from app.models.user import User
from app.models.workflow import (
    ActivityInstance,
    ActivityTemplate,
    ExecutionToken,
    ProcessTemplate,
    WorkflowInstance,
    WorkItem,
    WorkItemComment,
)
from app.services.audit_service import create_audit_record
from app.services.engine_service import _enforce_workflow_transition

logger = logging.getLogger(__name__)


async def _get_workflow_locked(
    db: AsyncSession, workflow_id: uuid.UUID
) -> WorkflowInstance:
    """Fetch workflow with row-level lock. Raises ValueError if not found."""
    result = await db.execute(
        select(WorkflowInstance)
        .where(
            WorkflowInstance.id == workflow_id,
            WorkflowInstance.is_deleted == False,  # noqa: E712
        )
        .with_for_update()
    )
    workflow = result.scalar_one_or_none()
    if workflow is None:
        raise ValueError(f"Workflow {workflow_id} not found")
    return workflow


async def _get_active_work_items(
    db: AsyncSession,
    workflow_id: uuid.UUID,
    states: list[WorkItemState],
) -> list[WorkItem]:
    """Get work items for a workflow in the specified states."""
    result = await db.execute(
        select(WorkItem)
        .join(ActivityInstance)
        .where(
            ActivityInstance.workflow_instance_id == workflow_id,
            WorkItem.state.in_(states),
        )
    )
    return list(result.scalars().all())


async def halt_workflow(
    db: AsyncSession, workflow_id: uuid.UUID, admin_id: str
) -> WorkflowInstance:
    """Halt a running workflow, suspending its active work items."""
    workflow = await _get_workflow_locked(db, workflow_id)
    _enforce_workflow_transition(workflow.state, WorkflowState.HALTED)

    workflow.state = WorkflowState.HALTED

    # Suspend active work items
    work_items = await _get_active_work_items(
        db, workflow_id, [WorkItemState.AVAILABLE, WorkItemState.ACQUIRED]
    )
    for wi in work_items:
        wi.state = WorkItemState.SUSPENDED

    await create_audit_record(
        db,
        entity_type="workflow",
        entity_id=str(workflow_id),
        action="workflow_halted",
        user_id=admin_id,
        before_state={"state": "running"},
        after_state={"state": "halted", "suspended_items": len(work_items)},
    )

    await db.flush()
    return workflow


async def resume_workflow(
    db: AsyncSession, workflow_id: uuid.UUID, admin_id: str
) -> WorkflowInstance:
    """Resume a halted workflow, restoring suspended work items to available."""
    workflow = await _get_workflow_locked(db, workflow_id)
    _enforce_workflow_transition(workflow.state, WorkflowState.RUNNING)

    workflow.state = WorkflowState.RUNNING

    # Restore suspended work items to available
    work_items = await _get_active_work_items(
        db, workflow_id, [WorkItemState.SUSPENDED]
    )
    for wi in work_items:
        wi.state = WorkItemState.AVAILABLE

    await create_audit_record(
        db,
        entity_type="workflow",
        entity_id=str(workflow_id),
        action="workflow_resumed",
        user_id=admin_id,
        before_state={"state": "halted"},
        after_state={"state": "running", "restored_items": len(work_items)},
    )

    await db.flush()
    return workflow


async def abort_workflow(
    db: AsyncSession, workflow_id: uuid.UUID, admin_id: str
) -> WorkflowInstance:
    """Abort a running or halted workflow, cancelling all active items."""
    workflow = await _get_workflow_locked(db, workflow_id)

    if workflow.state not in (WorkflowState.RUNNING, WorkflowState.HALTED):
        raise ValueError(
            f"Cannot abort workflow in state '{workflow.state.value}'"
        )

    before_state = workflow.state.value
    workflow.state = WorkflowState.FAILED
    workflow.completed_at = datetime.now(timezone.utc)

    # Cancel all non-complete work items
    work_items = await _get_active_work_items(
        db,
        workflow_id,
        [WorkItemState.AVAILABLE, WorkItemState.ACQUIRED, WorkItemState.SUSPENDED],
    )
    for wi in work_items:
        wi.state = WorkItemState.COMPLETE
        wi.completed_at = datetime.now(timezone.utc)

    # Complete active activity instances
    ai_result = await db.execute(
        select(ActivityInstance).where(
            ActivityInstance.workflow_instance_id == workflow_id,
            ActivityInstance.state == ActivityState.ACTIVE,
        )
    )
    active_activities = list(ai_result.scalars().all())
    for ai in active_activities:
        ai.state = ActivityState.COMPLETE
        ai.completed_at = datetime.now(timezone.utc)

    await create_audit_record(
        db,
        entity_type="workflow",
        entity_id=str(workflow_id),
        action="workflow_aborted",
        user_id=admin_id,
        before_state={"state": before_state},
        after_state={
            "state": "failed",
            "cancelled_items": len(work_items),
            "completed_activities": len(active_activities),
        },
    )

    await db.flush()
    return workflow


async def restart_workflow(
    db: AsyncSession, workflow_id: uuid.UUID, admin_id: str
) -> WorkflowInstance:
    """Restart a failed workflow, resetting to dormant state.

    Preserves process variables and workflow packages.
    Deletes all work items and execution tokens.
    """
    workflow = await _get_workflow_locked(db, workflow_id)
    _enforce_workflow_transition(workflow.state, WorkflowState.DORMANT)

    workflow.state = WorkflowState.DORMANT
    workflow.started_at = None
    workflow.completed_at = None

    # Reset all activity instances to dormant
    ai_result = await db.execute(
        select(ActivityInstance).where(
            ActivityInstance.workflow_instance_id == workflow_id,
        )
    )
    for ai in ai_result.scalars().all():
        ai.state = ActivityState.DORMANT
        ai.started_at = None
        ai.completed_at = None

    # Delete work item comments first (FK constraint)
    work_item_subq = select(WorkItem.id).join(ActivityInstance).where(
        ActivityInstance.workflow_instance_id == workflow_id
    )
    await db.execute(
        delete(WorkItemComment).where(
            WorkItemComment.work_item_id.in_(work_item_subq)
        )
    )

    # Delete all work items for this workflow (hard delete)
    await db.execute(
        delete(WorkItem).where(
            WorkItem.activity_instance_id.in_(
                select(ActivityInstance.id).where(
                    ActivityInstance.workflow_instance_id == workflow_id
                )
            )
        )
    )

    # Delete all execution tokens (hard delete)
    await db.execute(
        delete(ExecutionToken).where(
            ExecutionToken.workflow_instance_id == workflow_id
        )
    )

    await create_audit_record(
        db,
        entity_type="workflow",
        entity_id=str(workflow_id),
        action="workflow_restarted",
        user_id=admin_id,
        before_state={"state": "failed"},
        after_state={"state": "dormant"},
        details="Work items and tokens deleted. Variables and packages preserved.",
    )

    await db.flush()
    return workflow


async def list_workflows_filtered(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    state_filter: str | None = None,
    template_id: uuid.UUID | None = None,
    created_by: uuid.UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> tuple[list[dict], int]:
    """List workflows with admin filters, returning enriched dicts."""
    conditions = [WorkflowInstance.is_deleted == False]  # noqa: E712

    if state_filter:
        conditions.append(WorkflowInstance.state == WorkflowState(state_filter))
    if template_id:
        conditions.append(WorkflowInstance.process_template_id == template_id)
    if created_by:
        conditions.append(WorkflowInstance.supervisor_id == created_by)
    if date_from:
        conditions.append(WorkflowInstance.created_at >= date_from)
    if date_to:
        conditions.append(WorkflowInstance.created_at <= date_to)

    # Count total
    count_query = select(func.count()).select_from(
        select(WorkflowInstance.id).where(*conditions).subquery()
    )
    count_result = await db.execute(count_query)
    total_count = count_result.scalar_one()

    # Fetch workflows with template join
    query = (
        select(WorkflowInstance, ProcessTemplate.name.label("template_name"))
        .join(
            ProcessTemplate,
            WorkflowInstance.process_template_id == ProcessTemplate.id,
        )
        .where(*conditions)
        .order_by(WorkflowInstance.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    rows = result.all()

    workflows = []
    for workflow, template_name in rows:
        # Find started_by username
        started_by_username = None
        if workflow.supervisor_id:
            user_result = await db.execute(
                select(User.username).where(User.id == workflow.supervisor_id)
            )
            started_by_username = user_result.scalar_one_or_none()

        # Find active activity name
        active_activity_name = None
        active_ai_result = await db.execute(
            select(ActivityTemplate.name)
            .join(
                ActivityInstance,
                ActivityInstance.activity_template_id == ActivityTemplate.id,
            )
            .where(
                ActivityInstance.workflow_instance_id == workflow.id,
                ActivityInstance.state == ActivityState.ACTIVE,
            )
            .limit(1)
        )
        active_activity_name = active_ai_result.scalar_one_or_none()

        workflows.append(
            {
                "id": workflow.id,
                "process_template_id": workflow.process_template_id,
                "state": workflow.state,
                "started_at": workflow.started_at,
                "completed_at": workflow.completed_at,
                "supervisor_id": workflow.supervisor_id,
                "template_name": template_name,
                "started_by_username": started_by_username,
                "active_activity_name": active_activity_name,
                "created_at": workflow.created_at,
                "updated_at": workflow.updated_at,
            }
        )

    return workflows, total_count
