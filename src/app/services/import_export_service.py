"""Service layer for document import/export operations."""
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bulk_job import BulkJob
from app.schemas.import_export import ExportRequest, ImportRequest


async def create_export_job(
    db: AsyncSession,
    export_req: ExportRequest,
    user_id: str,
) -> BulkJob:
    """Create a BulkJob for export and dispatch the Celery task."""
    # Combine document_ids count + folder_ids count as initial total
    total = len(export_req.document_ids) + len(export_req.folder_ids)

    job = BulkJob(
        id=uuid.uuid4(),
        job_type="export",
        status="pending",
        document_ids=export_req.document_ids,
        parameters={
            "folder_ids": export_req.folder_ids,
            "include_acls": export_req.include_acls,
            "include_relationships": export_req.include_relationships,
        },
        total_count=total,
        success_count=0,
        failure_count=0,
        created_by=user_id,
    )
    db.add(job)
    await db.flush()

    from app.tasks.import_export import execute_export_job
    execute_export_job.delay(str(job.id))

    return job


async def create_import_job(
    db: AsyncSession,
    file_bytes: bytes,
    import_req: ImportRequest,
    user_id: str,
) -> BulkJob:
    """Upload ZIP to MinIO temp key, create BulkJob, dispatch Celery task."""
    job_id = uuid.uuid4()
    zip_key = f"imports/{job_id}.zip"

    # Upload raw ZIP to MinIO for the Celery task to process
    from app.core.minio_client import upload_object
    await upload_object(zip_key, file_bytes, "application/zip")

    job = BulkJob(
        id=job_id,
        job_type="import",
        status="pending",
        document_ids=[],
        parameters={
            "zip_key": zip_key,
            "target_folder_id": import_req.target_folder_id,
            "conflict_strategy": import_req.conflict_strategy,
        },
        total_count=0,  # Will be updated by the task once manifest is parsed
        success_count=0,
        failure_count=0,
        created_by=user_id,
    )
    db.add(job)
    await db.flush()

    from app.tasks.import_export import execute_import_job
    execute_import_job.delay(str(job.id))

    return job


async def get_import_export_jobs(
    db: AsyncSession,
    user_id: str,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[BulkJob], int]:
    """Get paginated list of import/export jobs for a user."""
    base = select(BulkJob).where(
        BulkJob.created_by == user_id,
        BulkJob.job_type.in_(["export", "import"]),
    )

    count_result = await db.execute(
        select(func.count()).select_from(base.subquery())
    )
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(
        base.order_by(BulkJob.created_at.desc()).offset(offset).limit(page_size)
    )
    return list(result.scalars().all()), total


async def get_import_export_job(
    db: AsyncSession,
    job_id: str,
    user_id: str,
) -> BulkJob | None:
    """Get a single import/export job by ID, verifying ownership."""
    result = await db.execute(
        select(BulkJob).where(
            BulkJob.id == uuid.UUID(job_id),
            BulkJob.created_by == user_id,
            BulkJob.job_type.in_(["export", "import"]),
        )
    )
    return result.scalar_one_or_none()
