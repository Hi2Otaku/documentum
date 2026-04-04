"""Query builder functions for admin search across workflows, work items, documents."""
import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.document import Document
from app.models.enums import ActivityState
from app.models.user import User
from app.models.workflow import (
    ActivityInstance,
    ActivityTemplate,
    ProcessTemplate,
    WorkflowInstance,
    WorkItem,
)
from app.schemas.query import (
    DocumentQueryResponse,
    WorkflowQueryResponse,
    WorkItemQueryResponse,
)


async def query_workflows(
    db: AsyncSession,
    template_id: uuid.UUID | None = None,
    state: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    started_by: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[WorkflowQueryResponse], int]:
    """Query workflow instances with multi-criteria filtering."""
    conditions = []

    if template_id:
        conditions.append(WorkflowInstance.process_template_id == template_id)
    if state:
        conditions.append(WorkflowInstance.state == state)
    if date_from:
        conditions.append(WorkflowInstance.created_at >= date_from)
    if date_to:
        conditions.append(WorkflowInstance.created_at <= date_to)
    if started_by:
        conditions.append(WorkflowInstance.supervisor_id == started_by)

    base_query = (
        select(WorkflowInstance)
        .where(*conditions)
        if conditions
        else select(WorkflowInstance)
    )

    # Count
    count_query = select(func.count()).select_from(base_query.subquery())
    count_result = await db.execute(count_query)
    total_count = count_result.scalar_one()

    # Fetch with eager-loading of relationships we need
    result = await db.execute(
        base_query.options(
            selectinload(WorkflowInstance.process_template),
            selectinload(WorkflowInstance.activity_instances).selectinload(
                ActivityInstance.activity_template
            ),
        )
        .order_by(WorkflowInstance.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    workflows = list(result.scalars().all())

    # Build response objects
    items = []
    for wf in workflows:
        # Find active activity name
        active_activity = None
        for ai in wf.activity_instances:
            if ai.state == ActivityState.ACTIVE:
                active_activity = ai.activity_template.name
                break

        # Get supervisor username
        started_by_name = None
        if wf.supervisor_id:
            user_result = await db.execute(
                select(User).where(User.id == wf.supervisor_id)
            )
            user = user_result.scalar_one_or_none()
            if user:
                started_by_name = user.username

        items.append(
            WorkflowQueryResponse(
                id=str(wf.id),
                template_name=wf.process_template.name,
                template_version=wf.process_template.version,
                state=wf.state.value if hasattr(wf.state, "value") else str(wf.state),
                started_by=started_by_name,
                started_at=wf.started_at.isoformat() if wf.started_at else None,
                completed_at=wf.completed_at.isoformat() if wf.completed_at else None,
                active_activity=active_activity,
            )
        )

    return items, total_count


async def query_work_items(
    db: AsyncSession,
    assignee_id: uuid.UUID | None = None,
    state: str | None = None,
    workflow_id: uuid.UUID | None = None,
    priority: int | None = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[WorkItemQueryResponse], int]:
    """Query work items with multi-criteria filtering."""
    conditions = []

    if assignee_id:
        conditions.append(WorkItem.performer_id == assignee_id)
    if state:
        conditions.append(WorkItem.state == state)
    if priority is not None:
        conditions.append(WorkItem.priority == priority)

    # If filtering by workflow_id, join through activity_instances
    if workflow_id:
        conditions.append(ActivityInstance.workflow_instance_id == workflow_id)
        base_query = (
            select(WorkItem)
            .join(ActivityInstance, WorkItem.activity_instance_id == ActivityInstance.id)
            .where(*conditions)
        )
    else:
        base_query = (
            select(WorkItem).where(*conditions) if conditions else select(WorkItem)
        )

    # Count
    count_query = select(func.count()).select_from(base_query.subquery())
    count_result = await db.execute(count_query)
    total_count = count_result.scalar_one()

    # Fetch with eager-loading
    result = await db.execute(
        base_query.options(
            selectinload(WorkItem.activity_instance).selectinload(
                ActivityInstance.activity_template
            ),
            selectinload(WorkItem.activity_instance).selectinload(
                ActivityInstance.workflow_instance
            ).selectinload(WorkflowInstance.process_template),
        )
        .order_by(WorkItem.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    work_items = list(result.scalars().all())

    items = []
    for wi in work_items:
        ai = wi.activity_instance
        wf = ai.workflow_instance
        tmpl = wf.process_template

        # Get assignee username
        assignee_name = None
        if wi.performer_id:
            user_result = await db.execute(
                select(User).where(User.id == wi.performer_id)
            )
            user = user_result.scalar_one_or_none()
            if user:
                assignee_name = user.username

        items.append(
            WorkItemQueryResponse(
                id=str(wi.id),
                activity_name=ai.activity_template.name,
                workflow_name=f"{tmpl.name} ({str(wf.id)[:8]})",
                workflow_id=str(wf.id),
                assignee=assignee_name,
                state=wi.state.value if hasattr(wi.state, "value") else str(wi.state),
                priority=wi.priority,
                created_at=wi.created_at.isoformat(),
            )
        )

    return items, total_count


async def query_documents(
    db: AsyncSession,
    lifecycle_state: str | None = None,
    metadata_key: str | None = None,
    metadata_value: str | None = None,
    version: str | None = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[DocumentQueryResponse], int]:
    """Query documents with multi-criteria filtering.

    metadata filtering is done in Python post-fetch for SQLite compatibility.
    """
    conditions = []

    if lifecycle_state:
        conditions.append(Document.lifecycle_state == lifecycle_state)

    base_query = (
        select(Document).where(*conditions) if conditions else select(Document)
    )

    # Fetch all matching docs (before metadata/version filtering)
    result = await db.execute(
        base_query.order_by(Document.created_at.desc())
    )
    all_docs = list(result.scalars().all())

    # Apply metadata filter in Python (SQLite JSON compatibility)
    if metadata_key and metadata_value:
        all_docs = [
            d for d in all_docs
            if d.custom_properties
            and d.custom_properties.get(metadata_key) == metadata_value
        ]

    # Apply version filter in Python (computed from two columns)
    if version:
        all_docs = [
            d for d in all_docs
            if f"{d.current_major_version}.{d.current_minor_version}" == version
        ]

    total_count = len(all_docs)
    paged_docs = all_docs[skip : skip + limit]

    items = []
    for doc in paged_docs:
        items.append(
            DocumentQueryResponse(
                id=str(doc.id),
                title=doc.title,
                lifecycle_state=(
                    doc.lifecycle_state.value
                    if hasattr(doc.lifecycle_state, "value")
                    else str(doc.lifecycle_state)
                )
                if doc.lifecycle_state
                else None,
                current_version=f"{doc.current_major_version}.{doc.current_minor_version}",
                author=doc.author,
                created_by=doc.created_by,
                updated_at=doc.updated_at.isoformat(),
                content_type=doc.content_type,
            )
        )

    return items, total_count
