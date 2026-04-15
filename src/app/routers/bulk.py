"""API endpoints for bulk document operations."""
import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.bulk_job import (
    BulkDeleteRequest,
    BulkJobResponse,
    BulkLifecycleRequest,
    BulkUpdateRequest,
)
from app.schemas.common import EnvelopeResponse, PaginationMeta
from app.services import bulk_service

router = APIRouter(prefix="/bulk", tags=["bulk"])


def _job_response(job) -> BulkJobResponse:
    """Convert a BulkJob model to a BulkJobResponse."""
    return BulkJobResponse(
        id=str(job.id),
        job_type=job.job_type,
        status=job.status,
        total_count=job.total_count,
        success_count=job.success_count,
        failure_count=job.failure_count,
        results=job.results,
        created_by=job.created_by,
        created_at=job.created_at.isoformat() if job.created_at else "",
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
    )


@router.post(
    "/update",
    response_model=EnvelopeResponse[BulkJobResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
async def bulk_update(
    req: BulkUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit a bulk metadata update job."""
    job = await bulk_service.create_bulk_job(
        db, "update", req.document_ids, {"metadata": req.metadata}, str(current_user.id)
    )
    return EnvelopeResponse(data=_job_response(job))


@router.post(
    "/delete",
    response_model=EnvelopeResponse[BulkJobResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
async def bulk_delete(
    req: BulkDeleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit a bulk delete job."""
    job = await bulk_service.create_bulk_job(
        db, "delete", req.document_ids, None, str(current_user.id)
    )
    return EnvelopeResponse(data=_job_response(job))


@router.post(
    "/lifecycle",
    response_model=EnvelopeResponse[BulkJobResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
async def bulk_lifecycle(
    req: BulkLifecycleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit a bulk lifecycle transition job."""
    job = await bulk_service.create_bulk_job(
        db, "lifecycle", req.document_ids, {"target_state": req.target_state}, str(current_user.id)
    )
    return EnvelopeResponse(data=_job_response(job))


@router.get(
    "/jobs",
    response_model=EnvelopeResponse[list[BulkJobResponse]],
)
async def list_bulk_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List bulk jobs for the current user."""
    jobs, total = await bulk_service.get_bulk_jobs(
        db, str(current_user.id), page, page_size
    )
    return EnvelopeResponse(
        data=[_job_response(j) for j in jobs],
        meta=PaginationMeta(
            page=page,
            page_size=page_size,
            total_count=total,
            total_pages=math.ceil(total / page_size) if total > 0 else 0,
        ),
    )


@router.get(
    "/jobs/{job_id}",
    response_model=EnvelopeResponse[BulkJobResponse],
)
async def get_bulk_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single bulk job by ID."""
    job = await bulk_service.get_bulk_job(db, job_id, str(current_user.id))
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bulk job not found",
        )
    return EnvelopeResponse(data=_job_response(job))
