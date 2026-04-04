"""Admin query interface endpoints — multi-criteria search."""
import math

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.common import EnvelopeResponse, PaginationMeta
from app.schemas.query import (
    AuditLogQueryRequest,
    AuditLogQueryResult,
    DocumentQueryRequest,
    DocumentQueryResult,
    WorkflowQueryRequest,
    WorkflowQueryResult,
    WorkItemQueryRequest,
    WorkItemQueryResult,
)
from app.services import query_service

router = APIRouter(prefix="/query", tags=["query"])


@router.post(
    "/workflows",
    response_model=EnvelopeResponse[list[WorkflowQueryResult]],
)
async def query_workflows(
    request: WorkflowQueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Query workflow instances with multi-criteria filtering."""
    results, total = await query_service.query_workflows(db, request)
    return EnvelopeResponse(
        data=results,
        meta=PaginationMeta(
            page=(request.skip // request.limit) + 1 if request.limit > 0 else 1,
            page_size=request.limit,
            total_count=total,
            total_pages=math.ceil(total / request.limit) if request.limit > 0 else 0,
        ),
    )


@router.post(
    "/work-items",
    response_model=EnvelopeResponse[list[WorkItemQueryResult]],
)
async def query_work_items(
    request: WorkItemQueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Query work items with multi-criteria filtering."""
    results, total = await query_service.query_work_items(db, request)
    return EnvelopeResponse(
        data=results,
        meta=PaginationMeta(
            page=(request.skip // request.limit) + 1 if request.limit > 0 else 1,
            page_size=request.limit,
            total_count=total,
            total_pages=math.ceil(total / request.limit) if request.limit > 0 else 0,
        ),
    )


@router.post(
    "/documents",
    response_model=EnvelopeResponse[list[DocumentQueryResult]],
)
async def query_documents(
    request: DocumentQueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Query documents with multi-criteria filtering."""
    results, total = await query_service.query_documents(db, request)
    return EnvelopeResponse(
        data=results,
        meta=PaginationMeta(
            page=(request.skip // request.limit) + 1 if request.limit > 0 else 1,
            page_size=request.limit,
            total_count=total,
            total_pages=math.ceil(total / request.limit) if request.limit > 0 else 0,
        ),
    )


@router.post(
    "/audit-logs",
    response_model=EnvelopeResponse[list[AuditLogQueryResult]],
)
async def query_audit_logs(
    request: AuditLogQueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Query audit logs with multi-criteria filtering."""
    results, total = await query_service.query_audit_logs(db, request)
    return EnvelopeResponse(
        data=results,
        meta=PaginationMeta(
            page=(request.skip // request.limit) + 1 if request.limit > 0 else 1,
            page_size=request.limit,
            total_count=total,
            total_pages=math.ceil(total / request.limit) if request.limit > 0 else 0,
        ),
    )
