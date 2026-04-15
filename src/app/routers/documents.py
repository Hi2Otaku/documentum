import json
import math
import uuid

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_admin, get_current_user, require_permission
from app.models.document import Document
from app.models.enums import PermissionLevel
from app.models.user import User
from app.schemas.common import EnvelopeResponse, PaginationMeta
from app.schemas.document import DocumentResponse, DocumentUpdate, DocumentVersionResponse
from app.services import document_service, document_type_service, folder_service
from app.services.audit_service import create_audit_record

router = APIRouter(prefix="/documents", tags=["documents"])


def _doc_response(doc: Document, folder_ids: list[str] | None = None) -> DocumentResponse:
    """Build DocumentResponse with document_type_name and folder_ids populated."""
    base = DocumentResponse.model_validate(doc)
    document_type_name = doc.document_type.name if doc.document_type else None
    updates: dict = {"document_type_name": document_type_name}
    if folder_ids is not None:
        updates["folder_ids"] = folder_ids
    return base.model_copy(update=updates)


@router.post(
    "/",
    response_model=EnvelopeResponse[DocumentResponse],
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile,
    title: str = Form(...),
    author: str | None = Form(None),
    custom_properties: str | None = Form(None),
    document_type_id: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a new document with file content."""
    props = None
    if custom_properties is not None:
        props = json.loads(custom_properties)

    type_id = uuid.UUID(document_type_id) if document_type_id else None

    # Validate metadata against document type schema before saving
    await document_type_service.validate_metadata(db, type_id, props or {})

    document = await document_service.upload_document(
        db,
        file=file,
        title=title,
        author=author,
        custom_properties=props,
        user_id=str(current_user.id),
        document_type_id=type_id,
    )
    fids = await folder_service.get_document_folder_ids(db, document.id)
    return EnvelopeResponse(data=_doc_response(document, folder_ids=fids))


@router.get(
    "/",
    response_model=EnvelopeResponse[list[DocumentResponse]],
)
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    title: str | None = Query(None),
    author: str | None = Query(None),
    folder_id: str | None = Query(None),
    lifecycle_state: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List documents with pagination and optional filters."""
    documents, total_count = await document_service.list_documents(
        db, page, page_size, title, author,
        user_id=str(current_user.id),
        is_superuser=current_user.is_superuser,
        folder_id=folder_id,
        lifecycle_state=lifecycle_state,
    )
    results = []
    for d in documents:
        fids = await folder_service.get_document_folder_ids(db, d.id)
        results.append(_doc_response(d, folder_ids=fids))
    return EnvelopeResponse(
        data=results,
        meta=PaginationMeta(
            page=page,
            page_size=page_size,
            total_count=total_count,
            total_pages=math.ceil(total_count / page_size) if page_size > 0 else 0,
        ),
    )


@router.get(
    "/{document_id}",
    response_model=EnvelopeResponse[DocumentResponse],
)
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PermissionLevel.READ)),
):
    """Get a single document by ID."""
    from app.services.acl_service import get_access_source

    document = await document_service.get_document(db, document_id)
    fids = await folder_service.get_document_folder_ids(db, document.id)
    access_info = await get_access_source(db, document_id, current_user.id, current_user.is_superuser)
    resp = _doc_response(document, folder_ids=fids)
    resp = resp.model_copy(update=access_info)
    return EnvelopeResponse(data=resp)


@router.put(
    "/{document_id}",
    response_model=EnvelopeResponse[DocumentResponse],
)
async def update_document(
    document_id: uuid.UUID,
    data: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PermissionLevel.WRITE)),
):
    """Update document metadata."""
    # Validate metadata if custom_properties or document_type_id is being updated
    if data.custom_properties is not None or data.document_type_id is not None:
        # Determine effective type: use provided type_id; if not provided, fetch current doc type
        if data.document_type_id is not None:
            effective_type_id = data.document_type_id
        else:
            current_doc = await document_service.get_document(db, document_id)
            effective_type_id = current_doc.document_type_id
        await document_type_service.validate_metadata(
            db, effective_type_id, data.custom_properties or {}
        )

    document = await document_service.update_document_metadata(
        db,
        document_id=document_id,
        title=data.title,
        author=data.author,
        custom_properties=data.custom_properties,
        user_id=str(current_user.id),
        document_type_id=data.document_type_id,
    )
    fids = await folder_service.get_document_folder_ids(db, document.id)
    return EnvelopeResponse(data=_doc_response(document, folder_ids=fids))


@router.delete(
    "/{document_id}",
    response_model=EnvelopeResponse,
)
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Soft delete a document (admin only). Blocked if under retention or legal hold."""
    from app.services import retention_service

    deletable, reason = await retention_service.check_document_deletable(db, document_id)
    if not deletable:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot delete document: {reason}",
        )

    document = await document_service.get_document(db, document_id)
    document.is_deleted = True
    await db.flush()

    await create_audit_record(
        db,
        entity_type="document",
        entity_id=str(document_id),
        action="delete",
        user_id=str(current_user.id),
    )

    return EnvelopeResponse(data=None, meta={"message": "Document deleted"})


@router.post(
    "/{document_id}/checkout",
    response_model=EnvelopeResponse[DocumentResponse],
)
async def checkout(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PermissionLevel.WRITE)),
):
    """Check out (lock) a document for editing."""
    document = await document_service.checkout_document(
        db, document_id, str(current_user.id)
    )
    fids = await folder_service.get_document_folder_ids(db, document.id)
    return EnvelopeResponse(data=_doc_response(document, folder_ids=fids))


@router.post(
    "/{document_id}/checkin",
    response_model=EnvelopeResponse[DocumentVersionResponse],
)
async def checkin(
    document_id: uuid.UUID,
    file: UploadFile,
    comment: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PermissionLevel.WRITE)),
):
    """Check in a document with a new file version."""
    version = await document_service.checkin_document(
        db,
        document_id=document_id,
        file=file,
        user_id=str(current_user.id),
        comment=comment,
    )

    if version is None:
        return EnvelopeResponse(
            data=None,
            meta={
                "message": "Content unchanged, no new version created",
                "lock_released": True,
            },
        )

    return EnvelopeResponse(data=DocumentVersionResponse.model_validate(version))


@router.post(
    "/{document_id}/unlock",
    response_model=EnvelopeResponse[DocumentResponse],
)
async def force_unlock(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Force-unlock a document (admin only)."""
    document = await document_service.force_unlock_document(
        db, document_id, str(current_user.id)
    )
    fids = await folder_service.get_document_folder_ids(db, document.id)
    return EnvelopeResponse(data=_doc_response(document, folder_ids=fids))


@router.get(
    "/{document_id}/versions",
    response_model=EnvelopeResponse[list[DocumentVersionResponse]],
)
async def list_versions(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PermissionLevel.READ)),
):
    """List all versions of a document."""
    versions = await document_service.list_versions(db, document_id)
    return EnvelopeResponse(
        data=[DocumentVersionResponse.model_validate(v) for v in versions]
    )


@router.get(
    "/{document_id}/versions/{version_id}/download",
)
async def download_version(
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PermissionLevel.READ)),
):
    """Download the content of a specific document version."""
    content, version = await document_service.download_version_content(
        db, document_id, version_id
    )
    return Response(
        content=content,
        media_type=version.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{version.filename}"',
        },
    )
