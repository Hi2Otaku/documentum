import math
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_admin
from app.models.user import User
from app.schemas.common import EnvelopeResponse, PaginationMeta
from app.schemas.retention import (
    DocumentRetentionAssign,
    DocumentRetentionResponse,
    LegalHoldCreate,
    LegalHoldResponse,
    RetentionPolicyCreate,
    RetentionPolicyResponse,
    RetentionPolicyUpdate,
    RetentionStatusResponse,
)
from app.services import retention_service

router = APIRouter(tags=["retention"])


# ---------------------------------------------------------------------------
# Retention Policy CRUD
# ---------------------------------------------------------------------------

@router.post(
    "/retention-policies",
    response_model=EnvelopeResponse[RetentionPolicyResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_retention_policy(
    data: RetentionPolicyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Create a new retention policy (admin only)."""
    policy = await retention_service.create_retention_policy(
        db,
        name=data.name,
        retention_period_days=data.retention_period_days,
        disposition_action=data.disposition_action,
        description=data.description,
        user_id=str(current_user.id),
    )
    return EnvelopeResponse(data=RetentionPolicyResponse.model_validate(policy))


@router.get(
    "/retention-policies",
    response_model=EnvelopeResponse[list[RetentionPolicyResponse]],
)
async def list_retention_policies(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """List all retention policies with pagination (admin only)."""
    policies, total = await retention_service.list_retention_policies(db, page, page_size)
    return EnvelopeResponse(
        data=[RetentionPolicyResponse.model_validate(p) for p in policies],
        meta=PaginationMeta(
            page=page,
            page_size=page_size,
            total_count=total,
            total_pages=math.ceil(total / page_size) if page_size > 0 else 0,
        ),
    )


@router.get(
    "/retention-policies/{policy_id}",
    response_model=EnvelopeResponse[RetentionPolicyResponse],
)
async def get_retention_policy(
    policy_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Get a single retention policy by ID (admin only)."""
    policy = await retention_service.get_retention_policy(db, policy_id)
    return EnvelopeResponse(data=RetentionPolicyResponse.model_validate(policy))


@router.put(
    "/retention-policies/{policy_id}",
    response_model=EnvelopeResponse[RetentionPolicyResponse],
)
async def update_retention_policy(
    policy_id: uuid.UUID,
    data: RetentionPolicyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Update a retention policy (admin only)."""
    policy = await retention_service.update_retention_policy(
        db,
        policy_id=policy_id,
        name=data.name,
        description=data.description,
        retention_period_days=data.retention_period_days,
        disposition_action=data.disposition_action,
        user_id=str(current_user.id),
    )
    return EnvelopeResponse(data=RetentionPolicyResponse.model_validate(policy))


@router.delete(
    "/retention-policies/{policy_id}",
    response_model=EnvelopeResponse,
)
async def delete_retention_policy(
    policy_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Soft-delete a retention policy (admin only)."""
    await retention_service.delete_retention_policy(db, policy_id, str(current_user.id))
    return EnvelopeResponse(data=None, meta={"message": "Retention policy deleted"})


# ---------------------------------------------------------------------------
# Document-Policy Assignment
# ---------------------------------------------------------------------------

@router.post(
    "/documents/{document_id}/retention",
    response_model=EnvelopeResponse[DocumentRetentionResponse],
    status_code=status.HTTP_201_CREATED,
)
async def assign_retention_policy(
    document_id: uuid.UUID,
    data: DocumentRetentionAssign,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Assign a retention policy to a document (admin only)."""
    assignment = await retention_service.assign_policy_to_document(
        db,
        document_id=document_id,
        policy_id=data.policy_id,
        user_id=str(current_user.id),
    )
    resp = DocumentRetentionResponse.model_validate(assignment)
    resp.policy_name = (await retention_service.get_retention_policy(db, data.policy_id)).name
    return EnvelopeResponse(data=resp)


@router.delete(
    "/documents/{document_id}/retention/{retention_id}",
    response_model=EnvelopeResponse,
)
async def remove_retention_assignment(
    document_id: uuid.UUID,
    retention_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Remove a retention policy assignment from a document (admin only)."""
    await retention_service.remove_policy_from_document(db, document_id, retention_id, str(current_user.id))
    return EnvelopeResponse(data=None, meta={"message": "Retention assignment removed"})


# ---------------------------------------------------------------------------
# Legal Holds
# ---------------------------------------------------------------------------

@router.post(
    "/documents/{document_id}/legal-hold",
    response_model=EnvelopeResponse[LegalHoldResponse],
    status_code=status.HTTP_201_CREATED,
)
async def place_legal_hold(
    document_id: uuid.UUID,
    data: LegalHoldCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Place a legal hold on a document (admin only)."""
    hold = await retention_service.place_legal_hold(
        db,
        document_id=document_id,
        reason=data.reason,
        user_id=str(current_user.id),
    )
    return EnvelopeResponse(data=LegalHoldResponse.model_validate(hold))


@router.delete(
    "/documents/{document_id}/legal-hold/{hold_id}",
    response_model=EnvelopeResponse[LegalHoldResponse],
)
async def release_legal_hold(
    document_id: uuid.UUID,
    hold_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Release a legal hold from a document (admin only)."""
    hold = await retention_service.release_legal_hold(db, document_id, hold_id, str(current_user.id))
    return EnvelopeResponse(data=LegalHoldResponse.model_validate(hold))


# ---------------------------------------------------------------------------
# Retention Status
# ---------------------------------------------------------------------------

@router.get(
    "/documents/{document_id}/retention-status",
    response_model=EnvelopeResponse[RetentionStatusResponse],
)
async def get_retention_status(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Get combined retention and legal hold status for a document (admin only)."""
    from app.services.document_service import get_document
    await get_document(db, document_id)

    retentions = await retention_service.get_document_retentions(db, document_id)
    holds = await retention_service.get_active_legal_holds(db, document_id)
    deletable, reason = await retention_service.check_document_deletable(db, document_id)

    retention_responses = []
    for r in retentions:
        resp = DocumentRetentionResponse.model_validate(r)
        if r.policy:
            resp.policy_name = r.policy.name
        retention_responses.append(resp)

    return EnvelopeResponse(
        data=RetentionStatusResponse(
            document_id=document_id,
            is_retained=len(retentions) > 0,
            is_held=len(holds) > 0,
            is_deletable=deletable,
            deletion_blocked_reason=reason,
            active_retentions=retention_responses,
            active_holds=[LegalHoldResponse.model_validate(h) for h in holds],
        )
    )
