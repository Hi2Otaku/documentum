"""Document relationships router — CRUD for typed links between documents."""

import json
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.models.enums import PermissionLevel
from app.models.user import User
from app.schemas.common import EnvelopeResponse
from app.schemas.document_relationship import RelationshipCreate, RelationshipResponse
from app.services import relationship_service
from app.services.audit_service import create_audit_record

router = APIRouter(prefix="/documents", tags=["document-relationships"])


def _rel_response(rel) -> RelationshipResponse:
    """Build RelationshipResponse with document titles populated."""
    source_title = rel.source_document.title if rel.source_document else None
    target_title = rel.target_document.title if rel.target_document else None
    return RelationshipResponse(
        id=rel.id,
        source_document_id=rel.source_document_id,
        target_document_id=rel.target_document_id,
        relationship_type=rel.relationship_type.value if hasattr(rel.relationship_type, "value") else rel.relationship_type,
        description=rel.description,
        created_at=rel.created_at,
        created_by=rel.created_by,
        source_document_title=source_title,
        target_document_title=target_title,
    )


@router.get(
    "/{document_id}/relationships",
    response_model=EnvelopeResponse[list[RelationshipResponse]],
)
async def list_relationships(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PermissionLevel.READ)),
):
    """List all relationships for a document (as source or target)."""
    rels = await relationship_service.list_relationships(db, document_id)
    return EnvelopeResponse(data=[_rel_response(r) for r in rels])


@router.post(
    "/{document_id}/relationships",
    response_model=EnvelopeResponse[RelationshipResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_relationship(
    document_id: uuid.UUID,
    data: RelationshipCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PermissionLevel.WRITE)),
):
    """Create a typed directional relationship from this document to another."""
    rel = await relationship_service.create_relationship(
        db,
        source_document_id=document_id,
        target_document_id=data.target_document_id,
        relationship_type=data.relationship_type,
        description=data.description,
        created_by=str(current_user.id),
    )

    await create_audit_record(
        db,
        entity_type="document_relationship",
        entity_id=str(rel.id),
        action="create",
        user_id=str(current_user.id),
        details=json.dumps({
            "source_document_id": str(document_id),
            "target_document_id": str(data.target_document_id),
            "relationship_type": data.relationship_type,
        }),
    )

    return EnvelopeResponse(data=_rel_response(rel))


@router.delete(
    "/{document_id}/relationships/{relationship_id}",
    response_model=EnvelopeResponse,
)
async def delete_relationship(
    document_id: uuid.UUID,
    relationship_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PermissionLevel.WRITE)),
):
    """Remove a relationship."""
    await relationship_service.delete_relationship(db, document_id, relationship_id)

    await create_audit_record(
        db,
        entity_type="document_relationship",
        entity_id=str(relationship_id),
        action="delete",
        user_id=str(current_user.id),
    )

    return EnvelopeResponse(data=None, meta={"message": "Relationship deleted"})
