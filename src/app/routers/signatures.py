import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.common import EnvelopeResponse
from app.schemas.signature import SignatureResponse, SignRequest, VerifyResponse
from app.services import signature_service

router = APIRouter(prefix="/documents", tags=["signatures"])


@router.post(
    "/{document_id}/versions/{version_id}/sign",
    response_model=EnvelopeResponse[SignatureResponse],
    status_code=status.HTTP_201_CREATED,
)
async def sign_version(
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    body: SignRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Digitally sign a specific document version with PKCS7/CMS."""
    sig = await signature_service.sign_document_version(
        db,
        document_id=document_id,
        version_id=version_id,
        user_id=str(current_user.id),
        private_key_pem=body.private_key_pem,
        certificate_pem=body.certificate_pem,
    )
    return EnvelopeResponse(data=SignatureResponse.model_validate(sig))


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
    """List all digital signatures for a document version."""
    signatures = await signature_service.list_signatures(db, document_id, version_id)
    return EnvelopeResponse(
        data=[SignatureResponse.model_validate(s) for s in signatures]
    )


@router.post(
    "/signatures/{signature_id}/verify",
    response_model=EnvelopeResponse[VerifyResponse],
)
async def verify_signature(
    signature_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Verify a specific digital signature."""
    sig, is_valid, detail = await signature_service.verify_signature(db, signature_id)
    return EnvelopeResponse(
        data=VerifyResponse(
            signature_id=sig.id,
            is_valid=is_valid,
            detail=detail,
        )
    )
