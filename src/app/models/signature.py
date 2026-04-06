import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, LargeBinary, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class DigitalSignature(BaseModel):
    __tablename__ = "digital_signatures"

    document_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("document_versions.id"), nullable=False, index=True
    )
    signer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("users.id"), nullable=False
    )
    signature_data: Mapped[bytes] = mapped_column(
        LargeBinary, nullable=False
    )
    certificate_pem: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    digest_algorithm: Mapped[str] = mapped_column(
        String(50), default="sha256", nullable=False
    )
    signed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    is_valid: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    version: Mapped["DocumentVersion"] = relationship(  # noqa: F821
        back_populates="signatures",
    )
    signer: Mapped["User"] = relationship()  # noqa: F821
