"""Pydantic schemas for process analytics and mining responses."""
from __future__ import annotations

from pydantic import BaseModel


class ExecutionPathStep(BaseModel):
    activity_name: str
    avg_duration_seconds: float | None = None


class ExecutionPath(BaseModel):
    path: list[str]
    frequency: int
    avg_total_duration_seconds: float | None = None


class CycleTimeStats(BaseModel):
    activity_name: str | None = None
    template_name: str | None = None
    template_id: str | None = None
    avg_seconds: float
    median_seconds: float
    min_seconds: float
    max_seconds: float
    sample_count: int


class BottleneckActivity(BaseModel):
    activity_name: str
    template_name: str
    avg_duration_seconds: float
    total_executions: int
    pct_of_total_time: float


class AnalyticsSummary(BaseModel):
    total_instances: int
    completed_instances: int
    avg_completion_seconds: float | None = None
    paths_discovered: int
    last_refreshed: str | None = None
