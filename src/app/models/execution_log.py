"""AutoActivityLog model for tracking auto method execution.

Records each execution attempt of an automated activity, including
status, error details, timing, and result data for retry/audit purposes.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class AutoActivityLog(BaseModel):
    __tablename__ = "auto_activity_logs"

    activity_instance_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("activity_instances.id"), nullable=False, index=True
    )
    method_name: Mapped[str] = mapped_column(String(255), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "success", "error", "timeout", "skipped"
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_traceback: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    result_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # One-directional relationship to ActivityInstance
    activity_instance = relationship("ActivityInstance", lazy="selectin")
