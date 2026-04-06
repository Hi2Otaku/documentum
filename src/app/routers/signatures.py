"""Digital signatures router - sign, verify, and list signatures on document versions."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.common import EnvelopeResponse
from app.schemas.signature import (
    SignatureResponse,
    SignatureVerifyResponse,
    SignDocumentRequest,
)
from app.services import document_service, signature_service

router = APIRouter(prefix="/documents", tags=["signatures"])


@router.post(
    "/{document_id}/versions/{version_id}/signatures",
    response_model=EnvelopeResponse[SignatureResponse],
    status_code=status.HTTP_201_CREATED,
)
async def sign_document_version(
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    body: SignDocumentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sign a specific document version with a PKCS7/CMS digital signature."""
    # Verify document and version exist
    version = await document_service.get_version(db, document_id, version_id)

    sig = await signature_service.sign_version(
        db,
        version=version,
        signer_id=current_user.id,
        certificate_pem=body.certificate_pem,
        private_key_pem=body.private_key_pem,
        reason=body.reason,
    )

    return EnvelopeResponse(
        data=SignatureResponse(
            id=sig.id,
            version_id=sig.version_id,
            signer_id=sig.signer_id,
            signer_cn=sig.signer_cn,
            signed_at=sig.signed_at,
            content_hash=sig.content_hash,
            algorithm=sig.algorithm,
            reason=sig.reason,
            is_valid=True,
            created_at=sig.created_at,
        )
    )


@router.get(
    "/{document_id}/versions/{version_id}/signatures",
    response_model=EnvelopeResponse[list[SignatureResponse]],
)
async def list_version_signatures(
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all signatures on a document version."""
    # Verify document and version exist
    await document_service.get_version(db, document_id, version_id)

    sigs = await signature_service.list_signatures(db, version_id)
    return EnvelopeResponse(
        data=[
            SignatureResponse(
                id=s.id,
                version_id=s.version_id,
                signer_id=s.signer_id,
                signer_cn=s.signer_cn,
                signed_at=s.signed_at,
                content_hash=s.content_hash,
                algorithm=s.algorithm,
                reason=s.reason,
                is_valid=True,
                created_at=s.created_at,
            )
            for s in sigs
        ]
    )


@router.get(
    "/{document_id}/versions/{version_id}/signatures/{signature_id}/verify",
    response_model=EnvelopeResponse[SignatureVerifyResponse],
)
async def verify_signature(
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    signature_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Verify the validity of a specific signature."""
    # Verify document and version exist
    await document_service.get_version(db, document_id, version_id)

    sig = await signature_service.get_signature(db, signature_id)
    if sig.version_id != version_id:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=404, detail="Signature does not belong to this version"
        )

    result = await signature_service.verify_signature(db, sig)
    return EnvelopeResponse(data=SignatureVerifyResponse(**result))
