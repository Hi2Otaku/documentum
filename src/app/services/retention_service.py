import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.retention import DocumentRetention, LegalHold, RetentionPolicy
from app.services.audit_service import create_audit_record


# ---------------------------------------------------------------------------
# Retention Policy CRUD
# ---------------------------------------------------------------------------

async def create_retention_policy(
    db: AsyncSession,
    name: str,
    retention_period_days: int,
    disposition_action: str,
    description: str | None,
    user_id: str,
) -> RetentionPolicy:
    policy = RetentionPolicy(
        name=name,
        description=description,
        retention_period_days=retention_period_days,
        disposition_action=disposition_action,
        created_by=user_id,
    )
    db.add(policy)
    await db.flush()

    await create_audit_record(
        db,
        entity_type="retention_policy",
        entity_id=str(policy.id),
        action="create",
        user_id=user_id,
        after_state={"name": name, "retention_period_days": retention_period_days, "disposition_action": disposition_action},
    )
    return policy


async def list_retention_policies(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[RetentionPolicy], int]:
    base = select(RetentionPolicy).where(RetentionPolicy.is_deleted == False)  # noqa: E712
    count_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(
        base.order_by(RetentionPolicy.created_at.desc()).offset(offset).limit(page_size)
    )
    return list(result.scalars().all()), total


async def get_retention_policy(
    db: AsyncSession,
    policy_id: uuid.UUID,
) -> RetentionPolicy:
    result = await db.execute(
        select(RetentionPolicy).where(
            RetentionPolicy.id == policy_id,
            RetentionPolicy.is_deleted == False,  # noqa: E712
        )
    )
    policy = result.scalar_one_or_none()
    if policy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Retention policy not found")
    return policy


async def update_retention_policy(
    db: AsyncSession,
    policy_id: uuid.UUID,
    name: str | None,
    description: str | None,
    retention_period_days: int | None,
    disposition_action: str | None,
    user_id: str,
) -> RetentionPolicy:
    policy = await get_retention_policy(db, policy_id)
    before = {"name": policy.name, "retention_period_days": policy.retention_period_days, "disposition_action": policy.disposition_action}

    if name is not None:
        policy.name = name
    if description is not None:
        policy.description = description
    if retention_period_days is not None:
        policy.retention_period_days = retention_period_days
    if disposition_action is not None:
        policy.disposition_action = disposition_action

    await db.flush()

    await create_audit_record(
        db,
        entity_type="retention_policy",
        entity_id=str(policy_id),
        action="update",
        user_id=user_id,
        before_state=before,
        after_state={"name": policy.name, "retention_period_days": policy.retention_period_days, "disposition_action": policy.disposition_action},
    )
    return policy


async def delete_retention_policy(
    db: AsyncSession,
    policy_id: uuid.UUID,
    user_id: str,
) -> None:
    policy = await get_retention_policy(db, policy_id)
    policy.is_deleted = True
    await db.flush()

    await create_audit_record(
        db,
        entity_type="retention_policy",
        entity_id=str(policy_id),
        action="delete",
        user_id=user_id,
    )


# ---------------------------------------------------------------------------
# Document-Policy Assignment
# ---------------------------------------------------------------------------

async def assign_policy_to_document(
    db: AsyncSession,
    document_id: uuid.UUID,
    policy_id: uuid.UUID,
    user_id: str,
) -> DocumentRetention:
    # Verify document exists
    from app.services.document_service import get_document
    await get_document(db, document_id)

    policy = await get_retention_policy(db, policy_id)

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=policy.retention_period_days)

    assignment = DocumentRetention(
        document_id=document_id,
        policy_id=policy_id,
        applied_at=now,
        expires_at=expires_at,
        created_by=user_id,
    )
    db.add(assignment)
    await db.flush()

    await create_audit_record(
        db,
        entity_type="document_retention",
        entity_id=str(assignment.id),
        action="assign",
        user_id=user_id,
        after_state={
            "document_id": str(document_id),
            "policy_id": str(policy_id),
            "policy_name": policy.name,
            "expires_at": expires_at.isoformat(),
        },
    )
    return assignment


