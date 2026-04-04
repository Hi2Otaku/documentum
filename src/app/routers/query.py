"""Admin query endpoints for workflows, work items, and documents."""
import math
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_admin
from app.models.user import User
from app.schemas.common import EnvelopeResponse, PaginationMeta
from app.schemas.query import (
    DocumentQueryResponse,
    WorkflowQueryResponse,
    WorkItemQueryResponse,
)
from app.services import query_service

router = APIRouter(prefix="/query", tags=["query"])


@router.get("/workflows", response_model=EnvelopeResponse[list[WorkflowQueryResponse]])
async def query_workflows_endpoint(
    template_id: uuid.UUID | None = Query(None),
    state: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    started_by: uuid.UUID | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Query workflow instances with multi-criteria filtering. Admin only."""
    items, total_count = await query_service.query_workflows(
        db,
        template_id=template_id,
        state=state,
        date_from=date_from,
        date_to=date_to,
        started_by=started_by,
        skip=skip,
        limit=limit,
    )
    return EnvelopeResponse(
        data=items,
        meta=PaginationMeta(
            page=(skip // limit) + 1,
            page_size=limit,
            total_count=total_count,
            total_pages=math.ceil(total_count / limit) if limit > 0 else 0,
        ),
    )


@router.get("/work-items", response_model=EnvelopeResponse[list[WorkItemQueryResponse]])
async def query_work_items_endpoint(
    assignee_id: uuid.UUID | None = Query(None),
    state: str | None = Query(None),
    workflow_id: uuid.UUID | None = Query(None),
    priority: int | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Query work items with multi-criteria filtering. Admin only."""
    items, total_count = await query_service.query_work_items(
        db,
        assignee_id=assignee_id,
        state=state,
        workflow_id=workflow_id,
        priority=priority,
        skip=skip,
        limit=limit,
    )
    return EnvelopeResponse(
        data=items,
        meta=PaginationMeta(
            page=(skip // limit) + 1,
            page_size=limit,
            total_count=total_count,
            total_pages=math.ceil(total_count / limit) if limit > 0 else 0,
        ),
    )


@router.get("/documents", response_model=EnvelopeResponse[list[DocumentQueryResponse]])
async def query_documents_endpoint(
    lifecycle_state: str | None = Query(None),
    metadata_key: str | None = Query(None),
    metadata_value: str | None = Query(None),
    version: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Query documents with multi-criteria filtering. Admin only."""
    items, total_count = await query_service.query_documents(
        db,
        lifecycle_state=lifecycle_state,
        metadata_key=metadata_key,
        metadata_value=metadata_value,
        version=version,
        skip=skip,
        limit=limit,
    )
    return EnvelopeResponse(
        data=items,
        meta=PaginationMeta(
            page=(skip // limit) + 1,
            page_size=limit,
            total_count=total_count,
            total_pages=math.ceil(total_count / limit) if limit > 0 else 0,
        ),
    )
