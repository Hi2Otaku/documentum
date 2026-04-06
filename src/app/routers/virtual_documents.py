"""API endpoints for virtual (compound) documents."""

import math
import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.common import EnvelopeResponse, PaginationMeta
from app.schemas.virtual_document import (
    AddChildRequest,
    ReorderChildrenRequest,
    VirtualDocumentChildResponse,
    VirtualDocumentCreate,
    VirtualDocumentListResponse,
    VirtualDocumentResponse,
    VirtualDocumentUpdate,
)
from app.services import virtual_document_service as vdoc_service

router = APIRouter(prefix="/virtual-documents", tags=["virtual-documents"])


# ---------------------------------------------------------------------------
# Helper to build child responses with document info
# ---------------------------------------------------------------------------


def _child_response(child) -> VirtualDocumentChildResponse:
    doc = getattr(child, "document", None)
    return VirtualDocumentChildResponse(
        id=child.id,
        document_id=child.document_id,
        sort_order=child.sort_order,
        document_title=doc.title if doc else None,
        document_filename=doc.filename if doc else None,
        created_at=child.created_at,
    )


def _vdoc_response(vdoc) -> VirtualDocumentResponse:
    children = [_child_response(c) for c in (vdoc.children or [])]
    return VirtualDocumentResponse(
        id=vdoc.id,
        title=vdoc.title,
        description=vdoc.description,
        owner_id=vdoc.owner_id,
        created_at=vdoc.created_at,
        updated_at=vdoc.updated_at,
        created_by=vdoc.created_by,
        is_deleted=vdoc.is_deleted,
        children=children,
    )


# ---------------------------------------------------------------------------
# CRUD endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/",
    response_model=EnvelopeResponse[VirtualDocumentResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_virtual_document(
    data: VirtualDocumentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new virtual document."""
    vdoc = await vdoc_service.create_virtual_document(
        db,
        title=data.title,
        description=data.description,
        owner_id=current_user.id,
        user_id=str(current_user.id),
    )
    return EnvelopeResponse(data=_vdoc_response(vdoc))


@router.get(
    "/",
    response_model=EnvelopeResponse[list[VirtualDocumentListResponse]],
)
async def list_virtual_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    owner_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List virtual documents with pagination."""
    vdocs, total = await vdoc_service.list_virtual_documents(
        db, page=page, page_size=page_size, owner_id=owner_id
    )
    items = [
        VirtualDocumentListResponse(
            id=v.id,
            title=v.title,
            description=v.description,
            owner_id=v.owner_id,
            child_count=len(v.children) if v.children else 0,
            created_at=v.created_at,
            updated_at=v.updated_at,
        )
        for v in vdocs
    ]
    return EnvelopeResponse(
        data=items,
        meta=PaginationMeta(
            page=page,
            page_size=page_size,
            total_count=total,
            total_pages=math.ceil(total / page_size) if page_size > 0 else 0,
        ),
    )


@router.get(
    "/{vdoc_id}",
    response_model=EnvelopeResponse[VirtualDocumentResponse],
)
async def get_virtual_document(
    vdoc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a virtual document with its children."""
    vdoc = await vdoc_service.get_virtual_document(db, vdoc_id)
    return EnvelopeResponse(data=_vdoc_response(vdoc))


@router.put(
    "/{vdoc_id}",
    response_model=EnvelopeResponse[VirtualDocumentResponse],
)
async def update_virtual_document(
    vdoc_id: uuid.UUID,
    data: VirtualDocumentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update virtual document metadata."""
    vdoc = await vdoc_service.update_virtual_document(
        db, vdoc_id, title=data.title, description=data.description
    )
    return EnvelopeResponse(data=_vdoc_response(vdoc))


@router.delete(
    "/{vdoc_id}",
    response_model=EnvelopeResponse,
)
async def delete_virtual_document(
    vdoc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft-delete a virtual document."""
    await vdoc_service.delete_virtual_document(db, vdoc_id)
    return EnvelopeResponse(data=None, meta={"message": "Virtual document deleted"})


# ---------------------------------------------------------------------------
# Child management endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/{vdoc_id}/children",
    response_model=EnvelopeResponse[VirtualDocumentChildResponse],
    status_code=status.HTTP_201_CREATED,
)
async def add_child(
    vdoc_id: uuid.UUID,
    data: AddChildRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a document as a child of the virtual document."""
    child = await vdoc_service.add_child(
        db, vdoc_id=vdoc_id, document_id=data.document_id, sort_order=data.sort_order
    )
    return EnvelopeResponse(data=_child_response(child))


@router.delete(
    "/{vdoc_id}/children/{document_id}",
    response_model=EnvelopeResponse,
)
async def remove_child(
    vdoc_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a child document from the virtual document."""
    await vdoc_service.remove_child(db, vdoc_id=vdoc_id, document_id=document_id)
    return EnvelopeResponse(data=None, meta={"message": "Child removed"})


@router.put(
    "/{vdoc_id}/children/reorder",
    response_model=EnvelopeResponse[list[VirtualDocumentChildResponse]],
)
async def reorder_children(
    vdoc_id: uuid.UUID,
    data: ReorderChildrenRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reorder children of the virtual document."""
    children = await vdoc_service.reorder_children(
        db, vdoc_id=vdoc_id, document_ids=data.document_ids
    )
    return EnvelopeResponse(data=[_child_response(c) for c in children])


# ---------------------------------------------------------------------------
# Merged PDF
# ---------------------------------------------------------------------------


@router.get(
    "/{vdoc_id}/merge",
)
async def generate_merged_pdf(
    vdoc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate and download a merged PDF from all child documents."""
    pdf_bytes, filename = await vdoc_service.generate_merged_pdf(db, vdoc_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
