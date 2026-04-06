"""Digital signature model for document version signing (PKCS7/CMS)."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, LargeBinary, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class DocumentSignature(BaseModel):
    __tablename__ = "document_signatures"

    version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("document_versions.id"), nullable=False, index=True
    )
    signer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("users.id"), nullable=False
    )
    signature_data: Mapped[bytes] = mapped_column(
        LargeBinary, nullable=False, doc="DER-encoded PKCS7/CMS signature"
    )
    certificate_pem: Mapped[str] = mapped_column(
        Text, nullable=False, doc="PEM-encoded X.509 certificate used for signing"
    )
    signer_cn: Mapped[str] = mapped_column(
        String(500), nullable=False, doc="Common Name from the signing certificate"
    )
    signed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    content_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, doc="SHA-256 hash of the signed content"
    )
    algorithm: Mapped[str] = mapped_column(
        String(50), default="sha256WithRSAEncryption", nullable=False
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    version: Mapped["DocumentVersion"] = relationship(  # noqa: F821
        back_populates="signatures",
    )
    signer: Mapped["User"] = relationship()  # noqa: F821
