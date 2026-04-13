"""Router for DocumentType CRUD endpoints.

Write operations (POST, PUT, DELETE) are admin-only.
Read operations (GET) are available to any authenticated user.
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_admin, get_current_user
from app.models.document_type import DocumentType
from app.models.user import User
from app.schemas.common import EnvelopeResponse
from app.schemas.document_type import DocumentTypeCreate, DocumentTypeResponse, DocumentTypeUpdate
from app.services import document_type_service

router = APIRouter(prefix="/document-types", tags=["document-types"])


def _build_response(doc_type: DocumentType, document_count: int = 0) -> DocumentTypeResponse:
    """Build a DocumentTypeResponse from a DocumentType ORM object.

    Computes derived fields: parent_type_name and field_count.
    """
    parent_type_name = doc_type.parent_type.name if doc_type.parent_type else None
    field_count = len(doc_type.metadata_schema.get("properties", {})) if isinstance(doc_type.metadata_schema, dict) else 0

    return DocumentTypeResponse(
        id=doc_type.id,
        name=doc_type.name,
        description=doc_type.description,
        metadata_schema=doc_type.metadata_schema,
        parent_type_id=doc_type.parent_type_id,
        parent_type_name=parent_type_name,
        field_count=field_count,
        document_count=document_count,
        created_at=doc_type.created_at,
        updated_at=doc_type.updated_at,
    )


@router.post(
    "/",
    response_model=EnvelopeResponse[DocumentTypeResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_document_type(
    data: DocumentTypeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
) -> EnvelopeResponse[DocumentTypeResponse]:
    """Create a new document type (admin only)."""
    result = await document_type_service.create_document_type(db, data, str(current_user.id))
    response = _build_response(result, document_count=0)
    return EnvelopeResponse(data=response)


@router.get(
    "/",
    response_model=EnvelopeResponse[list[DocumentTypeResponse]],
)
async def list_document_types(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EnvelopeResponse[list[DocumentTypeResponse]]:
    """List all document types (any authenticated user)."""
    types = await document_type_service.list_document_types(db)

    responses = []
    for doc_type in types:
        doc_count = await document_type_service.get_document_count_for_type(db, doc_type.id)
        responses.append(_build_response(doc_type, document_count=doc_count))

    return EnvelopeResponse(data=responses)


@router.get(
    "/{type_id}",
    response_model=EnvelopeResponse[DocumentTypeResponse],
)
async def get_document_type(
    type_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EnvelopeResponse[DocumentTypeResponse]:
    """Get a single document type by ID (any authenticated user)."""
    doc_type = await document_type_service.get_document_type(db, type_id)
    doc_count = await document_type_service.get_document_count_for_type(db, type_id)
    response = _build_response(doc_type, document_count=doc_count)
    return EnvelopeResponse(data=response)


@router.put(
    "/{type_id}",
    response_model=EnvelopeResponse[DocumentTypeResponse],
)
async def update_document_type(
    type_id: uuid.UUID,
    data: DocumentTypeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
) -> EnvelopeResponse[DocumentTypeResponse]:
    """Update a document type (admin only)."""
    result = await document_type_service.update_document_type(db, type_id, data, str(current_user.id))
    doc_count = await document_type_service.get_document_count_for_type(db, type_id)
    response = _build_response(result, document_count=doc_count)
    return EnvelopeResponse(data=response)


@router.delete(
    "/{type_id}",
    response_model=EnvelopeResponse,
)
async def delete_document_type(
    type_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
) -> EnvelopeResponse:
    """Soft-delete a document type (admin only)."""
    await document_type_service.delete_document_type(db, type_id)
    return EnvelopeResponse(data=None, meta={"message": "Document type deleted"})
