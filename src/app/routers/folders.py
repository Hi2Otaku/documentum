"""Router for Cabinet/Folder hierarchy endpoints.

Write operations (POST cabinet, DELETE, copy) restricted to admins or
authenticated users depending on the operation.
Read operations are available to any authenticated user.
"""

import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_admin, get_current_user
from app.models.enums import PermissionLevel
from app.models.folder import Folder
from app.models.user import User
from app.schemas.acl import FolderACLEntryCreate, FolderACLEntryResponse
from app.schemas.common import EnvelopeResponse, PaginationMeta
from app.schemas.folder import (
    FileDocumentRequest,
    FolderCopyRequest,
    FolderCreate,
    FolderPathSegment,
    FolderResponse,
    FolderTreeNode,
    FolderUpdate,
)
from app.services import acl_service, folder_service

router = APIRouter(prefix="/folders", tags=["folders"])


def _build_response(
    folder: Folder, path: list[dict], document_count: int
) -> FolderResponse:
    """Build a FolderResponse from an ORM Folder object."""
    return FolderResponse(
        id=folder.id,
        name=folder.name,
        description=folder.description,
        parent_id=folder.parent_id,
        is_cabinet=folder.is_cabinet,
        document_count=document_count,
        path=[FolderPathSegment(id=s["id"], name=s["name"]) for s in path],
        created_at=folder.created_at,
        updated_at=folder.updated_at,
        created_by=folder.created_by,
    )


@router.get(
    "/",
    response_model=EnvelopeResponse[list[FolderResponse]],
)
async def list_cabinets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EnvelopeResponse[list[FolderResponse]]:
    """List all root-level cabinets (any authenticated user)."""
    result = await db.execute(
        select(Folder)
        .where(Folder.is_cabinet == True, Folder.is_deleted == False)  # noqa: E712
        .order_by(Folder.name)
    )
    folders = result.scalars().all()
    return EnvelopeResponse(
        data=[
            FolderResponse(
                id=f.id,
                name=f.name,
                description=f.description,
                parent_id=f.parent_id,
                is_cabinet=f.is_cabinet,
                document_count=0,
                path=[],
                created_at=f.created_at,
                updated_at=f.updated_at,
                created_by=f.created_by,
            )
            for f in folders
        ]
    )


@router.post(
    "/",
    response_model=EnvelopeResponse[FolderResponse],
    status_code=201,
)
async def create_cabinet(
    data: FolderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
) -> EnvelopeResponse[FolderResponse]:
    """Create a new cabinet (root folder). Admin only."""
    folder = await folder_service.create_cabinet(
        db, data.name, data.description, str(current_user.id)
    )
    return EnvelopeResponse(data=_build_response(folder, path=[], document_count=0))


