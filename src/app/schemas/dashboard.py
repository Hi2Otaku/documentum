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


class KpiMetrics(BaseModel):
    running: int
    halted: int
    finished: int
    failed: int
    avg_completion_hours: float


class SlaCompliance(BaseModel):
    activity_name: str
    on_time: int
    overdue: int
    compliance_percent: float


class DashboardBottleneck(BaseModel):
    """Bottleneck data shaped for the frontend contract."""
    activity_name: str
    avg_duration_hours: float
    template_name: str | None = None


class DashboardWorkload(BaseModel):
    """Workload data shaped for the frontend contract."""
    user_id: uuid.UUID
    username: str
    assigned: int
    completed: int
    pending: int


class DashboardMetrics(BaseModel):
    kpi: KpiMetrics
    bottleneck_activities: list[DashboardBottleneck]
    workload: list[DashboardWorkload]
    sla_compliance: list[SlaCompliance]
