"""Work queue service layer.

Implements CRUD operations for work queues and queue member management.
"""
import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.workflow import WorkQueue, work_queue_members
from app.schemas.queue import WorkQueueCreate, WorkQueueUpdate
from app.services.audit_service import create_audit_record


async def create_queue(
    db: AsyncSession, data: WorkQueueCreate, user_id: str
) -> WorkQueue:
    """Create a new work queue. Raises ValueError if name exists."""
    existing = await db.execute(
        select(WorkQueue).where(
            WorkQueue.name == data.name,
            WorkQueue.is_deleted == False,  # noqa: E712
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError(f"Queue with name '{data.name}' already exists")

    queue = WorkQueue(
        name=data.name,
        description=data.description,
        created_by=user_id,
    )
    db.add(queue)
    await db.flush()

    await create_audit_record(
        db,
        entity_type="work_queue",
        entity_id=str(queue.id),
        action="queue_created",
        user_id=user_id,
        after_state={"name": data.name},
    )

    return queue


async def get_queues(
    db: AsyncSession, skip: int = 0, limit: int = 20
) -> tuple[list[WorkQueue], int]:
    """List active queues with pagination."""
    base_query = select(WorkQueue).where(
        WorkQueue.is_deleted == False,  # noqa: E712
    )

    count_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total_count = count_result.scalar_one()

    result = await db.execute(
        base_query.options(selectinload(WorkQueue.members))
        .order_by(WorkQueue.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    queues = list(result.scalars().unique().all())

    return queues, total_count


async def get_queue(db: AsyncSession, queue_id: uuid.UUID) -> WorkQueue:
    """Get queue with members loaded. Raises ValueError if not found."""
    result = await db.execute(
        select(WorkQueue)
        .options(selectinload(WorkQueue.members))
        .where(
            WorkQueue.id == queue_id,
            WorkQueue.is_deleted == False,  # noqa: E712
        )
    )
    queue = result.scalar_one_or_none()
    if queue is None:
        raise ValueError("Queue not found")
    return queue


async def update_queue(
    db: AsyncSession, queue_id: uuid.UUID, data: WorkQueueUpdate, user_id: str
) -> WorkQueue:
    """Update queue name/description."""
    queue = await get_queue(db, queue_id)

    before_state = {"name": queue.name, "description": queue.description}

    if data.name is not None:
        # Check uniqueness if name changed
        if data.name != queue.name:
            existing = await db.execute(
                select(WorkQueue).where(
                    WorkQueue.name == data.name,
                    WorkQueue.is_deleted == False,  # noqa: E712
                    WorkQueue.id != queue_id,
                )
            )
            if existing.scalar_one_or_none():
                raise ValueError(f"Queue with name '{data.name}' already exists")
        queue.name = data.name
    if data.description is not None:
        queue.description = data.description

    await create_audit_record(
        db,
        entity_type="work_queue",
        entity_id=str(queue.id),
        action="queue_updated",
        user_id=user_id,
        before_state=before_state,
        after_state={"name": queue.name, "description": queue.description},
    )

    await db.flush()
    return queue


async def delete_queue(
    db: AsyncSession, queue_id: uuid.UUID, user_id: str
) -> None:
    """Soft-delete a queue."""
    queue = await get_queue(db, queue_id)
    queue.is_deleted = True

    await create_audit_record(
        db,
        entity_type="work_queue",
        entity_id=str(queue.id),
        action="queue_deleted",
        user_id=user_id,
        after_state={"name": queue.name},
    )

    await db.flush()


async def add_member(
    db: AsyncSession, queue_id: uuid.UUID, member_user_id: uuid.UUID, user_id: str
) -> None:
    """Add a user to a queue. Raises ValueError if already member or user not found."""
    # Verify queue exists
    queue = await get_queue(db, queue_id)

    # Verify user exists
    user = await db.get(User, member_user_id)
    if user is None or user.is_deleted:
        raise ValueError("User not found")

    # Check not already member
    existing = await db.execute(
        select(work_queue_members).where(
            work_queue_members.c.queue_id == queue_id,
            work_queue_members.c.user_id == member_user_id,
        )
    )
    if existing.first() is not None:
        raise ValueError("User is already a member of this queue")

    # Insert membership
    await db.execute(
        work_queue_members.insert().values(
            queue_id=queue_id, user_id=member_user_id
        )
    )

    await create_audit_record(
        db,
        entity_type="work_queue",
        entity_id=str(queue.id),
        action="queue_member_added",
        user_id=user_id,
        after_state={"member_user_id": str(member_user_id)},
    )

    await db.flush()


async def remove_member(
    db: AsyncSession, queue_id: uuid.UUID, member_user_id: uuid.UUID, user_id: str
) -> None:
    """Remove a user from a queue."""
    # Verify queue exists
    queue = await get_queue(db, queue_id)

    # Check membership exists
    existing = await db.execute(
        select(work_queue_members).where(
            work_queue_members.c.queue_id == queue_id,
            work_queue_members.c.user_id == member_user_id,
        )
    )
    if existing.first() is None:
        raise ValueError("User is not a member of this queue")

    await db.execute(
        delete(work_queue_members).where(
            work_queue_members.c.queue_id == queue_id,
            work_queue_members.c.user_id == member_user_id,
        )
    )

    await create_audit_record(
        db,
        entity_type="work_queue",
        entity_id=str(queue.id),
        action="queue_member_removed",
        user_id=user_id,
        after_state={"member_user_id": str(member_user_id)},
    )

    await db.flush()
