"""CMIS 1.1 Browser Binding router.

Implements the OASIS CMIS Browser Binding protocol over existing
document_service and folder_service functions. All endpoints require
authentication.

Browser Binding conventions:
- GET with `cmisselector` query param for reads
- POST with `cmisaction` form param for writes
- Responses use succinctProperties format
"""

import json
import logging
import uuid

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.document import Document, DocumentVersion
from app.models.folder import Folder
from app.models.user import User
from app.services import cmis_service, document_service, folder_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cmis/browser", tags=["cmis"])


# ── Helpers ──────────────────────────────────────────────────────────────────


def _cmis_error(exception_type: str, message: str, status_code: int = 400) -> HTTPException:
    """Create an HTTPException with CMIS-style error body."""
    return HTTPException(
        status_code=status_code,
        detail={"exception": exception_type, "message": message},
    )


async def _get_or_create_root_folder(db: AsyncSession, user_id: str) -> Folder:
    """Get the first cabinet as CMIS root folder, or create one."""
    result = await db.execute(
        select(Folder).where(
            Folder.is_cabinet == True,  # noqa: E712
            Folder.is_deleted == False,  # noqa: E712
        ).order_by(Folder.created_at).limit(1)
    )
    folder = result.scalar_one_or_none()
    if folder is None:
        folder = await folder_service.create_cabinet(
            db, name="Root Folder", description="CMIS root folder", created_by=user_id
        )
        await db.commit()
    return folder


async def _resolve_object(
    db: AsyncSession, object_id: uuid.UUID
) -> tuple[Document | Folder, bool]:
    """Try to resolve an object ID as a document first, then folder.

    Returns (object, is_folder).
    """
    # Try document first
    try:
        doc = await document_service.get_document(db, object_id)
        return doc, False
    except HTTPException:
        pass

    # Try folder
    try:
        folder_data = await folder_service.get_folder(db, object_id)
        return folder_data["folder"], True
    except HTTPException:
        pass

    raise _cmis_error("objectNotFound", f"Object {object_id} not found", 404)


async def _get_descendants_tree(
    db: AsyncSession, folder_id: uuid.UUID
) -> list[dict]:
    """Build a CMIS descendants tree recursively."""
    # Get subfolders
    result = await db.execute(
        select(Folder).where(
            Folder.parent_id == folder_id,
            Folder.is_deleted == False,  # noqa: E712
        )
    )
    subfolders = list(result.scalars().all())

    # Get documents in this folder
    docs, _ = await folder_service.get_folder_documents(db, folder_id)

    children = []

    for sf in subfolders:
        sub_children = await _get_descendants_tree(db, sf.id)
        children.append({
            "object": cmis_service.to_cmis_object(sf, is_folder=True),
            "children": sub_children,
        })

    for doc in docs:
        children.append({
            "object": cmis_service.to_cmis_object(doc, is_folder=False),
            "children": [],
        })

    return children


# ── GET endpoints (reads via cmisselector) ───────────────────────────────────


