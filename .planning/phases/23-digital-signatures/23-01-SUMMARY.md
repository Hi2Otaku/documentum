---
phase: "23"
plan: "01"
subsystem: digital-signatures
tags: [pkcs7, cms, cryptography, document-signing, immutability]
dependency_graph:
  requires: [document-versions, minio-storage]
  provides: [digital-signature-api, signed-version-immutability]
  affects: [document-service, document-versions]
tech_stack:
  added: [cryptography]
  patterns: [pkcs7-detached-signatures, immutability-guards]
key_files:
  created:
    - src/app/models/signature.py
    - src/app/services/signature_service.py
    - src/app/schemas/signature.py
    - src/app/routers/signatures.py
    - alembic/versions/phase23_001_digital_signatures.py
  modified:
    - src/app/models/document.py
    - src/app/models/__init__.py
    - src/app/main.py
    - src/app/schemas/document.py
    - src/app/services/document_service.py
    - pyproject.toml
decisions:
  - Used cryptography library for PKCS7/CMS signing (standard Python crypto library)
  - Detached signatures stored as DER-encoded binary in database
  - Certificate PEM stored alongside signature for self-contained verification
  - Immutability enforced at checkout, check-in, and metadata update levels
metrics:
  duration: 3m
  completed: "2026-04-06"
  tasks: 5
  files: 11
---

# Phase 23 Plan 01: Digital Signatures Summary

PKCS7/CMS digital signatures on document versions with cryptography library, verification API, and signed-version immutability enforcement.

## What Was Built

### DigitalSignature Model and Migration (Task 1)
- New `DigitalSignature` SQLAlchemy model storing PKCS7 signature bytes, certificate PEM, signer reference, digest algorithm, and validity status
- Added `is_signed` boolean column to `DocumentVersion` model
- Added `signatures` relationship on `DocumentVersion` for eager loading
- Alembic migration `phase23_001` creates the table and index

### Signature Service (Task 2)
- `sign_document_version()` downloads version content from MinIO, creates PKCS7 detached signature using SHA-256, stores signature record, marks version as signed
- `verify_signature()` re-loads PKCS7 structure, validates certificate dates, updates validity status
- `list_signatures()` and `get_signature()` for querying

### API Endpoints (Task 3)
- `POST /api/v1/documents/{id}/versions/{id}/sign` - sign with provided private key and certificate PEM
- `GET /api/v1/documents/{id}/versions/{id}/signatures` - list all signatures
- `POST /api/v1/documents/signatures/{id}/verify` - verify a specific signature

### Immutability Enforcement (Task 4)
- Check-in blocked with HTTP 409 if latest version is signed
- Checkout blocked with HTTP 409 if current version is signed
- Metadata update blocked with HTTP 409 if current version is signed
- Clear error messages explain the immutability constraint

### Schema Updates (Task 5)
- `DocumentVersionResponse` now includes `is_signed` boolean field

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 4ba85c5 | DigitalSignature model, is_signed column, migration |
| 2 | 8df32c6 | Signature service with PKCS7/CMS sign and verify |
| 3 | b0323b8 | Signature schemas and API endpoints |
| 4 | 76303e2 | Immutability enforcement on signed versions |
| 5 | b61139e | is_signed field in DocumentVersionResponse |

## Deviations from Plan

None - plan executed exactly as written.

## Decisions Made

1. **cryptography library for PKCS7**: Standard Python cryptographic library with PKCS7 signing support via `pkcs7.PKCS7SignatureBuilder`. Detached signatures keep the signature separate from content.
2. **DER encoding for signatures**: Binary DER format is more compact than PEM for storage in the database `LargeBinary` column.
3. **Certificate stored with signature**: Each signature stores its full certificate PEM, making verification self-contained without requiring a separate certificate store.
4. **Three-level immutability**: Guards placed at checkout, check-in, and metadata update -- covering all mutation paths for document versions.

## Known Stubs

None - all data paths are wired to real PKCS7 operations.

## Self-Check: PASSED
