import math
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.retention import DocumentRetention, LegalHold, RetentionPolicy
from app.services.audit_service import create_audit_record


# === Retention Policy CRUD (RET-01) ===


async def create_retention_policy(
    db: AsyncSession,
    *,
    name: str,
    description: str | None,
    retention_period_days: int,
    disposition_action: str,
    user_id: str,
) -> RetentionPolicy:
    """Create a new retention policy."""
    policy = RetentionPolicy(
        id=uuid.uuid4(),
        name=name,
        description=description,
        retention_period_days=retention_period_days,
        disposition_action=disposition_action,
        is_active=True,
        created_by=user_id,
    )
    db.add(policy)
    await db.flush()

    await create_audit_record(
        db,
        entity_type="retention_policy",
        entity_id=str(policy.id),
        action="create_retention_policy",
        user_id=user_id,
    )

    return policy


async def list_retention_policies(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    is_active: bool | None = None,
) -> tuple[list[RetentionPolicy], int]:
    """List retention policies with pagination and optional active filter."""
    query = select(RetentionPolicy).where(
        RetentionPolicy.is_deleted == False,  # noqa: E712
    )

    if is_active is not None:
        query = query.where(RetentionPolicy.is_active == is_active)

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Paginate
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    policies = list(result.scalars().all())

    return policies, total


async def get_retention_policy(
    db: AsyncSession,
    policy_id: uuid.UUID,
) -> RetentionPolicy:
    """Get a single retention policy by ID. Raises 404 if not found."""
    result = await db.execute(
        select(RetentionPolicy).where(
            RetentionPolicy.id == policy_id,
            RetentionPolicy.is_deleted == False,  # noqa: E712
        )
    )
    policy = result.scalar_one_or_none()
    if policy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Retention policy not found",
        )
    return policy


async def update_retention_policy(
    db: AsyncSession,
    policy_id: uuid.UUID,
    *,
    name: str | None = None,
    description: str | None = None,
    retention_period_days: int | None = None,
    disposition_action: str | None = None,
    is_active: bool | None = None,
    user_id: str,
) -> RetentionPolicy:
    """Partial update of a retention policy."""
    policy = await get_retention_policy(db, policy_id)

    if name is not None:
        policy.name = name
    if description is not None:
        policy.description = description
    if retention_period_days is not None:
        policy.retention_period_days = retention_period_days
    if disposition_action is not None:
        policy.disposition_action = disposition_action
    if is_active is not None:
        policy.is_active = is_active

    await db.flush()

    await create_audit_record(
        db,
        entity_type="retention_policy",
        entity_id=str(policy.id),
        action="update_retention_policy",
        user_id=user_id,
    )

    return policy


async def delete_retention_policy(
    db: AsyncSession,
    policy_id: uuid.UUID,
    user_id: str,
) -> None:
    """Soft-delete a retention policy."""
    policy = await get_retention_policy(db, policy_id)
    policy.is_deleted = True
    await db.flush()

    await create_audit_record(
        db,
        entity_type="retention_policy",
        entity_id=str(policy.id),
        action="delete_retention_policy",
        user_id=user_id,
    )


# === Document Retention Assignment (RET-02) ===


async def assign_retention_to_document(
    db: AsyncSession,
    document_id: uuid.UUID,
    policy_id: uuid.UUID,
    user_id: str,
) -> DocumentRetention:
    """Assign a retention policy to a document."""
    from app.services.document_service import get_document

    # Verify document exists
    await get_document(db, document_id)

    # Verify policy exists and is active
    policy = await get_retention_policy(db, policy_id)
    if not policy.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Retention policy is not active",
        )

    # Check for duplicate
    existing = await db.execute(
        select(DocumentRetention).where(
            DocumentRetention.document_id == document_id,
            DocumentRetention.retention_policy_id == policy_id,
            DocumentRetention.is_deleted == False,  # noqa: E712
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Retention policy already assigned to this document",
        )

    now = datetime.now(timezone.utc)
    dr = DocumentRetention(
        id=uuid.uuid4(),
        document_id=document_id,
        retention_policy_id=policy_id,
        applied_at=now,
        expires_at=now + timedelta(days=policy.retention_period_days),
        applied_by=user_id,
        created_by=user_id,
    )
    db.add(dr)
    await db.flush()

    await create_audit_record(
        db,
        entity_type="document_retention",
        entity_id=str(dr.id),
        action="assign_retention",
        user_id=user_id,
        details=f"Assigned policy '{policy.name}' to document {document_id}",
    )

    # Eagerly load the relationship for the response
    await db.refresh(dr, attribute_names=["retention_policy"])

    return dr


async def list_document_retentions(
    db: AsyncSession,
    document_id: uuid.UUID,
) -> list[DocumentRetention]:
    """List all retention assignments for a document with eagerly loaded policy."""
    result = await db.execute(
        select(DocumentRetention)
        .where(
            DocumentRetention.document_id == document_id,
            DocumentRetention.is_deleted == False,  # noqa: E712
        )
        .options(selectinload(DocumentRetention.retention_policy))
    )
    return list(result.scalars().all())


async def remove_retention_from_document(
    db: AsyncSession,
    document_id: uuid.UUID,
    retention_id: uuid.UUID,
    user_id: str,
) -> None:
    """Soft-delete a document retention assignment."""
    result = await db.execute(
        select(DocumentRetention).where(
            DocumentRetention.id == retention_id,
            DocumentRetention.document_id == document_id,
            DocumentRetention.is_deleted == False,  # noqa: E712
        )
    )
    dr = result.scalar_one_or_none()
    if dr is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document retention assignment not found",
        )

    dr.is_deleted = True
    await db.flush()

    await create_audit_record(
        db,
        entity_type="document_retention",
        entity_id=str(retention_id),
        action="remove_retention",
        user_id=user_id,
    )
