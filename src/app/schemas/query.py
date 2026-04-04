"""Query interface request/response schemas."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class WorkflowQueryRequest(BaseModel):
    template_id: uuid.UUID | None = None
    state: str | None = None
    supervisor_id: uuid.UUID | None = None
    started_after: datetime | None = None
    started_before: datetime | None = None
    completed_after: datetime | None = None
    completed_before: datetime | None = None
    skip: int = 0
    limit: int = 20


class WorkItemQueryRequest(BaseModel):
    performer_id: uuid.UUID | None = None
    state: str | None = None
    workflow_id: uuid.UUID | None = None
    priority_min: int | None = None
    priority_max: int | None = None
    due_before: datetime | None = None
    skip: int = 0
    limit: int = 20


class DocumentQueryRequest(BaseModel):
    title_contains: str | None = None
    author: str | None = None
    content_type: str | None = None
    lifecycle_state: str | None = None
    created_after: datetime | None = None
    created_before: datetime | None = None
    skip: int = 0
    limit: int = 20


class AuditLogQueryRequest(BaseModel):
    entity_type: str | None = None
    entity_id: str | None = None
    action: str | None = None
    user_id: str | None = None
    after: datetime | None = None
    before: datetime | None = None
    skip: int = 0
    limit: int = 20


class WorkflowQueryResult(BaseModel):
    id: uuid.UUID
    process_template_id: uuid.UUID
    state: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    supervisor_id: uuid.UUID | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class WorkItemQueryResult(BaseModel):
    id: uuid.UUID
    activity_instance_id: uuid.UUID
    performer_id: uuid.UUID | None = None
    state: str
    priority: int
    due_date: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DocumentQueryResult(BaseModel):
    id: uuid.UUID
    title: str
    author: str | None = None
    filename: str
    content_type: str
    lifecycle_state: str | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AuditLogQueryResult(BaseModel):
    id: uuid.UUID
    timestamp: datetime
    entity_type: str
    entity_id: str
    action: str
    user_id: str | None = None
    details: str | None = None
    model_config = ConfigDict(from_attributes=True)
