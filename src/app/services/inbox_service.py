"""Inbox service layer.

Implements business logic for the user inbox: listing work items with nested
context, acquiring/releasing items, completing (via engine delegation), rejecting,
and work-item comments.
"""
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import WorkItemState
from app.models.workflow import (
    ActivityInstance,
    ProcessTemplate,
    WorkflowInstance,
    WorkflowPackage,
    WorkItem,
    WorkItemComment,
)
from app.services.audit_service import create_audit_record

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. List inbox items (paginated, filtered, sorted)
# ---------------------------------------------------------------------------


async def get_inbox_items(
    db: AsyncSession,
    user_id: str,
    skip: int = 0,
    limit: int = 20,
    state_filter: str | None = None,
    priority_filter: int | None = None,
    template_name_filter: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> tuple[list[dict], int]:
    """Return paginated inbox items for a user with optional filters and sorting.

    Returns (items_as_dicts, total_count).
    """
    # Base WHERE clause
    conditions = [
        WorkItem.performer_id == uuid.UUID(user_id),
        WorkItem.is_deleted == False,  # noqa: E712
    ]

    if state_filter:
        conditions.append(WorkItem.state == state_filter)
    if priority_filter is not None:
        conditions.append(WorkItem.priority == priority_filter)

    # Build base query (joins needed for template_name filter)
    base_query = select(WorkItem).join(
        ActivityInstance, WorkItem.activity_instance_id == ActivityInstance.id
    ).join(
        WorkflowInstance, ActivityInstance.workflow_instance_id == WorkflowInstance.id
    ).join(
        ProcessTemplate, WorkflowInstance.process_template_id == ProcessTemplate.id
    ).where(*conditions)

    if template_name_filter:
        base_query = base_query.where(
            ProcessTemplate.name.ilike(f"%{template_name_filter}%")
        )

    # Count query
    count_query = select(func.count()).select_from(base_query.subquery())
    count_result = await db.execute(count_query)
    total_count = count_result.scalar_one()

    # Sort
    valid_sort_fields = {
        "priority": WorkItem.priority,
        "due_date": WorkItem.due_date,
        "created_at": WorkItem.created_at,
    }
    sort_column = valid_sort_fields.get(sort_by, WorkItem.created_at)
    if sort_order == "asc":
        base_query = base_query.order_by(sort_column.asc())
    else:
        base_query = base_query.order_by(sort_column.desc())

    # Eager loading
    base_query = base_query.options(
        selectinload(WorkItem.activity_instance)
        .selectinload(ActivityInstance.activity_template),
        selectinload(WorkItem.activity_instance)
        .selectinload(ActivityInstance.workflow_instance)
        .selectinload(WorkflowInstance.process_template),
        selectinload(WorkItem.activity_instance)
        .selectinload(ActivityInstance.workflow_instance)
        .selectinload(WorkflowInstance.workflow_packages),
        selectinload(WorkItem.comments),
    )

    base_query = base_query.offset(skip).limit(limit)
    result = await db.execute(base_query)
    work_items = list(result.scalars().unique().all())

    items = []
    for wi in work_items:
        ai = wi.activity_instance
        at = ai.activity_template
        wf = ai.workflow_instance
        pt = wf.process_template
        items.append({
            "id": wi.id,
            "state": wi.state,
            "priority": wi.priority,
            "due_date": wi.due_date,
            "instructions": wi.instructions,
            "performer_id": wi.performer_id,
            "created_at": wi.created_at,
            "completed_at": wi.completed_at,
            "activity": {
                "name": at.name,
                "activity_type": at.activity_type.value,
                "instructions": at.description,
            },
            "workflow": {
                "id": wf.id,
                "template_name": pt.name,
                "state": wf.state,
            },
            "documents": [
                {"document_id": p.document_id, "package_name": p.package_name}
                for p in wf.workflow_packages
            ],
            "comment_count": len(wi.comments),
        })

    return items, total_count


# ---------------------------------------------------------------------------
# 2. Get single inbox item detail
# ---------------------------------------------------------------------------


async def get_inbox_item_detail(
    db: AsyncSession,
    work_item_id: uuid.UUID,
    user_id: str,
) -> dict:
    """Load a single work item with full nested context and comments."""
    result = await db.execute(
        select(WorkItem)
        .options(
            selectinload(WorkItem.activity_instance)
            .selectinload(ActivityInstance.activity_template),
            selectinload(WorkItem.activity_instance)
            .selectinload(ActivityInstance.workflow_instance)
            .selectinload(WorkflowInstance.process_template),
            selectinload(WorkItem.activity_instance)
            .selectinload(ActivityInstance.workflow_instance)
            .selectinload(WorkflowInstance.workflow_packages),
            selectinload(WorkItem.comments),
        )
        .where(
            WorkItem.id == work_item_id,
            WorkItem.is_deleted == False,  # noqa: E712
        )
    )
    wi = result.scalar_one_or_none()
    if wi is None:
        raise ValueError("Work item not found")
    if wi.performer_id != uuid.UUID(user_id):
        raise ValueError("Not authorized to view this work item")

    ai = wi.activity_instance
    at = ai.activity_template
    wf = ai.workflow_instance
    pt = wf.process_template

    return {
        "id": wi.id,
        "state": wi.state,
        "priority": wi.priority,
        "due_date": wi.due_date,
        "instructions": wi.instructions,
        "performer_id": wi.performer_id,
        "created_at": wi.created_at,
        "completed_at": wi.completed_at,
        "activity": {
            "name": at.name,
            "activity_type": at.activity_type.value,
            "instructions": at.description,
        },
        "workflow": {
            "id": wf.id,
            "template_name": pt.name,
            "state": wf.state,
        },
        "documents": [
            {"document_id": p.document_id, "package_name": p.package_name}
            for p in wf.workflow_packages
        ],
        "comment_count": len(wi.comments),
        "comments": [
            {
                "id": c.id,
                "user_id": c.user_id,
                "content": c.content,
                "created_at": c.created_at,
            }
            for c in wi.comments
        ],
    }


# ---------------------------------------------------------------------------
# 3. Acquire work item (SELECT FOR UPDATE)
# ---------------------------------------------------------------------------


async def acquire_work_item(
    db: AsyncSession,
    work_item_id: uuid.UUID,
    user_id: str,
) -> WorkItem:
    """Acquire an AVAILABLE work item with row-level locking."""
    result = await db.execute(
        select(WorkItem)
        .with_for_update()
        .where(
            WorkItem.id == work_item_id,
            WorkItem.is_deleted == False,  # noqa: E712
        )
    )
    wi = result.scalar_one_or_none()
    if wi is None:
        raise ValueError("Work item not found")
    if wi.state != WorkItemState.AVAILABLE:
        raise ValueError(
            f"Cannot acquire work item in state '{wi.state.value}'; must be 'available'"
        )

    wi.state = WorkItemState.ACQUIRED
    wi.performer_id = uuid.UUID(user_id)

    await create_audit_record(
        db,
        entity_type="work_item",
        entity_id=str(wi.id),
        action="work_item_acquired",
        user_id=user_id,
        after_state={"state": WorkItemState.ACQUIRED.value, "performer_id": user_id},
    )

    await db.flush()
    return wi


# ---------------------------------------------------------------------------
# 4. Release work item
# ---------------------------------------------------------------------------


async def release_work_item(
    db: AsyncSession,
    work_item_id: uuid.UUID,
    user_id: str,
) -> WorkItem:
    """Release an ACQUIRED work item back to AVAILABLE."""
    result = await db.execute(
        select(WorkItem).where(
            WorkItem.id == work_item_id,
            WorkItem.is_deleted == False,  # noqa: E712
        )
    )
    wi = result.scalar_one_or_none()
    if wi is None:
        raise ValueError("Work item not found")
    if wi.state != WorkItemState.ACQUIRED:
        raise ValueError(
            f"Cannot release work item in state '{wi.state.value}'; must be 'acquired'"
        )
    if wi.performer_id != uuid.UUID(user_id):
        raise ValueError("Not authorized to release this work item")

    before_performer = str(wi.performer_id) if wi.performer_id else None
    wi.state = WorkItemState.AVAILABLE
    wi.performer_id = None

    await create_audit_record(
        db,
        entity_type="work_item",
        entity_id=str(wi.id),
        action="work_item_released",
        user_id=user_id,
        before_state={"state": WorkItemState.ACQUIRED.value, "performer_id": before_performer},
        after_state={"state": WorkItemState.AVAILABLE.value, "performer_id": None},
    )

    await db.flush()
    return wi


# ---------------------------------------------------------------------------
# 5. Complete inbox item (delegates to engine_service)
# ---------------------------------------------------------------------------


async def complete_inbox_item(
    db: AsyncSession,
    work_item_id: uuid.UUID,
    user_id: str,
    output_variables: dict | None = None,
) -> WorkItem:
    """Complete a work item and advance the workflow via engine_service."""
    from app.services import engine_service

    result = await db.execute(
        select(WorkItem)
        .options(selectinload(WorkItem.activity_instance))
        .where(
            WorkItem.id == work_item_id,
            WorkItem.is_deleted == False,  # noqa: E712
        )
    )
    wi = result.scalar_one_or_none()
    if wi is None:
        raise ValueError("Work item not found")
    if wi.state != WorkItemState.ACQUIRED:
        raise ValueError(
            f"Cannot complete work item in state '{wi.state.value}'; must be 'acquired'"
        )
    if wi.performer_id != uuid.UUID(user_id):
        raise ValueError("Not authorized to complete this work item")

    workflow_instance_id = wi.activity_instance.workflow_instance_id

    return await engine_service.complete_work_item(
        db, workflow_instance_id, work_item_id, user_id, output_variables
    )


# ---------------------------------------------------------------------------
# 6. Reject work item
# ---------------------------------------------------------------------------


async def reject_inbox_item(
    db: AsyncSession,
    work_item_id: uuid.UUID,
    user_id: str,
    reason: str | None = None,
) -> WorkItem:
    """Reject an acquired work item."""
    result = await db.execute(
        select(WorkItem).where(
            WorkItem.id == work_item_id,
            WorkItem.is_deleted == False,  # noqa: E712
        )
    )
    wi = result.scalar_one_or_none()
    if wi is None:
        raise ValueError("Work item not found")
    if wi.state != WorkItemState.ACQUIRED:
        raise ValueError(
            f"Cannot reject work item in state '{wi.state.value}'; must be 'acquired'"
        )
    if wi.performer_id != uuid.UUID(user_id):
        raise ValueError("Not authorized to reject this work item")

    wi.state = WorkItemState.REJECTED
    wi.completed_at = datetime.now(timezone.utc)

    after_state: dict = {"state": WorkItemState.REJECTED.value}
    if reason:
        after_state["reason"] = reason

    await create_audit_record(
        db,
        entity_type="work_item",
        entity_id=str(wi.id),
        action="work_item_rejected",
        user_id=user_id,
        after_state=after_state,
    )

    await db.flush()
    return wi


# ---------------------------------------------------------------------------
# 7. Add comment
# ---------------------------------------------------------------------------


async def add_comment(
    db: AsyncSession,
    work_item_id: uuid.UUID,
    user_id: str,
    content: str,
) -> WorkItemComment:
    """Add a comment to a work item."""
    # Verify work item exists
    result = await db.execute(
        select(WorkItem).where(
            WorkItem.id == work_item_id,
            WorkItem.is_deleted == False,  # noqa: E712
        )
    )
    wi = result.scalar_one_or_none()
    if wi is None:
        raise ValueError("Work item not found")

    comment = WorkItemComment(
        work_item_id=work_item_id,
        user_id=uuid.UUID(user_id),
        content=content,
        created_by=user_id,
    )
    db.add(comment)

    await create_audit_record(
        db,
        entity_type="work_item",
        entity_id=str(work_item_id),
        action="work_item_comment_added",
        user_id=user_id,
        after_state={"content": content[:200]},
    )

    await db.flush()
    return comment


# ---------------------------------------------------------------------------
# 8. Get comments
# ---------------------------------------------------------------------------


async def get_comments(
    db: AsyncSession,
    work_item_id: uuid.UUID,
) -> list[WorkItemComment]:
    """List all comments for a work item, ordered by created_at ascending."""
    result = await db.execute(
        select(WorkItemComment)
        .where(WorkItemComment.work_item_id == work_item_id)
        .order_by(WorkItemComment.created_at.asc())
    )
    return list(result.scalars().all())
