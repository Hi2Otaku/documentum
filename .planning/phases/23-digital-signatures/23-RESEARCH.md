# Phase 23: Digital Signatures - Research

**Date:** 2026-04-06
**Level:** 1 (Quick Verification)
**Scope:** PKCS7/CMS signing with `cryptography` library

## Library Confirmation

### `cryptography` library
- **Available via:** `python-jose[cryptography]` dependency already in pyproject.toml
  - The `cryptography` package is a transitive dependency, already installed
- **Modules needed:**
  - `cryptography.x509` -- certificate creation, loading, parsing
  - `cryptography.hazmat.primitives.serialization.pkcs7` -- PKCS7/CMS signing
  - `cryptography.hazmat.primitives.hashes` -- SHA-256 digest
  - `cryptography.hazmat.primitives.asymmetric.rsa` -- RSA key generation (test certs)
  - `cryptography.hazmat.primitives.serialization` -- PEM encoding/decoding

### PKCS7 Signing API (cryptography >= 41.0)
```python
from cryptography.hazmat.primitives.serialization import pkcs7

# Sign data
signature_bytes = pkcs7.serialize_certificates(...)
# or more precisely:
options = [pkcs7.PKCS7Options.DetachedSignature]
signature = (
    pkcs7.PKCS7SignatureBuilder()
    .set_data(document_content)
    .add_signer(certificate, private_key, hashes.SHA256())
    .sign(serialization.Encoding.DER, options)
)
```

### Certificate Generation (for development/testing)
```python
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa

key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
subject = issuer = x509.Name([
    x509.NameAttribute(NameOID.COMMON_NAME, username),
])
cert = (
    x509.CertificateBuilder()
    .subject_name(subject)
    .issuer_name(issuer)
    .public_key(key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(datetime.utcnow())
    .not_valid_after(datetime.utcnow() + timedelta(days=365))
    .sign(key, hashes.SHA256())
)
```

### Verification
```python
# Load the original data and detached signature
# Verify signature against certificate
pkcs7.load_der_pkcs7_certificates(signature_bytes)  # extract certs from signature
# For full verification: check signature mathematically + cert validity
```

## Architecture Decisions

### Signature Storage
- **Decision:** Store signatures as binary blobs in MinIO (alongside document content)
- **Object key pattern:** `{doc_id}/{version_id}/signatures/{signature_id}.der`
- **Metadata in PostgreSQL:** `document_signatures` table with signer info, timestamp, MinIO key

### Certificate Strategy
- **Decision:** Self-signed certificates for development (per REQUIREMENTS.md "Full PKI/CA infrastructure" is out of scope)
- **Flow:** User provides PEM-encoded private key + certificate when signing. System stores the certificate (public part) for verification. Private key is never stored.
- **Simplified approach for MVP:** System generates a self-signed cert per user on first sign request (private key generated transiently, cert stored in DB). This avoids requiring users to manage certificates externally.
- **Chosen approach:** Users have a system-generated signing certificate. On first sign, the system generates a key pair, creates a self-signed cert, stores cert PEM + encrypted private key in the user_certificates table. The private key is encrypted with the user's password (or a derived key). For this phase, we'll store the PEM-encoded private key encrypted with a server-side key (from settings) since we don't have access to user passwords at signing time.

### Immutability Enforcement
- **Decision:** Add guard checks in `document_service.py` for:
  - `checkin_document()` -- reject if latest version has signatures
  - `update_document_metadata()` -- reject if any version is signed (whole doc becomes immutable)
  - Also add a `has_signatures` boolean on `DocumentVersion` model for fast checking
- **Scope:** Immutability applies to the signed VERSION, not the whole document. New versions can still be created via checkout/checkin on the document, but signed versions cannot be replaced.

## No External Dependencies Needed
- `cryptography` is already available as a transitive dependency
- No new packages need to be added to pyproject.toml