async def remove_policy_from_document(
    db: AsyncSession,
    document_id: uuid.UUID,
    retention_id: uuid.UUID,
    user_id: str,
) -> None:
    result = await db.execute(
        select(DocumentRetention).where(
            DocumentRetention.id == retention_id,
            DocumentRetention.document_id == document_id,
            DocumentRetention.is_deleted == False,  # noqa: E712
        )
    )
    assignment = result.scalar_one_or_none()
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document retention assignment not found")

    assignment.is_deleted = True
    await db.flush()

    await create_audit_record(
        db,
        entity_type="document_retention",
        entity_id=str(retention_id),
        action="remove",
        user_id=user_id,
    )


async def get_document_retentions(
    db: AsyncSession,
    document_id: uuid.UUID,
) -> list[DocumentRetention]:
    result = await db.execute(
        select(DocumentRetention)
        .options(joinedload(DocumentRetention.policy))
        .where(
            DocumentRetention.document_id == document_id,
            DocumentRetention.is_deleted == False,  # noqa: E712
        )
        .order_by(DocumentRetention.applied_at.desc())
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Legal Holds
# ---------------------------------------------------------------------------

async def place_legal_hold(
    db: AsyncSession,
    document_id: uuid.UUID,
    reason: str,
    user_id: str,
) -> LegalHold:
    from app.services.document_service import get_document
    await get_document(db, document_id)

    now = datetime.now(timezone.utc)
    hold = LegalHold(
        document_id=document_id,
        reason=reason,
        placed_by=uuid.UUID(user_id),
        placed_at=now,
        created_by=user_id,
    )
    db.add(hold)
    await db.flush()

    await create_audit_record(
        db,
        entity_type="legal_hold",
        entity_id=str(hold.id),
        action="place",
        user_id=user_id,
        after_state={"document_id": str(document_id), "reason": reason},
    )
    return hold


async def release_legal_hold(
    db: AsyncSession,
    document_id: uuid.UUID,
    hold_id: uuid.UUID,
    user_id: str,
) -> LegalHold:
    result = await db.execute(
        select(LegalHold).where(
            LegalHold.id == hold_id,
            LegalHold.document_id == document_id,
            LegalHold.released_at == None,  # noqa: E711
        )
    )
    hold = result.scalar_one_or_none()
    if hold is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active legal hold not found")

    hold.released_at = datetime.now(timezone.utc)
    await db.flush()

    await create_audit_record(
        db,
        entity_type="legal_hold",
        entity_id=str(hold_id),
        action="release",
        user_id=user_id,
    )
    return hold


async def get_active_legal_holds(
    db: AsyncSession,
    document_id: uuid.UUID,
) -> list[LegalHold]:
    result = await db.execute(
        select(LegalHold).where(
            LegalHold.document_id == document_id,
            LegalHold.released_at == None,  # noqa: E711
        ).order_by(LegalHold.placed_at.desc())
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Deletion Guard
# ---------------------------------------------------------------------------

async def check_document_deletable(
    db: AsyncSession,
    document_id: uuid.UUID,
) -> tuple[bool, str | None]:
    """Check whether a document can be deleted.

    Returns (True, None) if deletable, or (False, reason) if blocked.
    """
    now = datetime.now(timezone.utc)

    # Check active (non-expired) retentions
    retention_result = await db.execute(
        select(func.count()).select_from(
            select(DocumentRetention).where(
                DocumentRetention.document_id == document_id,
                DocumentRetention.is_deleted == False,  # noqa: E712
                DocumentRetention.expires_at > now,
            ).subquery()
        )
    )
    active_retentions = retention_result.scalar_one()

    if active_retentions > 0:
        return False, f"Document is under active retention ({active_retentions} active policy assignment(s))"

    # Check active legal holds
    hold_result = await db.execute(
        select(func.count()).select_from(
            select(LegalHold).where(
                LegalHold.document_id == document_id,
                LegalHold.released_at == None,  # noqa: E711
            ).subquery()
        )
    )
    active_holds = hold_result.scalar_one()

    if active_holds > 0:
        return False, f"Document is under legal hold ({active_holds} active hold(s))"

    return True, None
