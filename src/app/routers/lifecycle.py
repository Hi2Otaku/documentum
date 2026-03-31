"""Lifecycle and ACL management endpoints for documents.

Provides manual lifecycle transitions, lifecycle state queries,
and ACL CRUD operations as sub-resources of documents.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.models.enums import LifecycleState, PermissionLevel
from app.models.user import User
from app.schemas.acl import ACLEntryCreate, ACLEntryResponse
from app.schemas.common import EnvelopeResponse
from app.schemas.lifecycle import LifecycleTransitionRequest, LifecycleTransitionResponse
from app.services import acl_service, lifecycle_service

router = APIRouter(prefix="/documents", tags=["lifecycle"])


@router.post(
    "/{document_id}/lifecycle/transition",
    response_model=EnvelopeResponse[LifecycleTransitionResponse],
)
async def transition_document_lifecycle(
    document_id: uuid.UUID,
    request: LifecycleTransitionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PermissionLevel.WRITE)),
):
    """Manually transition a document to a new lifecycle state."""
    try:
        document = await lifecycle_service.transition_lifecycle_state(
            db, document_id, request.target_state, str(current_user.id)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    return EnvelopeResponse(
        data=LifecycleTransitionResponse.model_validate(document)
    )


@router.get(
    "/{document_id}/lifecycle",
    response_model=EnvelopeResponse,
)
async def get_lifecycle_state(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PermissionLevel.READ)),
):
    """Get the current lifecycle state of a document."""
    from app.services.document_service import get_document

    document = await get_document(db, document_id)
    return EnvelopeResponse(
        data={
            "document_id": str(document.id),
            "lifecycle_state": document.lifecycle_state or LifecycleState.DRAFT.value,
        }
    )


@router.get(
    "/{document_id}/acl",
    response_model=EnvelopeResponse[list[ACLEntryResponse]],
)
async def list_acl_entries(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PermissionLevel.ADMIN)),
):
    """List all ACL entries for a document (requires ADMIN)."""
    entries = await acl_service.get_document_acls(db, document_id)
    return EnvelopeResponse(
        data=[ACLEntryResponse.model_validate(e) for e in entries]
    )


@router.post(
    "/{document_id}/acl",
    response_model=EnvelopeResponse[ACLEntryResponse],
    status_code=status.HTTP_201_CREATED,
)
async def add_acl_entry(
    document_id: uuid.UUID,
    request: ACLEntryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PermissionLevel.ADMIN)),
):
    """Add an ACL entry for a document (requires ADMIN)."""
    entry = await acl_service.create_acl_entry(
        db,
        document_id=document_id,
        principal_id=request.principal_id,
        principal_type=request.principal_type,
        permission_level=request.permission_level,
        user_id=str(current_user.id),
    )
    return EnvelopeResponse(data=ACLEntryResponse.model_validate(entry))


@router.delete(
    "/{document_id}/acl/{acl_id}",
    response_model=EnvelopeResponse,
)
async def remove_acl_entry(
    document_id: uuid.UUID,
    acl_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PermissionLevel.ADMIN)),
):
    """Remove a specific ACL entry (requires ADMIN)."""
    from sqlalchemy import select
    from app.models.acl import DocumentACL

    result = await db.execute(
        select(DocumentACL).where(
            DocumentACL.id == acl_id,
            DocumentACL.document_id == document_id,
            DocumentACL.is_deleted == False,  # noqa: E712
        )
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ACL entry not found",
        )

    await db.delete(entry)

    from app.services.audit_service import create_audit_record
    await create_audit_record(
        db,
        entity_type="document_acl",
        entity_id=str(document_id),
        action="acl_revoked",
        user_id=str(current_user.id),
        before_state={
            "principal_id": str(entry.principal_id),
            "principal_type": entry.principal_type,
            "permission_level": entry.permission_level,
        },
    )

    return EnvelopeResponse(data=None, meta={"message": "ACL entry removed"})
