---
phase: 23-digital-signatures
verified: 2026-04-06T20:44:21Z
status: gaps_found
score: 2/5 must-haves verified
re_verification: false
gaps:
  - truth: "User can POST to sign a document version and receive a signature response"
    status: failed
    reason: "Router defines POST to /signatures suffix but tests and plan 01 summary describe /sign suffix. Tests assert response fields document_version_id and digest_algorithm which do not match schema fields version_id and algorithm. Tests fail at collection due to missing RenditionStatus/RenditionType enums blocking conftest fixture."
    artifacts:
      - path: "src/app/routers/signatures.py"
        issue: "Sign endpoint path is POST /documents/{id}/versions/{id}/signatures but tests call /documents/{id}/versions/{id}/sign — routes do not match"
      - path: "src/app/schemas/signature.py"
        issue: "Response has version_id and algorithm fields; test_sign_document_version asserts document_version_id and digest_algorithm — field name mismatch"
      - path: "src/app/models/enums.py"
        issue: "RenditionStatus and RenditionType enums are absent; rendition_service import fails which blocks conftest fixture; all tests fail at collection"
    missing:
      - "Either rename router endpoint from /signatures to /sign OR update test helpers to POST to /signatures"
      - "Either add version_id alias as document_version_id and algorithm alias as digest_algorithm to SignatureResponse OR update test assertions"
      - "Add RenditionStatus and RenditionType enums to src/app/models/enums.py (claimed added in Plan 02 summary but not present)"

  - truth: "User can GET to verify a specific signature and see validity status"
    status: failed
    reason: "Tests POST to /api/v1/documents/signatures/{sig_id}/verify but router defines GET /documents/{document_id}/versions/{version_id}/signatures/{signature_id}/verify — both method and URL structure differ. Tests cannot pass until route mismatch is resolved."
    artifacts:
      - path: "src/app/routers/signatures.py"
        issue: "Verify endpoint is GET with full version path; tests call POST with short /documents/signatures/{id}/verify path"
    missing:
      - "Either add a shortcut POST /documents/signatures/{id}/verify route OR update tests to use GET with version_id in path"

  - truth: "System rejects checkin on a document whose latest version is signed with 409 error"
    status: failed
    reason: "test_checkin_blocked_on_signed_version checks that checkout (not checkin) is blocked and expects 409. checkout_document() in document_service.py has no _check_version_not_signed call — checkout is not guarded. Additionally migration table name is digital_signatures but model __tablename__ is document_signatures causing FK constraint mismatch if migration is applied."
    artifacts:
      - path: "src/app/services/document_service.py"
        issue: "checkout_document() does not call _check_version_not_signed; signed version does not block checkout"
      - path: "alembic/versions/phase23_001_digital_signatures.py"
        issue: "Migration creates table digital_signatures and column document_version_id but model uses __tablename__=document_signatures and column version_id — migration and model are out of sync"
    missing:
      - "Add _check_version_not_signed(db, document_id) call inside checkout_document() before acquiring the lock"
      - "Fix migration table name from digital_signatures to document_signatures (or vice versa, make consistent)"
      - "Fix migration column name from document_version_id to version_id, and digest_algorithm to algorithm; remove is_valid column that does not exist in model"

  - truth: "System rejects metadata update on a document with any signed version with 409 error"
    status: partial
    reason: "update_document_metadata() does call _check_version_not_signed — the guard is wired. However all tests fail at collection due to the RenditionStatus/RenditionType import error so the test covering this truth (test_metadata_update_blocked_on_signed_version) cannot run. The logic itself exists but is unverified."
    artifacts:
      - path: "src/app/models/enums.py"
        issue: "Missing RenditionStatus/RenditionType enums prevent test collection"
    missing:
      - "Add RenditionStatus and RenditionType enums to enums.py to unblock test collection"

  - truth: "User can GET all signatures for a document version with signer, timestamp, validity"
    status: partial
    reason: "GET /documents/{id}/versions/{id}/signatures route exists and calls list_signatures from service which performs a real DB query. However tests cannot run due to collection error. The test asserts signer_id but schema returns signer_cn (common name) not signer_id — this is present in SignatureResponse but may cause assertion failures once tests run."
    artifacts:
      - path: "src/app/models/enums.py"
        issue: "Missing RenditionStatus/RenditionType blocks all test collection"
    missing:
      - "Add RenditionStatus and RenditionType enums to enums.py"
      - "Confirm test_list_signatures assertion checks signer_id which is present in SignatureResponse schema"
---

# Phase 23: Digital Signatures Verification Report

