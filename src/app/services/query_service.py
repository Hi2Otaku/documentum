"""Admin query interface — multi-criteria search for workflows, work items, documents, and audit logs."""
import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.document import Document
from app.models.workflow import WorkflowInstance, WorkItem
from app.schemas.query import (
    AuditLogQueryRequest,
    AuditLogQueryResult,
    DocumentQueryRequest,
    DocumentQueryResult,
    WorkflowQueryRequest,
    WorkflowQueryResult,
    WorkItemQueryRequest,
    WorkItemQueryResult,
)

logger = logging.getLogger(__name__)


async def query_workflows(
    db: AsyncSession, filters: WorkflowQueryRequest
) -> tuple[list[WorkflowQueryResult], int]:
    """Query workflow instances with multi-criteria filtering."""
    stmt = select(WorkflowInstance).where(
        WorkflowInstance.is_deleted == False  # noqa: E712
    )

    if filters.template_id is not None:
        stmt = stmt.where(WorkflowInstance.process_template_id == filters.template_id)
    if filters.state is not None:
        stmt = stmt.where(WorkflowInstance.state == filters.state)
    if filters.supervisor_id is not None:
        stmt = stmt.where(WorkflowInstance.supervisor_id == filters.supervisor_id)
    if filters.started_after is not None:
        stmt = stmt.where(WorkflowInstance.started_at >= filters.started_after)
    if filters.started_before is not None:
        stmt = stmt.where(WorkflowInstance.started_at <= filters.started_before)
    if filters.completed_after is not None:
        stmt = stmt.where(WorkflowInstance.completed_at >= filters.completed_after)
    if filters.completed_before is not None:
        stmt = stmt.where(WorkflowInstance.completed_at <= filters.completed_before)

    # Count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    # Paginate
    stmt = stmt.order_by(WorkflowInstance.created_at.desc()).offset(filters.skip).limit(filters.limit)
    result = await db.execute(stmt)
    rows = list(result.scalars().all())

    return [WorkflowQueryResult.model_validate(r) for r in rows], total


async def query_work_items(
    db: AsyncSession, filters: WorkItemQueryRequest
) -> tuple[list[WorkItemQueryResult], int]:
    """Query work items with multi-criteria filtering."""
    stmt = select(WorkItem).where(
        WorkItem.is_deleted == False  # noqa: E712
    )

    if filters.performer_id is not None:
        stmt = stmt.where(WorkItem.performer_id == filters.performer_id)
    if filters.state is not None:
        stmt = stmt.where(WorkItem.state == filters.state)
    if filters.workflow_id is not None:
        from app.models.workflow import ActivityInstance
        stmt = stmt.join(
            ActivityInstance, WorkItem.activity_instance_id == ActivityInstance.id
        ).where(ActivityInstance.workflow_instance_id == filters.workflow_id)
    if filters.priority_min is not None:
        stmt = stmt.where(WorkItem.priority >= filters.priority_min)
    if filters.priority_max is not None:
        stmt = stmt.where(WorkItem.priority <= filters.priority_max)
    if filters.due_before is not None:
        stmt = stmt.where(WorkItem.due_date <= filters.due_before)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = stmt.order_by(WorkItem.created_at.desc()).offset(filters.skip).limit(filters.limit)
    result = await db.execute(stmt)
    rows = list(result.scalars().all())

    return [WorkItemQueryResult.model_validate(r) for r in rows], total


async def query_documents(
    db: AsyncSession, filters: DocumentQueryRequest
) -> tuple[list[DocumentQueryResult], int]:
    """Query documents with multi-criteria filtering."""
    stmt = select(Document).where(
        Document.is_deleted == False  # noqa: E712
    )

    if filters.title_contains is not None:
        stmt = stmt.where(Document.title.ilike(f"%{filters.title_contains}%"))
    if filters.author is not None:
        stmt = stmt.where(Document.author == filters.author)
    if filters.content_type is not None:
        stmt = stmt.where(Document.content_type == filters.content_type)
    if filters.lifecycle_state is not None:
        stmt = stmt.where(Document.lifecycle_state == filters.lifecycle_state)
    if filters.created_after is not None:
        stmt = stmt.where(Document.created_at >= filters.created_after)
    if filters.created_before is not None:
        stmt = stmt.where(Document.created_at <= filters.created_before)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = stmt.order_by(Document.created_at.desc()).offset(filters.skip).limit(filters.limit)
    result = await db.execute(stmt)
    rows = list(result.scalars().all())

    return [DocumentQueryResult.model_validate(r) for r in rows], total


async def query_audit_logs(
    db: AsyncSession, filters: AuditLogQueryRequest
) -> tuple[list[AuditLogQueryResult], int]:
    """Query audit logs with multi-criteria filtering."""
    stmt = select(AuditLog)

    if filters.entity_type is not None:
        stmt = stmt.where(AuditLog.entity_type == filters.entity_type)
    if filters.entity_id is not None:
        stmt = stmt.where(AuditLog.entity_id == filters.entity_id)
    if filters.action is not None:
        stmt = stmt.where(AuditLog.action == filters.action)
    if filters.user_id is not None:
        stmt = stmt.where(AuditLog.user_id == filters.user_id)
    if filters.after is not None:
        stmt = stmt.where(AuditLog.timestamp >= filters.after)
    if filters.before is not None:
        stmt = stmt.where(AuditLog.timestamp <= filters.before)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = stmt.order_by(AuditLog.timestamp.desc()).offset(filters.skip).limit(filters.limit)
    result = await db.execute(stmt)
    rows = list(result.scalars().all())

    return [AuditLogQueryResult.model_validate(r) for r in rows], total