@router.get(
    "/tree",
    response_model=EnvelopeResponse[list[FolderTreeNode]],
)
async def get_folder_tree(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EnvelopeResponse[list[FolderTreeNode]]:
    """Return the full folder/cabinet hierarchy as a nested tree."""
    tree = await folder_service.get_folder_tree(db)
    # Validate into FolderTreeNode Pydantic models (supports recursive children)
    nodes = [FolderTreeNode.model_validate(node) for node in tree]
    return EnvelopeResponse(data=nodes)


@router.get(
    "/{folder_id}",
    response_model=EnvelopeResponse[FolderResponse],
)
async def get_folder(
    folder_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EnvelopeResponse[FolderResponse]:
    """Get a single folder with breadcrumb path and document count."""
    result = await folder_service.get_folder(db, folder_id)
    return EnvelopeResponse(
        data=_build_response(
            result["folder"],
            path=result["path"],
            document_count=result["document_count"],
        )
    )


@router.post(
    "/{folder_id}/children",
    response_model=EnvelopeResponse[FolderResponse],
    status_code=201,
)
async def create_subfolder(
    folder_id: uuid.UUID,
    data: FolderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EnvelopeResponse[FolderResponse]:
    """Create a subfolder under an existing folder (any authenticated user)."""
    folder = await folder_service.create_folder(
        db, folder_id, data.name, data.description, str(current_user.id)
    )
    return EnvelopeResponse(data=_build_response(folder, path=[], document_count=0))


@router.put(
    "/{folder_id}",
    response_model=EnvelopeResponse[FolderResponse],
)
async def update_folder(
    folder_id: uuid.UUID,
    data: FolderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EnvelopeResponse[FolderResponse]:
    """Rename and/or move a folder (any authenticated user)."""
    if data.name is not None:
        await folder_service.rename_folder(db, folder_id, data.name)
    if data.parent_id is not None:
        await folder_service.move_folder(db, folder_id, data.parent_id)
    result = await folder_service.get_folder(db, folder_id)
    return EnvelopeResponse(
        data=_build_response(
            result["folder"],
            path=result["path"],
            document_count=result["document_count"],
        )
    )


@router.delete(
    "/{folder_id}",
    response_model=EnvelopeResponse,
)
async def delete_folder(
    folder_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
) -> EnvelopeResponse:
    """Soft-delete a folder and all descendants (admin only)."""
    await folder_service.delete_folder(db, folder_id)
    return EnvelopeResponse(data=None, meta={"message": "Folder deleted"})


@router.post(
    "/{folder_id}/copy",
    response_model=EnvelopeResponse[FolderResponse],
    status_code=201,
)
async def copy_folder(
    folder_id: uuid.UUID,
    data: FolderCopyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EnvelopeResponse[FolderResponse]:
    """Shallow copy of a folder subtree to a destination parent."""
    folder = await folder_service.copy_folder(
        db, folder_id, data.destination_parent_id, str(current_user.id)
    )
    result = await folder_service.get_folder(db, folder.id)
    return EnvelopeResponse(
        data=_build_response(
            result["folder"],
            path=result["path"],
            document_count=result["document_count"],
        )
    )


@router.get(
    "/{folder_id}/documents",
    response_model=EnvelopeResponse[list],
)
async def get_folder_documents(
    folder_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EnvelopeResponse:
    """Return paginated documents filed in a folder, filtered by ACL."""
    from app.schemas.document import DocumentResponse as DocResp

    documents, total = await folder_service.get_folder_documents(
        db, folder_id, page, page_size,
        user_id=current_user.id,
        is_superuser=current_user.is_superuser,
    )
    return EnvelopeResponse(
        data=[DocResp.model_validate(d) for d in documents],
        meta=PaginationMeta(
            page=page,
            page_size=page_size,
            total_count=total,
            total_pages=math.ceil(total / page_size) if page_size > 0 else 0,
        ),
    )


@router.get(
    "/{folder_id}/acl",
    response_model=EnvelopeResponse[list[FolderACLEntryResponse]],
)
async def list_folder_acl(
    folder_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EnvelopeResponse:
    """List folder ACL entries. Requires ADMIN on folder or superuser."""
    if not current_user.is_superuser:
        has_admin = await acl_service.check_folder_permission(
            db, folder_id, current_user.id, PermissionLevel.ADMIN
        )
        if not has_admin:
            raise HTTPException(status_code=403, detail="Insufficient permissions: requires ADMIN on folder")
    entries = await acl_service.get_folder_acls(db, folder_id)
    return EnvelopeResponse(data=[FolderACLEntryResponse.model_validate(e) for e in entries])


@router.post(
    "/{folder_id}/acl",
    response_model=EnvelopeResponse[FolderACLEntryResponse],
    status_code=201,
)
async def add_folder_acl(
    folder_id: uuid.UUID,
    request: FolderACLEntryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EnvelopeResponse:
    """Add folder ACL entry. Requires ADMIN on folder or superuser."""
    if not current_user.is_superuser:
        has_admin = await acl_service.check_folder_permission(
            db, folder_id, current_user.id, PermissionLevel.ADMIN
        )
        if not has_admin:
            raise HTTPException(status_code=403, detail="Insufficient permissions: requires ADMIN on folder")
    entry = await acl_service.create_folder_acl_entry(
        db, folder_id=folder_id, principal_id=request.principal_id,
        principal_type=request.principal_type, permission_level=request.permission_level,
        user_id=str(current_user.id),
    )
    return EnvelopeResponse(data=FolderACLEntryResponse.model_validate(entry))


@router.delete(
    "/{folder_id}/acl/{acl_id}",
    response_model=EnvelopeResponse,
)
async def remove_folder_acl(
    folder_id: uuid.UUID,
    acl_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EnvelopeResponse:
    """Remove folder ACL entry. Requires ADMIN on folder or superuser."""
    if not current_user.is_superuser:
        has_admin = await acl_service.check_folder_permission(
            db, folder_id, current_user.id, PermissionLevel.ADMIN
        )
        if not has_admin:
            raise HTTPException(status_code=403, detail="Insufficient permissions: requires ADMIN on folder")
    removed = await acl_service.remove_folder_acl_entry(
        db, folder_id, acl_id, user_id=str(current_user.id),
    )
    if not removed:
        raise HTTPException(status_code=404, detail="ACL entry not found")
    return EnvelopeResponse(data=None, meta={"message": "ACL entry removed"})


@router.post(
    "/{folder_id}/documents",
    response_model=EnvelopeResponse,
)
async def file_document(
    folder_id: uuid.UUID,
    data: FileDocumentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EnvelopeResponse:
    """File a document into a folder."""
    await folder_service.file_document(
        db, folder_id, data.document_id, str(current_user.id)
    )
    return EnvelopeResponse(data=None, meta={"message": "Document filed"})


@router.delete(
    "/{folder_id}/documents/{document_id}",
    response_model=EnvelopeResponse,
)
async def unfile_document(
    folder_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EnvelopeResponse:
    """Remove a document from a folder (unfile)."""
    await folder_service.unfile_document(db, folder_id, document_id)
    return EnvelopeResponse(data=None, meta={"message": "Document unfiled"})