**Phase Goal:** Users can cryptographically sign document versions and verify signatures, with the system enforcing immutability on signed content
**Verified:** 2026-04-06T20:44:21Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can POST to sign a document version and receive a signature response | FAILED | Route path mismatch (/sign vs /signatures), schema field name mismatch (document_version_id vs version_id, digest_algorithm vs algorithm), all tests fail at collection |
| 2 | User can GET to verify a specific signature and see validity status | FAILED | Verify endpoint method mismatch (POST in tests vs GET in router) and URL structure mismatch |
| 3 | User can GET all signatures for a document version with signer, timestamp, validity | PARTIAL | Route and service logic exist and are wired; tests blocked from running by enums import error |
| 4 | System rejects checkin on a document whose latest version is signed with 409 error | FAILED | checkout_document() has no immutability guard; migration/model table name and column name are out of sync |
| 5 | System rejects metadata update on a document with any signed version with 409 error | PARTIAL | Guard is in update_document_metadata() but tests cannot run due to missing enums |

**Score:** 0/5 truths fully verified (2/5 partially wired, 3/5 fully failed)

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/app/models/signature.py` | DocumentSignature SQLAlchemy model | VERIFIED | Exists, substantive, registered in __init__.py. Uses __tablename__="document_signatures" |
| `src/app/services/signature_service.py` | sign_version, verify_signature, list_signatures, is_version_signed | VERIFIED | All four functions present, use real cryptography library and DB queries. No stubs. |
| `src/app/schemas/signature.py` | SignDocumentRequest, SignatureResponse, SignatureVerifyResponse | VERIFIED | All three schemas present with proper fields |
| `src/app/routers/signatures.py` | POST sign, GET list, GET verify endpoints | PARTIAL | Router exists with 3 routes but sign endpoint path (/signatures) does not match tests (/sign); verify endpoint method (GET) does not match test (POST) |
| `tests/test_signatures.py` | Integration tests for all four SIG requirements | STUB | File exists with 12 test functions but ALL fail at collection due to missing RenditionStatus/RenditionType enums; test assertions use wrong field names; no TestDigitalSignatures class as required by plan |
| `alembic/versions/phase23_001_digital_signatures.py` | Migration creating document_signatures table | BROKEN | Migration creates table named `digital_signatures` but model uses `document_signatures`; migration columns (document_version_id, digest_algorithm, is_valid) do not match model columns (version_id, algorithm); is_signed column added to document_versions but never declared in DocumentVersion model |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/app/routers/signatures.py` | `src/app/services/signature_service.py` | import and call sign/verify/list functions | WIRED | Router imports `signature_service` and calls `sign_version`, `list_signatures`, `verify_signature`, `get_signature` |
| `src/app/services/document_service.py` | `src/app/services/signature_service.py` | import is_version_signed for immutability guard | PARTIAL | `_check_version_not_signed` imports `is_version_signed` and is called in `checkin_document` and `update_document_metadata` — but NOT in `checkout_document` |
| `src/app/main.py` | `src/app/routers/signatures.py` | include_router registration | WIRED | `signatures` imported in router list and `application.include_router(signatures.router, ...)` present at line 91 |

