"""Pydantic schemas for document import/export operations."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ExportRequest(BaseModel):
    document_ids: list[str] = Field(default_factory=list)
    folder_ids: list[str] = Field(default_factory=list)
    include_acls: bool = Field(default=True)
    include_relationships: bool = Field(default=True)

    @model_validator(mode="after")
    def at_least_one(self):
        if not self.document_ids and not self.folder_ids:
            raise ValueError("At least one of document_ids or folder_ids must be provided")
        return self


class ImportRequest(BaseModel):
    target_folder_id: str | None = None
    conflict_strategy: Literal["skip", "overwrite", "rename"] = "skip"


class ImportExportJobResponse(BaseModel):
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
    download_ready: bool = False
