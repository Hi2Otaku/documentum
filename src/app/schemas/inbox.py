"""Pydantic schemas for work-item inbox feature.

Provides nested response models with activity, workflow, and document
summaries so the inbox UI can render rich work-item cards without
additional API calls (per D-02 nested response pattern).
"""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.enums import WorkflowState, WorkItemState


class ActivitySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    activity_type: str
    instructions: str | None = None


class WorkflowSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    template_name: str
    state: WorkflowState


class DocumentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: uuid.UUID | None = None
    package_name: str | None = None


class CommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    content: str
    created_at: datetime


class CommentCreateRequest(BaseModel):
    content: str


class InboxItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    state: WorkItemState
    priority: int
    due_date: datetime | None = None
    instructions: str | None = None
    performer_id: uuid.UUID | None = None
    created_at: datetime
    completed_at: datetime | None = None
    activity: ActivitySummary
    workflow: WorkflowSummary
    documents: list[DocumentSummary] = []
    comment_count: int = 0


class InboxItemDetailResponse(InboxItemResponse):
    comments: list[CommentResponse] = []


class AcquireResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    state: WorkItemState
    performer_id: uuid.UUID | None = None


class CompleteFromInboxRequest(BaseModel):
    output_variables: dict[str, Any] = {}


class RejectFromInboxRequest(BaseModel):
    reason: str | None = None
