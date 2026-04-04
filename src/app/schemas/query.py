"""Pydantic response schemas for admin query endpoints."""
from pydantic import BaseModel, ConfigDict


class WorkflowQueryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    template_name: str
    template_version: int
    state: str
    started_by: str | None = None  # username
    started_at: str | None = None  # ISO format
    completed_at: str | None = None
    active_activity: str | None = None  # name of current ACTIVE activity


class WorkItemQueryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    activity_name: str
    workflow_name: str  # template name + ID fragment
    workflow_id: str
    assignee: str | None = None  # username
    state: str
    priority: int
    created_at: str  # ISO format


class DocumentQueryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    lifecycle_state: str | None = None
    current_version: str  # e.g. "2.1"
    author: str | None = None
    created_by: str | None = None
    updated_at: str  # ISO format
    content_type: str
