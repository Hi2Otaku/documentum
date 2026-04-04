"""Pre-aggregated dashboard metrics for chart data."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class MetricsSummary(BaseModel):
    __tablename__ = "metrics_summary"

    metric_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("process_templates.id"), nullable=True
    )
    dimension_key: Mapped[str] = mapped_column(String(255), nullable=False)
    dimension_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    numeric_value: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    count_value: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
