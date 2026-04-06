import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.common import EnvelopeResponse
from app.schemas.rendition import RenditionResponse
from app.services import rendition_service

router = APIRouter(tags=["renditions"])


@router.get(
    "/documents/{document_id}/versions/{version_id}/renditions",
    response_model=EnvelopeResponse[list[RenditionResponse]],
)
async def list_renditions(
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all renditions for a document version."""
    renditions = await rendition_service.get_renditions_for_version(
        db, document_id, version_id
    )
    return EnvelopeResponse(
        data=[RenditionResponse.model_validate(r) for r in renditions]
    )


@router.get(
    "/renditions/{rendition_id}",
    response_model=EnvelopeResponse[RenditionResponse],
)
async def get_rendition(
    rendition_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single rendition by ID."""
    rendition = await rendition_service.get_rendition(db, rendition_id)
    return EnvelopeResponse(data=RenditionResponse.model_validate(rendition))


@router.get(
    "/renditions/{rendition_id}/download",
)
async def download_rendition(
    rendition_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download the content of a ready rendition."""
    content, rendition = await rendition_service.download_rendition(db, rendition_id)

    filename = "rendition"
    if rendition.content_type == "application/pdf":
        filename = "rendition.pdf"
    elif rendition.content_type == "image/png":
        filename = "thumbnail.png"

    return Response(
        content=content,
        media_type=rendition.content_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.post(
    "/renditions/{rendition_id}/retry",
    response_model=EnvelopeResponse[RenditionResponse],
)
async def retry_rendition(
    rendition_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retry a failed rendition."""
    rendition = await rendition_service.retry_rendition(db, rendition_id)
    return EnvelopeResponse(data=RenditionResponse.model_validate(rendition))
