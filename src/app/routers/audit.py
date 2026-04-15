"""Audit trail query endpoints."""
import hashlib
import json
import math
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_admin
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.audit import AuditBreak, AuditLogResponse, AuditVerifyResponse
from app.schemas.common import EnvelopeResponse, PaginationMeta

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=EnvelopeResponse[list[AuditLogResponse]])
async def query_audit(
    user_id: str | None = Query(None),
    workflow_id: str | None = Query(None),
    document_id: str | None = Query(None),
    action_type: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Query audit trail with filters. Admin only."""
    conditions = []
    if user_id:
        conditions.append(AuditLog.user_id == user_id)
    if workflow_id:
        conditions.append(AuditLog.entity_id == workflow_id)
    if document_id:
        conditions.append(AuditLog.entity_id == document_id)
    if action_type:
        conditions.append(AuditLog.action == action_type)
    if date_from:
        conditions.append(AuditLog.timestamp >= date_from)
    if date_to:
        conditions.append(AuditLog.timestamp <= date_to)

    base_query = select(AuditLog).where(*conditions) if conditions else select(AuditLog)
    count_query = select(func.count()).select_from(base_query.subquery())
    count_result = await db.execute(count_query)
    total_count = count_result.scalar_one()

    result = await db.execute(
        base_query.order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit)
    )
    records = list(result.scalars().all())

    return EnvelopeResponse(
        data=[AuditLogResponse.model_validate(r) for r in records],
        meta=PaginationMeta(
            page=(skip // limit) + 1,
            page_size=limit,
            total_count=total_count,
            total_pages=math.ceil(total_count / limit) if limit > 0 else 0,
        ),
    )


@router.post("/verify", response_model=AuditVerifyResponse)
async def verify_integrity(
    limit: int = Query(100000, ge=1, le=1000000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Verify audit trail integrity by recomputing hash chain. Admin only."""
    # Count total records
    total_result = await db.execute(select(func.count()).select_from(AuditLog))
    total_records = total_result.scalar_one()

    # Count pending records (chain_hash is NULL)
    pending_result = await db.execute(
        select(func.count()).select_from(AuditLog).where(AuditLog.chain_hash.is_(None))
    )
    pending_records = pending_result.scalar_one()

    # Fetch chained records ordered by chain_sequence
    chained_query = (
        select(AuditLog)
        .where(AuditLog.chain_sequence.isnot(None))
        .order_by(AuditLog.chain_sequence.asc())
        .limit(limit)
    )
    result = await db.execute(chained_query)
    chained_records = list(result.scalars().all())

    breaks: list[AuditBreak] = []
    previous_chain_hash = "GENESIS"
    expected_sequence = 1 if chained_records else 0

    for record in chained_records:
        # Check sequence gap
        if record.chain_sequence != expected_sequence:
            breaks.append(
                AuditBreak(
                    chain_sequence=record.chain_sequence,
                    record_id=str(record.id),
                    type="sequence_gap",
                    details=f"Expected sequence {expected_sequence}, found {record.chain_sequence}",
                )
            )
            expected_sequence = record.chain_sequence

        # Recompute content_hash
        canonical_data = {
            "id": str(record.id),
            "timestamp": record.timestamp.isoformat() if record.timestamp else None,
            "entity_type": record.entity_type,
            "entity_id": record.entity_id,
            "action": record.action,
            "user_id": record.user_id,
            "before_state": record.before_state,
            "after_state": record.after_state,
            "details": record.details,
        }
        canonical_json = json.dumps(canonical_data, sort_keys=True, default=str)
        recomputed_content_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

        if recomputed_content_hash != record.content_hash:
            breaks.append(
                AuditBreak(
                    chain_sequence=record.chain_sequence,
                    record_id=str(record.id),
                    type="content_tampered",
                    details=f"Stored content_hash {record.content_hash} != recomputed {recomputed_content_hash}",
                )
            )

        # Recompute chain_hash
        chain_input = f"{recomputed_content_hash}:{previous_chain_hash}"
        recomputed_chain_hash = hashlib.sha256(chain_input.encode("utf-8")).hexdigest()

        if recomputed_chain_hash != record.chain_hash:
            breaks.append(
                AuditBreak(
                    chain_sequence=record.chain_sequence,
                    record_id=str(record.id),
                    type="chain_broken",
                    details=f"Stored chain_hash {record.chain_hash} != recomputed {recomputed_chain_hash}",
                )
            )

        # Use the STORED chain_hash as previous for next iteration
        # (so one tampered record doesn't cascade false positives)
        previous_chain_hash = record.chain_hash
        expected_sequence += 1

    return AuditVerifyResponse(
        status="fail" if breaks else "pass",
        total_records=total_records,
        chained_records=len(chained_records),
        pending_records=pending_records,
        breaks=breaks,
        verified_at=datetime.now(timezone.utc),
    )
