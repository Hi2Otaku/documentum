import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SignRequest(BaseModel):
    """Request body for signing a document version."""
    private_key_pem: str = Field(
        ...,
        description="PEM-encoded private key for signing",
    )
    certificate_pem: str = Field(
        ...,
        description="PEM-encoded X.509 certificate",
    )


class SignatureResponse(BaseModel):
    """Response for a digital signature record."""
    id: uuid.UUID
    document_version_id: uuid.UUID
    signer_id: uuid.UUID
    digest_algorithm: str
    signed_at: datetime
    is_valid: bool
    certificate_pem: str
    created_at: datetime
    created_by: str | None

    model_config = ConfigDict(from_attributes=True)


class VerifyResponse(BaseModel):
    """Response for signature verification."""
    signature_id: uuid.UUID
    is_valid: bool
    detail: str
