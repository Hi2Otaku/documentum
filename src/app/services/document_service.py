import hashlib
import mimetypes
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.minio_client import delete_object, download_object, upload_object
from app.models.document import Document, DocumentVersion
from app.services.audit_service import create_audit_record
from app.services.event_bus import event_bus


async def upload_document(
    db: AsyncSession,
    file: UploadFile,
    title: str,
    author: str | None,
    custom_properties: dict | None,
    user_id: str,
) -> Document:
    """Upload a new document. Creates Document + initial DocumentVersion (0.1)."""
    doc_id = uuid.uuid4()
    version_id = uuid.uuid4()

    content = await file.read()
    content_hash = hashlib.sha256(content).hexdigest()

    # Determine content type with fallback
    content_type = file.content_type
    if content_type is None:
        guessed, _ = mimetypes.guess_type(file.filename or "")
        content_type = guessed or "application/octet-stream"

    filename = file.filename or "unnamed"
    object_name = f"{doc_id}/{version_id}"

    # Upload to MinIO first
    await upload_object(object_name, content, content_type)

    # Create DB records; clean up MinIO on failure
    try:
        document = Document(
            id=doc_id,
            title=title,
            author=author,
            filename=filename,
            content_type=content_type,
            custom_properties=custom_properties or {},
            created_by=user_id,
            current_major_version=0,
            current_minor_version=1,
        )
        db.add(document)

        version = DocumentVersion(
            id=version_id,
            document_id=doc_id,
            major_version=0,
            minor_version=1,
            content_hash=content_hash,
            content_size=len(content),
            minio_object_key=object_name,
            filename=filename,
            content_type=content_type,
            created_by=user_id,
        )
        db.add(version)

        await db.flush()

        await create_audit_record(
            db,
            entity_type="document",
            entity_id=str(doc_id),
            action="upload",
            user_id=user_id,
            after_state={
                "title": title,
                "version": "0.1",
                "filename": filename,
            },
        )

        # Create ADMIN ACL for document creator (Phase 7)
        from app.services import acl_service
        await acl_service.create_owner_acl(db, document.id, uuid.UUID(user_id))

        # Emit document.uploaded domain event
        await event_bus.emit(
            db,
            event_type="document.uploaded",
            entity_type="document",
            entity_id=document.id,
            actor_id=uuid.UUID(user_id),
            payload={
                "title": title,
                "filename": filename,
                "content_type": content_type,
                "version": "0.1",
            },
        )
    except Exception:
        await delete_object(object_name)
        raise

    return document


async def get_document(db: AsyncSession, document_id: uuid.UUID) -> Document:
    """Get a single document by ID. Raises 404 if not found or soft-deleted."""
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.is_deleted == False,  # noqa: E712
        )
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return document


async def list_documents(
    db: AsyncSession,
    page: int,
    page_size: int,
    title: str | None = None,
    author: str | None = None,
) -> tuple[list[Document], int]:
    """List documents with pagination and optional filters."""
    base_query = select(Document).where(
        Document.is_deleted == False  # noqa: E712
    )

    if title:
        base_query = base_query.where(Document.title.ilike(f"%{title}%"))
    if author:
        base_query = base_query.where(Document.author.ilike(f"%{author}%"))

    # Total count
    count_query = select(func.count()).select_from(base_query.subquery())
    count_result = await db.execute(count_query)
    total_count = count_result.scalar_one()

    # Paginated results
    offset = (page - 1) * page_size
    result = await db.execute(
        base_query.order_by(Document.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    documents = list(result.scalars().all())

    return documents, total_count


async def update_document_metadata(
    db: AsyncSession,
    document_id: uuid.UUID,
    title: str | None,
    author: str | None,
    custom_properties: dict | None,
    user_id: str,
) -> Document:
    """Update document metadata fields. Only non-None fields are changed."""
    document = await get_document(db, document_id)

    before_state = {
        "title": document.title,
        "author": document.author,
        "custom_properties": document.custom_properties,
    }

    if title is not None:
        document.title = title
    if author is not None:
        document.author = author
    if custom_properties is not None:
        document.custom_properties = custom_properties

    await db.flush()

    after_state = {
        "title": document.title,
        "author": document.author,
        "custom_properties": document.custom_properties,
    }

    await create_audit_record(
        db,
        entity_type="document",
        entity_id=str(document_id),
        action="update_metadata",
        user_id=user_id,
        before_state=before_state,
        after_state=after_state,
    )

    return document


async def checkout_document(
    db: AsyncSession,
    document_id: uuid.UUID,
    user_id: str,
) -> Document:
    """Check out (lock) a document for editing."""
    document = await get_document(db, document_id)

    if document.locked_by is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Document is already checked out by user {document.locked_by}",
        )

    document.locked_by = uuid.UUID(user_id)
    document.locked_at = datetime.now(timezone.utc)

    await db.flush()

    await create_audit_record(
        db,
        entity_type="document",
        entity_id=str(document_id),
        action="checkout",
        user_id=user_id,
    )

    return document


async def checkin_document(
    db: AsyncSession,
    document_id: uuid.UUID,
    file: UploadFile,
    user_id: str,
    comment: str | None = None,
) -> DocumentVersion | None:
    """Check in a document with a new file version.

    Returns None if the content is unchanged (SHA-256 dedup).
    Releases the lock in all cases.
    """
    document = await get_document(db, document_id)

    # Verify caller holds the lock
    if document.locked_by is None or str(document.locked_by) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not hold the lock on this document",
        )

    content = await file.read()
    content_hash = hashlib.sha256(content).hexdigest()

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
    latest_version = result.scalar_one_or_none()

    # SHA-256 dedup: if content unchanged, just release lock
    if latest_version is not None and latest_version.content_hash == content_hash:
        document.locked_by = None
        document.locked_at = None
        await db.flush()
        return None

    # Create new version with minor increment
    new_major = latest_version.major_version if latest_version else 0
    new_minor = (latest_version.minor_version + 1) if latest_version else 1

    version_id = uuid.uuid4()
    object_name = f"{document_id}/{version_id}"

    content_type = file.content_type
    if content_type is None:
        guessed, _ = mimetypes.guess_type(file.filename or "")
        content_type = guessed or "application/octet-stream"

    filename = file.filename or "unnamed"

    await upload_object(object_name, content, content_type)

    try:
        new_version = DocumentVersion(
            id=version_id,
            document_id=document_id,
            major_version=new_major,
            minor_version=new_minor,
            content_hash=content_hash,
            content_size=len(content),
            minio_object_key=object_name,
            filename=filename,
            content_type=content_type,
            comment=comment,
            created_by=user_id,
        )
        db.add(new_version)

        document.current_major_version = new_major
        document.current_minor_version = new_minor
        document.locked_by = None
        document.locked_at = None

        await db.flush()

        await create_audit_record(
            db,
            entity_type="document",
            entity_id=str(document_id),
            action="checkin",
            user_id=user_id,
            after_state={
                "version": f"{new_major}.{new_minor}",
                "filename": filename,
                "comment": comment,
            },
        )
    except Exception:
        await delete_object(object_name)
        raise

    return new_version


