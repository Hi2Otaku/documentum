---
phase: 27-document-type-system
plan: 02
subsystem: document-management
tags: [fastapi, sqlalchemy, pydantic, document-types, jsonschema, metadata-validation]

requires:
  - phase: 27-01
    provides: DocumentType model, document_type_service CRUD+validation, Pydantic schemas, test stubs

provides:
  - document_types router with 5 CRUD endpoints (POST/GET list/GET single/PUT/DELETE)
  - Admin-gated write operations, any-user read access
  - document_type_id Form field on document upload endpoint
  - document_type_id JSON field on document update endpoint
  - validate_metadata called before save on both upload and update
  - document_type_name populated in all DocumentResponse objects
  - selectinload for parent_type and document_type relationships to avoid async lazy-load errors
  - All 12 TYPE-01 through TYPE-04 tests passing

affects:
  - 27-03 (frontend reads /api/v1/document-types/ for type management UI)
  - 27-04 (integration tests exercise full upload+type+validation pipeline)

tech-stack:
  added: []
  patterns:
    - "selectinload(Model.relationship) added to all queries returning objects whose relationships are accessed in response helpers"
    - "db.refresh(obj, ['relationship']) after flush to load relationships on newly-created objects"
    - "_doc_response helper uses model_copy(update=...) to inject computed document_type_name into frozen Pydantic model"
    - "_build_response helper computes parent_type_name and field_count from ORM object"

key-files:
  created:
    - src/app/routers/document_types.py
  modified:
    - src/app/main.py
    - src/app/routers/documents.py
    - src/app/services/document_service.py
    - src/app/services/document_type_service.py

key-decisions:
  - "selectinload in service queries rather than relying on model-level lazy='selectin' to prevent MissingGreenlet errors in async context"
  - "db.refresh with attribute list after flush to load relationships on newly created objects without re-querying"
  - "validate_metadata called in router (not service) so upload_document service stays pure"

patterns-established:
  - "Pattern 3: Use explicit selectinload() in async queries for any relationship accessed in response serialization"
  - "Pattern 4: db.refresh(obj, ['rel']) after flush to initialize newly-created object relationships"

requirements-completed: [TYPE-01, TYPE-02, TYPE-03, TYPE-04]

duration: 5min
completed: 2026-04-13
---

# Phase 27 Plan 02: Document Type API Wiring Summary

**document_types CRUD router (5 endpoints, admin-gated writes) wired into FastAPI, document upload/update extended with document_type_id and validate_metadata, all 12 integration tests green.**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-04-13T03:57:42Z
- **Completed:** 2026-04-13T04:02:31Z
- **Tasks:** 2 of 2
- **Files modified:** 5

## Accomplishments

- Created `document_types.py` router: POST (201, admin), GET list, GET single, PUT (admin), DELETE (admin) — all returning `EnvelopeResponse[DocumentTypeResponse]` with computed `parent_type_name`, `field_count`, `document_count`
- Extended `upload_document` with `document_type_id: str | None = Form(None)` parameter; calls `validate_metadata` before DB write
- Extended `update_document` to pass `document_type_id` to service and validate before save
- Fixed async lazy-load MissingGreenlet errors by adding explicit `selectinload` in service queries and `db.refresh` after flush

## Task Commits

1. **Task 1: Create document_types router with admin-gated CRUD endpoints** - `1d75b8e` (feat)
2. **Task 2: Integrate document_type_id into upload/update and wire validation** - `bc68242` (feat)

## Files Created/Modified

- `src/app/routers/document_types.py` — New: 5 CRUD endpoints with _build_response helper
- `src/app/main.py` — Added document_types import and include_router call
- `src/app/routers/documents.py` — Added document_type_id Form param, validate_metadata calls, _doc_response helper
- `src/app/services/document_service.py` — Added document_type_id param + selectinload + db.refresh
- `src/app/services/document_type_service.py` — Added selectinload on parent_type in _fetch_type_or_404 and list_document_types

## Decisions Made

- Used explicit `selectinload()` in service queries rather than relying on model-level `lazy="selectin"` to prevent `MissingGreenlet` errors in aiosqlite test context. The model-level lazy loader doesn't guarantee loading within async greenlet boundaries.
- Placed `validate_metadata` call in the router (before calling the service) to keep `document_service.upload_document` clean and reusable without validation coupling.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed MissingGreenlet errors for lazy-loaded relationships**
- **Found during:** Task 2 (integration test run)
- **Issue:** `doc_type.parent_type` and `doc.document_type` accessed in response helpers triggered SQLAlchemy lazy load outside greenlet context, causing `MissingGreenlet` exceptions in async tests
- **Fix:** Added `selectinload(DocumentType.parent_type)` to `_fetch_type_or_404` and `list_document_types` queries; added `selectinload(Document.document_type)` to `get_document` and `list_documents`; added `db.refresh(document, ["document_type"])` after flush in upload/update/checkout/force_unlock service functions
- **Files modified:** src/app/services/document_type_service.py, src/app/services/document_service.py
- **Verification:** 12 document_types tests pass; 27 existing document tests pass
- **Committed in:** bc68242 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Necessary correctness fix. The model-level `lazy="selectin"` is insufficient in async test context; explicit selectinload is required.

## Issues Encountered

None beyond the MissingGreenlet fix documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Full backend API for document types is ready: CRUD + schema validation + document assignment
- Plan 03 (frontend document type management UI) can now consume `/api/v1/document-types/` endpoints
- Plan 04 (integration validation) can run end-to-end tests against the complete API

## Self-Check: PASSED

Files verified:
- FOUND: src/app/routers/document_types.py
- FOUND: src/app/main.py (document_types import verified)
- FOUND: src/app/routers/documents.py (document_type_id Form param + validate_metadata)
- FOUND: src/app/services/document_service.py (document_type_id param + selectinload)
- FOUND: src/app/services/document_type_service.py (selectinload added)

Commits verified:
- FOUND: 1d75b8e
- FOUND: bc68242

---
*Phase: 27-document-type-system*
*Completed: 2026-04-13*