@router.get("")
async def get_repository_info(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return CMIS 1.1 repository info."""
    root = await _get_or_create_root_folder(db, str(current_user.id))
    info = cmis_service.get_repository_info(str(root.id))
    return info


@router.get("/type")
async def get_type_definition(
    typeId: str = Query(..., description="CMIS type ID (cmis:document or cmis:folder)"),
    current_user: User = Depends(get_current_user),
):
    """Return CMIS type definition."""
    try:
        return cmis_service.get_type_definition(typeId)
    except ValueError as e:
        raise _cmis_error("invalidArgument", str(e))


@router.get("/root")
async def get_root_children(
    cmisselector: str = Query("children"),
    maxItems: int = Query(50, ge=1, le=1000),
    skipCount: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get children of the root folder."""
    root = await _get_or_create_root_folder(db, str(current_user.id))
    return await _handle_get_object(
        db, root.id, cmisselector, maxItems, skipCount, current_user, is_folder=True
    )


@router.get("/root/{object_id}")
async def get_object(
    object_id: uuid.UUID,
    cmisselector: str = Query("object"),
    maxItems: int = Query(50, ge=1, le=1000),
    skipCount: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a CMIS object by ID. Behavior depends on cmisselector."""
    obj, is_folder = await _resolve_object(db, object_id)
    return await _handle_get_object(
        db, object_id, cmisselector, maxItems, skipCount, current_user, is_folder, obj
    )


async def _handle_get_object(
    db: AsyncSession,
    object_id: uuid.UUID,
    cmisselector: str,
    maxItems: int,
    skipCount: int,
    current_user: User,
    is_folder: bool,
    obj: Document | Folder | None = None,
):
    """Dispatch GET based on cmisselector value."""

    if cmisselector == "object":
        if obj is None:
            obj, is_folder = await _resolve_object(db, object_id)
        return cmis_service.to_cmis_object(obj, is_folder=is_folder)

    elif cmisselector == "children":
        if not is_folder:
            raise _cmis_error("invalidArgument", "getChildren requires a folder object")
        return await _get_children(db, object_id, maxItems, skipCount, current_user)

    elif cmisselector == "descendants":
        if not is_folder:
            raise _cmis_error("invalidArgument", "getDescendants requires a folder object")
        return await _get_descendants_tree(db, object_id)

    elif cmisselector == "parents":
        return await _get_parents(db, object_id, is_folder)

    elif cmisselector == "content":
        if is_folder:
            raise _cmis_error("invalidArgument", "Folders have no content stream")
        return await _get_content_stream(db, object_id)

    else:
        raise _cmis_error("invalidArgument", f"Unsupported cmisselector: {cmisselector}")


async def _get_children(
    db: AsyncSession,
    folder_id: uuid.UUID,
    max_items: int,
    skip_count: int,
    current_user: User,
) -> dict:
    """Get folder children in CMIS format."""
    # Get subfolders
    result = await db.execute(
        select(Folder).where(
            Folder.parent_id == folder_id,
            Folder.is_deleted == False,  # noqa: E712
        ).order_by(Folder.name)
    )
    subfolders = list(result.scalars().all())

    # Get documents
    docs, _ = await folder_service.get_folder_documents(
        db, folder_id, user_id=current_user.id, is_superuser=current_user.is_superuser
    )

    # Combine and paginate
    all_objects = []
    for sf in subfolders:
        all_objects.append(cmis_service.to_cmis_object(sf, is_folder=True))
    for doc in docs:
        all_objects.append(cmis_service.to_cmis_object(doc, is_folder=False))

    total = len(all_objects)
    paged = all_objects[skip_count : skip_count + max_items]
    has_more = (skip_count + max_items) < total

    return {
        "objects": paged,
        "hasMoreItems": has_more,
        "numItems": total,
    }


async def _get_parents(
    db: AsyncSession, object_id: uuid.UUID, is_folder: bool
) -> list[dict]:
    """Get parent folders of an object."""
    if is_folder:
        folder_data = await folder_service.get_folder(db, object_id)
        folder = folder_data["folder"]
        if folder.parent_id:
            parent_data = await folder_service.get_folder(db, folder.parent_id)
            return [cmis_service.to_cmis_object(parent_data["folder"], is_folder=True)]
        return []
    else:
        # Document: find all folders containing it
        folder_ids = await folder_service.get_document_folder_ids(db, object_id)
        parents = []
        for fid in folder_ids:
            try:
                fdata = await folder_service.get_folder(db, uuid.UUID(fid))
                parents.append(cmis_service.to_cmis_object(fdata["folder"], is_folder=True))
            except Exception:
                pass
        return parents


async def _get_content_stream(db: AsyncSession, document_id: uuid.UUID) -> Response:
    """Stream document content."""
    doc = await document_service.get_document(db, document_id)

    # Get latest version
    result = await db.execute(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == document_id)
        .order_by(
            DocumentVersion.major_version.desc(),
            DocumentVersion.minor_version.desc(),
        )
        .limit(1)
    )
    version = result.scalar_one_or_none()
    if version is None:
        raise _cmis_error("objectNotFound", "No content available", 404)

    from app.core.minio_client import download_object
    content = await download_object(version.minio_object_key)

    return Response(
        content=content,
        media_type=doc.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{doc.filename}"',
            "Content-Length": str(version.content_size),
        },
    )


# ── POST endpoints (writes via cmisaction) ───────────────────────────────────


@router.post("/root")
async def create_object_in_root(
    cmisaction: str = Form(...),
    file: UploadFile | None = None,
    propertyId_0_: str | None = Form(None, alias="propertyId[0]"),
    propertyValue_0_: str | None = Form(None, alias="propertyValue[0]"),
    propertyId_1_: str | None = Form(None, alias="propertyId[1]"),
    propertyValue_1_: str | None = Form(None, alias="propertyValue[1]"),
    properties: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a document or folder in the root folder."""
    root = await _get_or_create_root_folder(db, str(current_user.id))
    return await _handle_post_action(
        db, root.id, cmisaction, file, propertyId_0_, propertyValue_0_,
        propertyId_1_, propertyValue_1_, properties, current_user, is_root=True
    )


@router.post("/root/{object_id}")
async def action_on_object(
    object_id: uuid.UUID,
    cmisaction: str = Form(...),
    file: UploadFile | None = None,
    propertyId_0_: str | None = Form(None, alias="propertyId[0]"),
    propertyValue_0_: str | None = Form(None, alias="propertyValue[0]"),
    propertyId_1_: str | None = Form(None, alias="propertyId[1]"),
    propertyValue_1_: str | None = Form(None, alias="propertyValue[1]"),
    properties: str | None = Form(None),
    sourceFolderId: str | None = Form(None),
    targetFolderId: str | None = Form(None),
    comment: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Perform CMIS action on an existing object."""
    user_id = str(current_user.id)

    if cmisaction == "update":
        cmis_props = _collect_properties(
            propertyId_0_, propertyValue_0_, propertyId_1_, propertyValue_1_, properties
        )
        internal = cmis_service.from_cmis_properties(cmis_props)
        doc = await document_service.update_document_metadata(
            db,
            document_id=object_id,
            title=internal.get("title"),
            author=internal.get("author"),
            custom_properties=None,
            user_id=user_id,
        )
        await db.commit()
        return cmis_service.to_cmis_object(doc, is_folder=False)

    elif cmisaction == "delete":
        obj, is_folder = await _resolve_object(db, object_id)
        if is_folder:
            await folder_service.delete_folder(db, object_id)
        else:
            obj.is_deleted = True
            await db.flush()
        await db.commit()
        return {"status": "ok"}

    elif cmisaction == "move":
        if not sourceFolderId or not targetFolderId:
            raise _cmis_error("invalidArgument", "move requires sourceFolderId and targetFolderId")
        source_id = uuid.UUID(sourceFolderId)
        target_id = uuid.UUID(targetFolderId)
        await folder_service.unfile_document(db, source_id, object_id)
        await folder_service.file_document(db, target_id, object_id, user_id)
        await db.commit()
        doc = await document_service.get_document(db, object_id)
        return cmis_service.to_cmis_object(doc, is_folder=False)

    elif cmisaction == "checkOut":
        doc = await document_service.checkout_document(db, object_id, user_id)
        await db.commit()
        return cmis_service.to_cmis_object(doc, is_folder=False)

    elif cmisaction == "checkIn":
        if file is None:
            raise _cmis_error("invalidArgument", "checkIn requires a file")
        version = await document_service.checkin_document(
            db, object_id, file, user_id, comment=comment
        )
        await db.commit()
        doc = await document_service.get_document(db, object_id)
        return cmis_service.to_cmis_object(doc, is_folder=False)

    elif cmisaction == "cancelCheckOut":
        doc = await document_service.get_document(db, object_id)
        if doc.locked_by is None:
            raise _cmis_error("constraint", "Document is not checked out")
        if str(doc.locked_by) != user_id and not current_user.is_superuser:
            raise _cmis_error("permissionDenied", "You do not hold the lock", 403)
        doc.locked_by = None
        doc.locked_at = None
        await db.flush()
        await db.commit()
        return cmis_service.to_cmis_object(doc, is_folder=False)

    elif cmisaction == "createDocument":
        # Create document in the specified folder (object_id is folder)
        return await _create_document_in_folder(
            db, object_id, file, propertyId_0_, propertyValue_0_,
            propertyId_1_, propertyValue_1_, properties, current_user
        )

    elif cmisaction == "createFolder":
        cmis_props = _collect_properties(
            propertyId_0_, propertyValue_0_, propertyId_1_, propertyValue_1_, properties
        )
        internal = cmis_service.from_cmis_properties_folder(cmis_props)
        folder_name = internal.get("name", "Untitled Folder")
        folder = await folder_service.create_folder(
            db, parent_id=object_id, name=folder_name,
            description=internal.get("description"), created_by=user_id
        )
        await db.commit()
        return cmis_service.to_cmis_object(folder, is_folder=True)

    else:
        raise _cmis_error("notSupported", f"Unsupported cmisaction: {cmisaction}")


async def _handle_post_action(
    db: AsyncSession,
    folder_id: uuid.UUID,
    cmisaction: str,
    file: UploadFile | None,
    propId0: str | None,
    propVal0: str | None,
    propId1: str | None,
    propVal1: str | None,
    properties: str | None,
    current_user: User,
    is_root: bool = False,
):
    """Handle POST to root folder (createDocument, createFolder)."""
    user_id = str(current_user.id)

    if cmisaction == "createDocument":
        return await _create_document_in_folder(
            db, folder_id, file, propId0, propVal0, propId1, propVal1, properties, current_user
        )

    elif cmisaction == "createFolder":
        cmis_props = _collect_properties(propId0, propVal0, propId1, propVal1, properties)
        internal = cmis_service.from_cmis_properties_folder(cmis_props)
        folder_name = internal.get("name", "Untitled Folder")
        folder = await folder_service.create_folder(
            db, parent_id=folder_id, name=folder_name,
            description=internal.get("description"), created_by=user_id
        )
        await db.commit()
        return cmis_service.to_cmis_object(folder, is_folder=True)

    else:
        raise _cmis_error("notSupported", f"Unsupported cmisaction for root: {cmisaction}")


async def _create_document_in_folder(
    db: AsyncSession,
    folder_id: uuid.UUID,
    file: UploadFile | None,
    propId0: str | None,
    propVal0: str | None,
    propId1: str | None,
    propVal1: str | None,
    properties: str | None,
    current_user: User,
) -> dict:
    """Create a document and file it into a folder."""
    if file is None:
        raise _cmis_error("invalidArgument", "createDocument requires a file")

    user_id = str(current_user.id)
    cmis_props = _collect_properties(propId0, propVal0, propId1, propVal1, properties)
    internal = cmis_service.from_cmis_properties(cmis_props)
    title = internal.get("title", file.filename or "Untitled")

    doc = await document_service.upload_document(
        db,
        file=file,
        title=title,
        author=None,
        custom_properties=None,
        user_id=user_id,
    )

    # File document into the folder
    await folder_service.file_document(db, folder_id, doc.id, user_id)
    await db.commit()

    return cmis_service.to_cmis_object(doc, is_folder=False)


def _collect_properties(
    propId0: str | None,
    propVal0: str | None,
    propId1: str | None,
    propVal1: str | None,
    properties_json: str | None,
) -> dict:
    """Collect CMIS properties from form fields or JSON."""
    props: dict = {}

    # From indexed form fields (CMIS Browser Binding standard)
    if propId0 and propVal0 is not None:
        props[propId0] = propVal0
    if propId1 and propVal1 is not None:
        props[propId1] = propVal1

    # From JSON blob (convenience alternative)
    if properties_json:
        try:
            parsed = json.loads(properties_json)
            if isinstance(parsed, dict):
                props.update(parsed)
        except (json.JSONDecodeError, TypeError):
            pass

    return props
