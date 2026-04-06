import math
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_admin
from app.models.user import User
from app.schemas.common import EnvelopeResponse, PaginationMeta
from app.schemas.retention import (
    AssignRetentionRequest,
    DocumentRetentionResponse,
    RetentionPolicyCreate,
    RetentionPolicyResponse,
    RetentionPolicyUpdate,
)
from app.services import retention_service

router = APIRouter(prefix="/retention", tags=["retention"])


# === Policy CRUD endpoints (admin only) ===


@router.post(
    "/",
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
        description=data.description,
        retention_period_days=data.retention_period_days,
        disposition_action=data.disposition_action,
        user_id=str(current_user.id),
    )
    return EnvelopeResponse(data=RetentionPolicyResponse.model_validate(policy))


@router.get(
    "/",
    response_model=EnvelopeResponse[list[RetentionPolicyResponse]],
)
async def list_retention_policies(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_active: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """List retention policies with pagination (admin only)."""
    policies, total = await retention_service.list_retention_policies(
        db, page, page_size, is_active
    )
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
    "/{policy_id}",
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
    "/{policy_id}",
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
        policy_id,
        name=data.name,
        description=data.description,
        retention_period_days=data.retention_period_days,
        disposition_action=data.disposition_action,
        is_active=data.is_active,
        user_id=str(current_user.id),
    )
    return EnvelopeResponse(data=RetentionPolicyResponse.model_validate(policy))


@router.delete(
    "/{policy_id}",
    response_model=EnvelopeResponse,
)
async def delete_retention_policy(
    policy_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Delete a retention policy (admin only, soft delete)."""
    await retention_service.delete_retention_policy(
        db, policy_id, str(current_user.id)
    )
    return EnvelopeResponse(data=None, meta={"message": "Retention policy deleted"})


# === Document assignment endpoints (admin only) ===


@router.post(
    "/documents/{document_id}/assign",
    response_model=EnvelopeResponse[DocumentRetentionResponse],
    status_code=status.HTTP_201_CREATED,
)
async def assign_retention_to_document(
    document_id: uuid.UUID,
    data: AssignRetentionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Assign a retention policy to a document (admin only)."""
    dr = await retention_service.assign_retention_to_document(
        db, document_id, data.retention_policy_id, str(current_user.id)
    )
    return EnvelopeResponse(
        data=DocumentRetentionResponse(
            id=dr.id,
            document_id=dr.document_id,
            retention_policy_id=dr.retention_policy_id,
            policy_name=dr.retention_policy.name,
            applied_at=dr.applied_at,
            expires_at=dr.expires_at,
            applied_by=dr.applied_by,
        )
    )


@router.get(
    "/documents/{document_id}",
    response_model=EnvelopeResponse[list[DocumentRetentionResponse]],
)
async def list_document_retentions(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """List all retention assignments for a document (admin only)."""
    retentions = await retention_service.list_document_retentions(db, document_id)
    return EnvelopeResponse(
        data=[
            DocumentRetentionResponse(
                id=dr.id,
                document_id=dr.document_id,
                retention_policy_id=dr.retention_policy_id,
                policy_name=dr.retention_policy.name,
                applied_at=dr.applied_at,
                expires_at=dr.expires_at,
                applied_by=dr.applied_by,
            )
            for dr in retentions
        ]
    )


@router.delete(
    "/documents/{document_id}/{retention_id}",
    response_model=EnvelopeResponse,
)
async def remove_retention_from_document(
    document_id: uuid.UUID,
    retention_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Remove a retention assignment from a document (admin only)."""
    await retention_service.remove_retention_from_document(
        db, document_id, retention_id, str(current_user.id)
    )
    return EnvelopeResponse(data=None, meta={"message": "Retention removed"})
