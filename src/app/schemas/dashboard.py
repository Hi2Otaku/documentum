"""Dashboard response schemas for BAM metrics."""
import uuid
from datetime import datetime

from pydantic import BaseModel


class WorkflowCountByState(BaseModel):
    state: str
    count: int


class WorkflowSummary(BaseModel):
    total: int
    by_state: list[WorkflowCountByState]
    avg_completion_seconds: float | None = None


class BottleneckActivity(BaseModel):
    activity_template_id: uuid.UUID
    activity_name: str
    template_name: str
    avg_duration_seconds: float
    total_instances: int
    currently_active: int


class UserWorkload(BaseModel):
    user_id: uuid.UUID
    username: str
    available_count: int
    acquired_count: int
    total_pending: int


class TemplateMetric(BaseModel):
    template_id: uuid.UUID
    template_name: str
    total_instances: int
    running: int
    finished: int
    failed: int
    avg_completion_seconds: float | None = None
