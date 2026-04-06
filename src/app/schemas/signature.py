"""Pydantic schemas for digital signatures."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SignDocumentRequest(BaseModel):
    """Request body for signing a document version."""

    certificate_pem: str = Field(
        ..., description="PEM-encoded X.509 certificate for signing"
    )
    private_key_pem: str = Field(
        ..., description="PEM-encoded private key (not stored server-side)"
    )
    reason: str | None = Field(
        default=None, max_length=1000, description="Reason for signing"
    )


class SignatureResponse(BaseModel):
    """Response for a single document signature."""

    id: uuid.UUID
    version_id: uuid.UUID
    signer_id: uuid.UUID
    signer_cn: str
    signed_at: datetime
    content_hash: str
    algorithm: str
    reason: str | None
    is_valid: bool = Field(
        default=True, description="Whether the signature is currently valid"
    )
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SignatureVerifyResponse(BaseModel):
    """Response from verifying a specific signature."""

    signature_id: uuid.UUID
    is_valid: bool
    signer_cn: str
    signed_at: datetime
    content_hash_match: bool
    detail: str
