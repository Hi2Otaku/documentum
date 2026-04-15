"""API endpoints for document import/export operations."""
import io
import math
import zipfile

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core import minio_client
from app.models.user import User
from app.schemas.common import EnvelopeResponse, PaginationMeta
from app.schemas.import_export import (
    ExportRequest,
    ImportExportJobResponse,
    ImportRequest,
)
from app.services import import_export_service

router = APIRouter(prefix="/import-export", tags=["import-export"])


def _job_response(job) -> ImportExportJobResponse:
    """Convert a BulkJob model to an ImportExportJobResponse."""
    download_ready = (
        job.status == "completed"
        and job.job_type == "export"
        and bool((job.parameters or {}).get("zip_object_key"))
    )
    return ImportExportJobResponse(
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
        download_ready=download_ready,
    )


@router.post(
    "/export",
    response_model=EnvelopeResponse[ImportExportJobResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_export(
    req: ExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit a document/folder export job."""
    job = await import_export_service.create_export_job(
        db, req, str(current_user.id)
    )
    return EnvelopeResponse(data=_job_response(job))


@router.post(
    "/import",
    response_model=EnvelopeResponse[ImportExportJobResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_import(
    file: UploadFile = File(...),
    target_folder_id: str | None = Form(None),
    conflict_strategy: str = Form("skip"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a ZIP file for import."""
    # Read and validate ZIP
    file_bytes = await file.read()
    if not zipfile.is_zipfile(io.BytesIO(file_bytes)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is not a valid ZIP archive",
        )

    import_req = ImportRequest(
        target_folder_id=target_folder_id,
        conflict_strategy=conflict_strategy,
    )
    job = await import_export_service.create_import_job(
        db, file_bytes, import_req, str(current_user.id)
    )
    return EnvelopeResponse(data=_job_response(job))


@router.get(
    "/jobs",
    response_model=EnvelopeResponse[list[ImportExportJobResponse]],
)
async def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List import/export jobs for the current user."""
    jobs, total = await import_export_service.get_import_export_jobs(
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
    response_model=EnvelopeResponse[ImportExportJobResponse],
)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single import/export job by ID."""
    job = await import_export_service.get_import_export_job(
        db, job_id, str(current_user.id)
    )
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Import/export job not found",
        )
    return EnvelopeResponse(data=_job_response(job))


@router.get("/download/{job_id}")
async def download_export(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download the ZIP for a completed export job."""
    job = await import_export_service.get_import_export_job(
        db, job_id, str(current_user.id)
    )
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Import/export job not found",
        )
    if job.job_type != "export":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job is not an export",
        )
    if job.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Export is not completed yet",
        )

    zip_key = (job.parameters or {}).get("zip_object_key")
    if not zip_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No export file available",
        )

    zip_data = await minio_client.download_object(zip_key)
    return StreamingResponse(
        io.BytesIO(zip_data),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="export_{job_id}.zip"',
        },
    )
