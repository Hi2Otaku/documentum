"""AlertRule model for threshold-based system monitoring alerts."""
import uuid

from sqlalchemy import Boolean, Float, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class AlertRule(BaseModel):
    __tablename__ = "alert_rules"
    __table_args__ = (
        Index("ix_alert_rules_metric_enabled", "metric_name", "enabled"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    metric_name: Mapped[str] = mapped_column(
        String(100), nullable=False,
    )  # e.g. "celery_queue_depth", "db_connection_ok", "redis_ping_ok", "minio_health_ok"
    operator: Mapped[str] = mapped_column(
        String(10), nullable=False,
    )  # one of "gt", "lt", "eq", "gte", "lte"
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notification_message: Mapped[str | None] = mapped_column(Text, nullable=True)