async def force_unlock_document(
    db: AsyncSession,
    document_id: uuid.UUID,
    admin_user_id: str,
) -> Document:
    """Force-unlock a document (admin only)."""
    document = await get_document(db, document_id)

    if document.locked_by is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document is not checked out",
        )

    previous_holder = str(document.locked_by)

    document.locked_by = None
    document.locked_at = None

    await db.flush()

    await create_audit_record(
        db,
        entity_type="document",
        entity_id=str(document_id),
        action="force_unlock",
        user_id=admin_user_id,
        details=f"Force-unlocked document previously held by user {previous_holder}",
    )

    return document


async def list_versions(
    db: AsyncSession,
    document_id: uuid.UUID,
) -> list[DocumentVersion]:
    """List all versions of a document, newest first."""
    # Verify document exists
    await get_document(db, document_id)

    result = await db.execute(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == document_id)
        .order_by(
            DocumentVersion.major_version.desc(),
            DocumentVersion.minor_version.desc(),
        )
    )
    return list(result.scalars().all())


async def get_version(
    db: AsyncSession,
    document_id: uuid.UUID,
    version_id: uuid.UUID,
) -> DocumentVersion:
    """Get a specific version of a document."""
    result = await db.execute(
        select(DocumentVersion).where(
            DocumentVersion.id == version_id,
            DocumentVersion.document_id == document_id,
        )
    )
    version = result.scalar_one_or_none()
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document version not found",
        )
    return version


async def download_version_content(
    db: AsyncSession,
    document_id: uuid.UUID,
    version_id: uuid.UUID,
) -> tuple[bytes, DocumentVersion]:
    """Download the content of a specific document version from MinIO."""
    version = await get_version(db, document_id, version_id)
    content = await download_object(version.minio_object_key)
    return content, version


async def promote_to_major_version(
    db: AsyncSession,
    document_id: uuid.UUID,
    user_id: str,
) -> DocumentVersion:
    """Promote the current version to the next major version (e.g., 0.3 -> 1.0).

    Creates a new DocumentVersion with the same content but new version numbers.
    """
    document = await get_document(db, document_id)

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
    latest_version = result.scalar_one_or_none()
    if latest_version is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No versions exist for this document",
        )

    new_major = latest_version.major_version + 1
    new_minor = 0

    version_id = uuid.uuid4()
    new_version = DocumentVersion(
        id=version_id,
        document_id=document_id,
        major_version=new_major,
        minor_version=new_minor,
        content_hash=latest_version.content_hash,
        content_size=latest_version.content_size,
        minio_object_key=latest_version.minio_object_key,
        filename=latest_version.filename,
        content_type=latest_version.content_type,
        comment=f"Promoted to version {new_major}.{new_minor}",
        created_by=user_id,
    )
    db.add(new_version)

    document.current_major_version = new_major
    document.current_minor_version = new_minor

    await db.flush()

    await create_audit_record(
        db,
        entity_type="document",
        entity_id=str(document_id),
        action="promote_version",
        user_id=user_id,
        after_state={
            "from_version": f"{latest_version.major_version}.{latest_version.minor_version}",
            "to_version": f"{new_major}.{new_minor}",
        },
    )

    return new_version
