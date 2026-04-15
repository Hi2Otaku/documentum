"""Pydantic schemas for bulk operation requests and responses."""
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BulkUpdateRequest(BaseModel):
    document_ids: list[str] = Field(..., min_length=1, max_length=500)
    metadata: dict[str, Any]


class BulkDeleteRequest(BaseModel):
    document_ids: list[str] = Field(..., min_length=1, max_length=500)


class BulkLifecycleRequest(BaseModel):
    document_ids: list[str] = Field(..., min_length=1, max_length=500)
    target_state: str = Field(
        ..., pattern="^(draft|review|approved|archived)$"
    )


class BulkJobItemResult(BaseModel):
    document_id: str
    status: str  # "success" | "error"
    error: str | None = None


class BulkJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_type: str
    status: str
    total_count: int
    success_count: int
    failure_count: int
    results: list[dict] | None = None
    created_by: str
    created_at: str
    completed_at: str | None = None
