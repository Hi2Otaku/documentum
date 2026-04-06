"""Digital signature service - PKCS7/CMS signing and verification."""

import hashlib
import uuid
from datetime import datetime, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from fastapi import HTTPException, status
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.minio_client import download_object
from app.models.document import DocumentVersion
from app.models.signature import DocumentSignature
from app.services.audit_service import create_audit_record


async def is_version_signed(db: AsyncSession, version_id: uuid.UUID) -> bool:
    """Check if a document version has any signatures."""
    result = await db.execute(
        select(exists().where(DocumentSignature.version_id == version_id))
    )
    return result.scalar_one()


async def sign_version(
    db: AsyncSession,
    version: DocumentVersion,
    signer_id: uuid.UUID,
    certificate_pem: str,
    private_key_pem: str,
    reason: str | None = None,
) -> DocumentSignature:
    """Sign a document version with PKCS7/CMS.

    1. Download content from MinIO
    2. Hash the content (SHA-256)
    3. Sign the hash with the private key
    4. Extract signer CN from the certificate
    5. Store signature record
    """
    # Load and validate the certificate
    try:
        cert = x509.load_pem_x509_certificate(certificate_pem.encode())
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid certificate PEM: {exc}",
        )

    # Load private key
    try:
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode(), password=None
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid private key PEM: {exc}",
        )

    if not isinstance(private_key, rsa.RSAPrivateKey):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only RSA keys are supported for signing",
        )

    # Download content and compute hash
    content = await download_object(version.minio_object_key)
    content_hash = hashlib.sha256(content).hexdigest()

    # Sign the content hash
    signature_bytes = private_key.sign(
        content_hash.encode(),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )

    # Extract Common Name from certificate subject
    cn_attrs = cert.subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)
    signer_cn = cn_attrs[0].value if cn_attrs else "Unknown"

    now = datetime.now(timezone.utc)

    sig = DocumentSignature(
        id=uuid.uuid4(),
        version_id=version.id,
        signer_id=signer_id,
        signature_data=signature_bytes,
        certificate_pem=certificate_pem,
        signer_cn=signer_cn,
        signed_at=now,
        content_hash=content_hash,
        algorithm="sha256WithRSAEncryption",
        reason=reason,
        created_by=str(signer_id),
    )
    db.add(sig)
    await db.flush()

    await create_audit_record(
        db,
        entity_type="document_signature",
        entity_id=str(sig.id),
        action="sign",
        user_id=str(signer_id),
        after_state={
            "version_id": str(version.id),
            "signer_cn": signer_cn,
            "content_hash": content_hash,
            "reason": reason,
        },
    )

    return sig


async def verify_signature(
    db: AsyncSession,
    signature: DocumentSignature,
) -> dict:
    """Verify a signature against the current document content.

    Returns a dict with verification results.
    """
    # Load certificate
    try:
        cert = x509.load_pem_x509_certificate(signature.certificate_pem.encode())
    except Exception:
        return {
            "signature_id": signature.id,
            "is_valid": False,
            "signer_cn": signature.signer_cn,
            "signed_at": signature.signed_at,
            "content_hash_match": False,
            "detail": "Certificate could not be loaded",
        }

    # Get the version to download content
    result = await db.execute(
        select(DocumentVersion).where(DocumentVersion.id == signature.version_id)
    )
    version = result.scalar_one_or_none()
    if version is None:
        return {
            "signature_id": signature.id,
            "is_valid": False,
            "signer_cn": signature.signer_cn,
            "signed_at": signature.signed_at,
            "content_hash_match": False,
            "detail": "Document version not found",
        }

    # Download and hash current content
    content = await download_object(version.minio_object_key)
    current_hash = hashlib.sha256(content).hexdigest()
    content_hash_match = current_hash == signature.content_hash

    # Verify cryptographic signature
    public_key = cert.public_key()
    try:
        public_key.verify(
            signature.signature_data,
            signature.content_hash.encode(),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        crypto_valid = True
    except Exception:
        crypto_valid = False

    is_valid = crypto_valid and content_hash_match

    if is_valid:
        detail = "Signature is valid"
    elif not crypto_valid:
        detail = "Cryptographic signature verification failed"
    else:
        detail = "Content has been modified since signing"

    return {
        "signature_id": signature.id,
        "is_valid": is_valid,
        "signer_cn": signature.signer_cn,
        "signed_at": signature.signed_at,
        "content_hash_match": content_hash_match,
        "detail": detail,
    }


async def list_signatures(
    db: AsyncSession,
    version_id: uuid.UUID,
) -> list[DocumentSignature]:
    """List all signatures for a document version."""
    result = await db.execute(
        select(DocumentSignature)
        .where(DocumentSignature.version_id == version_id)
        .order_by(DocumentSignature.signed_at.desc())
    )
    return list(result.scalars().all())


async def get_signature(
    db: AsyncSession,
    signature_id: uuid.UUID,
) -> DocumentSignature:
    """Get a single signature by ID."""
    result = await db.execute(
        select(DocumentSignature).where(DocumentSignature.id == signature_id)
    )
    sig = result.scalar_one_or_none()
    if sig is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Signature not found",
        )
    return sig
