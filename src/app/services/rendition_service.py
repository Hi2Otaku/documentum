"""Service layer for document renditions.

Handles creating rendition requests, querying rendition status,
retrying failed renditions, and downloading rendition content.
"""
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import RenditionStatus, RenditionType
from app.models.rendition import Rendition


async def create_rendition_request(
    db: AsyncSession,
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    rendition_type: RenditionType,
    user_id: str | None = None,
) -> Rendition:
    """Create a PENDING rendition record and dispatch the Celery task."""
    rendition = Rendition(
        id=uuid.uuid4(),
        document_version_id=version_id,
        rendition_type=rendition_type,
        status=RenditionStatus.PENDING,
        created_by=user_id,
    )
    db.add(rendition)
    await db.flush()

    # Dispatch Celery task
    _dispatch_rendition_task(
        rendition_id=str(rendition.id),
        document_version_id=str(version_id),
        document_id=str(document_id),
        rendition_type=rendition_type,
    )

    return rendition


def _dispatch_rendition_task(
    rendition_id: str,
    document_version_id: str,
    document_id: str,
    rendition_type: RenditionType,
) -> None:
    """Dispatch the appropriate Celery task for the rendition type."""
    from app.tasks.rendition import generate_pdf_rendition, generate_thumbnail

    if rendition_type == RenditionType.PDF:
        generate_pdf_rendition.delay(rendition_id, document_version_id, document_id)
    elif rendition_type == RenditionType.THUMBNAIL:
        generate_thumbnail.delay(rendition_id, document_version_id, document_id)


async def get_renditions_for_version(
    db: AsyncSession,
    document_id: uuid.UUID,
    version_id: uuid.UUID,
) -> list[Rendition]:
    """List all renditions for a specific document version."""
    result = await db.execute(
        select(Rendition)
        .where(
            Rendition.document_version_id == version_id,
            Rendition.is_deleted == False,  # noqa: E712
        )
        .order_by(Rendition.created_at.desc())
    )
    return list(result.scalars().all())


async def get_rendition(db: AsyncSession, rendition_id: uuid.UUID) -> Rendition:
    """Get a single rendition by ID. Raises 404 if not found."""
    result = await db.execute(
        select(Rendition).where(
            Rendition.id == rendition_id,
            Rendition.is_deleted == False,  # noqa: E712
        )
    )
    rendition = result.scalar_one_or_none()
    if rendition is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rendition not found",
        )
    return rendition


async def retry_rendition(
    db: AsyncSession,
    rendition_id: uuid.UUID,
) -> Rendition:
    """Retry a failed rendition by resetting status and re-dispatching."""
    rendition = await get_rendition(db, rendition_id)

    if rendition.status != RenditionStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only retry failed renditions, current status: {rendition.status}",
        )

    rendition.status = RenditionStatus.PENDING
    rendition.error_message = None
    await db.flush()

    # We need the document_id for the MinIO path; get it from the version
    from app.models.document import DocumentVersion

    ver_result = await db.execute(
        select(DocumentVersion).where(
            DocumentVersion.id == rendition.document_version_id
        )
    )
    version = ver_result.scalar_one_or_none()
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated document version not found",
        )

    _dispatch_rendition_task(
        rendition_id=str(rendition.id),
        document_version_id=str(rendition.document_version_id),
        document_id=str(version.document_id),
        rendition_type=RenditionType(rendition.rendition_type),
    )

    return rendition


async def download_rendition(
    db: AsyncSession,
    rendition_id: uuid.UUID,
) -> tuple[bytes, Rendition]:
    """Download the content of a ready rendition from MinIO."""
    rendition = await get_rendition(db, rendition_id)

    if rendition.status != RenditionStatus.READY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rendition is not ready, current status: {rendition.status}",
        )

    if rendition.minio_object_key is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Rendition marked ready but has no storage key",
        )

    from app.core.minio_client import download_object

    content = await download_object(rendition.minio_object_key)
    return content, rendition