---

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `signature_service.sign_version` | `content` | `download_object(version.minio_object_key)` | Yes — downloads actual file bytes from MinIO for hashing | FLOWING |
| `signature_service.verify_signature` | `content` | `download_object(version.minio_object_key)` | Yes — re-downloads content for hash comparison | FLOWING |
| `signature_service.list_signatures` | query result | `select(DocumentSignature).where(version_id == ...)` | Yes — real DB query ordered by signed_at | FLOWING |
| `signature_service.is_version_signed` | bool result | `select(exists().where(version_id == ...))` | Yes — real DB existence check | FLOWING |

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Signatures router importable | `python -c "from app.routers.signatures import router"` | ImportError (settings validation fails without env vars — not a code defect) | SKIP |
| Tests pass | `python -m pytest tests/test_signatures.py -x -v` | ERROR: ImportError: cannot import name 'RenditionStatus' from 'app.models.enums' — ALL 12 tests fail at collection | FAIL |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| SIG-01 | 23-01, 23-02 | User can digitally sign a specific document version (PKCS7/CMS signature) | BLOCKED | Sign endpoint exists but path mismatch and test collection failure prevent verification |
| SIG-02 | 23-01, 23-02 | User can verify the signature on a signed document version | BLOCKED | Verify endpoint exists but method/path mismatch and test collection failure prevent verification |
| SIG-03 | 23-01, 23-02 | User can view all signatures on a document with signer, timestamp, and validity | BLOCKED | List endpoint exists and logic is wired but test collection failure prevents automated verification |
| SIG-04 | 23-01, 23-02 | System enforces immutability on signed document versions (no re-upload or modification) | BLOCKED | Metadata and checkin guards exist; checkout guard is missing; migration/model mismatch may prevent DB from working at all; test collection failure blocks automated verification |

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `alembic/versions/phase23_001_digital_signatures.py` | 30 | Table name `digital_signatures` does not match model `__tablename__ = "document_signatures"` | BLOCKER | If migration is applied the table will not be found by SQLAlchemy ORM queries; all sign/verify operations fail at runtime |
| `alembic/versions/phase23_001_digital_signatures.py` | 34, 36, 38 | Column names `document_version_id`, `digest_algorithm`, `is_valid` do not match model columns `version_id`, `algorithm` (no is_valid in model) | BLOCKER | FK constraint references wrong column name; ORM column mapping fails |
| `src/app/models/document.py` | (missing) | `is_signed` column added by migration but never declared in DocumentVersion SQLAlchemy model | BLOCKER | If migration runs, DB has is_signed column but ORM never reads/writes it — document_service logic that marks versions as signed cannot work |
| `src/app/models/enums.py` | (absent) | RenditionStatus and RenditionType enums missing — claimed fixed in Plan 02 summary but fix never applied to main repo | BLOCKER | rendition_service import fails; conftest autouse fixture errors; ALL 12 signature tests fail at collection |
| `tests/test_signatures.py` | 100, 142, 174 | POST to `/documents/{id}/versions/{id}/sign` but router serves POST to `/documents/{id}/versions/{id}/signatures` | BLOCKER | All sign tests would return 404/405 even if collection error were fixed |
| `tests/test_signatures.py` | 201, 218 | POST to `/documents/signatures/{id}/verify` but router serves GET to `/documents/{id}/versions/{id}/signatures/{id}/verify` | BLOCKER | All verify tests would return 404/405 even if collection error were fixed |
| `tests/test_signatures.py` | 126–127 | Asserts `data["document_version_id"]` and `data["digest_algorithm"]` but schema uses `version_id` and `algorithm` | BLOCKER | Assertions fail with KeyError even if endpoint were reached |
| `src/app/services/document_service.py` | 195–222 | `checkout_document` has no `_check_version_not_signed` guard despite plan requiring it and test expecting 409 | BLOCKER | test_checkin_blocked_on_signed_version would fail; checkout of signed version is not immutability-protected |

---

## Human Verification Required

### 1. Migration State

**Test:** Check whether the migration `phase23_001` has already been applied against the running PostgreSQL database. If it has, determine whether the table name / column name mismatches have caused silent data loss or constraint violations.
**Expected:** Either migration has not been applied (safe to fix), or was applied with the wrong schema (data exists under wrong table name and FK constraints are broken).
**Why human:** Requires access to a running PostgreSQL instance with `alembic current` or `psql \dt`.

### 2. Endpoint Path Choice

**Test:** Decide whether the canonical sign endpoint URL should be `.../versions/{id}/sign` or `.../versions/{id}/signatures` (POST). The router uses `/signatures` (POST) while tests and the Plan 01 summary describe `/sign`.
**Expected:** A consistent choice that matches router, tests, and documentation.
**Why human:** This is a design decision — either the router or the tests are wrong and an authoritative choice needs to be made.

---

## Gaps Summary

Phase 23 contains the right structural pieces — the cryptographic signing logic in `signature_service.py` is substantive (real RSA/SHA-256 operations, real MinIO downloads, real DB writes) and the router, schemas, model, and guards are all present. However the phase fails goal verification on five distinct integration problems:

1. **Migration is broken:** The Alembic migration creates a table named `digital_signatures` with columns `document_version_id` and `digest_algorithm`, but the SQLAlchemy model uses `document_signatures`, `version_id`, and `algorithm`. If the migration is applied the database schema and ORM mapping are out of sync — all runtime queries fail.

2. **Tests cannot be collected:** The Plan 02 summary claims `RenditionStatus` and `RenditionType` enums were added to `enums.py` as a blocker fix, but those enums are absent from the file in the current main branch. This causes an `ImportError` that blocks every test in `test_signatures.py` at the pytest collection phase.

3. **Test endpoints do not match router routes:** The sign tests POST to `.../versions/{id}/sign` but the router registers `.../versions/{id}/signatures`. The verify tests POST to `/documents/signatures/{id}/verify` but the router registers a GET at `.../versions/{id}/signatures/{id}/verify`.

4. **Test field assertions do not match schema:** `test_sign_document_version` checks `data["document_version_id"]` and `data["digest_algorithm"]` but `SignatureResponse` exposes `version_id` and `algorithm`.

5. **Checkout immutability not enforced:** `checkout_document()` lacks the `_check_version_not_signed` call. The test `test_checkin_blocked_on_signed_version` tests checkout (not checkin) and expects 409, but checkout succeeds without restriction.

These gaps collectively mean that no SIG requirement can be considered fully satisfied in the current codebase state.

---

_Verified: 2026-04-06T20:44:21Z_
_Verifier: Claude (gsd-verifier)_
