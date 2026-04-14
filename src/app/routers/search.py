"""Search API endpoint for full-text document search."""
import math
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.common import EnvelopeResponse, PaginationMeta
from app.schemas.search import SearchResultResponse
from app.services import search_service

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/", response_model=EnvelopeResponse[list[SearchResultResponse]])
async def search_documents_endpoint(
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    folder_id: uuid.UUID | None = Query(None, description="Filter by folder"),
    document_type_id: uuid.UUID | None = Query(None, description="Filter by document type"),
    lifecycle_state: str | None = Query(None, description="Filter by lifecycle state"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search documents by content and metadata with ranked results.

    Supports full-text search across document title, author, and extracted content.
    Results are ranked by relevance with highlighted snippets. Per D-03, D-14.
    Filters apply as AND conditions per D-12.
    """
    skip = (page - 1) * page_size
    results, total = await search_service.search_documents(
        db,
        q,
        folder_id=folder_id,
        document_type_id=document_type_id,
        lifecycle_state=lifecycle_state,
        skip=skip,
        limit=page_size,
        user_id=str(current_user.id),
        is_superuser=current_user.is_superuser,
    )
    # Map result dicts to response schema
    items = [
        SearchResultResponse(
            id=row["id"],
            title=row["title"],
            author=row["author"],
            filename=row["filename"],
            content_type=row["content_type"],
            lifecycle_state=(
                row["lifecycle_state"].value
                if hasattr(row["lifecycle_state"], "value")
                else row["lifecycle_state"]
            ),
            extraction_status=row["extraction_status"],
            document_type_name=row["document_type_name"],
            headline=row["headline"],
            rank=row["rank"],
        )
        for row in results
    ]
    return EnvelopeResponse(
        data=items,
        meta=PaginationMeta(
            page=page,
            page_size=page_size,
            total_count=total,
            total_pages=max(1, math.ceil(total / page_size)),
        ),
    )
