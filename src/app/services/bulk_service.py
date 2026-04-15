"""Service layer for bulk document operations."""
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bulk_job import BulkJob


async def create_bulk_job(
    db: AsyncSession,
    job_type: str,
    document_ids: list[str],
    parameters: dict | None,
    user_id: str,
) -> BulkJob:
    """Create a BulkJob record and dispatch the Celery task."""
    job = BulkJob(
        id=uuid.uuid4(),
        job_type=job_type,
        status="pending",
        document_ids=document_ids,
        parameters=parameters,
        total_count=len(document_ids),
        success_count=0,
        failure_count=0,
        created_by=user_id,
    )
    db.add(job)
    await db.flush()

    # Dispatch Celery task for background execution
    from app.tasks.bulk_operations import execute_bulk_job
    execute_bulk_job.delay(str(job.id))

    return job


async def get_bulk_jobs(
    db: AsyncSession,
    user_id: str,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[BulkJob], int]:
    """Get paginated list of bulk jobs for a user."""
    base = select(BulkJob).where(BulkJob.created_by == user_id)

    count_result = await db.execute(
        select(func.count()).select_from(base.subquery())
    )
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(
        base.order_by(BulkJob.created_at.desc()).offset(offset).limit(page_size)
    )
    return list(result.scalars().all()), total


async def get_bulk_job(
    db: AsyncSession,
    job_id: str,
    user_id: str,
) -> BulkJob | None:
    """Get a single bulk job by ID, verifying ownership."""
    result = await db.execute(
        select(BulkJob).where(
            BulkJob.id == uuid.UUID(job_id),
            BulkJob.created_by == user_id,
        )
    )
    return result.scalar_one_or_none()
