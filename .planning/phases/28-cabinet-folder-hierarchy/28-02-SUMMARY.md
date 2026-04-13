---
phase: 28-cabinet-folder-hierarchy
plan: "02"
subsystem: api
tags: [folder, cabinet, fastapi, pydantic, rest-api, filing, folder-ids, document-filter]
dependency_graph:
  requires:
    - "28-01: Folder model, FolderService with CTE operations, 18 Wave-0 test stubs"
    - "27-02: DocumentResponse schema, documents router, document_service.list_documents"
  provides:
    - "Folders REST API: 11 endpoints (cabinets, tree, CRUD, filing, unfile, copy)"
    - "FolderResponse, FolderTreeNode, FolderCreate, FolderUpdate, FolderCopyRequest, FileDocumentRequest Pydantic schemas"
    - "DocumentResponse.folder_ids field (list of folder IDs containing the document)"
    - "GET /api/v1/documents/?folder_id={id} filter support"
    - "18 passing integration tests for FOLD-01 through FOLD-04"
  affects:
    - "28-03: UI phase consumes folder endpoints and DocumentResponse.folder_ids"
tech-stack:
  added: []
  patterns:
    - "GET /tree static route declared before /{folder_id} dynamic route to avoid FastAPI path conflict"
    - "_build_response helper centralizes ORM-to-Pydantic conversion with path/document_count args"
    - "_doc_response helper accepts optional folder_ids kwarg; populated via get_document_folder_ids call"
    - "folder_service imported at module level in documents.py for per-document folder_ids lookup"
    - "list_documents folder_id filter uses Document.id.in_(select(document_folders.c.document_id).where(...))"
key-files:
  created:
    - src/app/schemas/folder.py
    - src/app/routers/folders.py
  modified:
    - src/app/main.py
    - src/app/schemas/document.py
    - src/app/routers/documents.py
    - src/app/services/document_service.py
    - tests/test_folders.py
key-decisions:
  - "GET /tree placed before /{folder_id} in router to avoid FastAPI treating 'tree' as a UUID path param"
  - "list_documents folder_id filter implemented as subquery (Document.id.in_) rather than explicit JOIN to preserve existing ACL filter logic"
  - "_doc_response folder_ids populated only when explicitly passed (None = skip update, [] = no folders)"
  - "test helper _create_cabinet calls POST /api/v1/folders/ not /cabinets (correct route)"
  - "test_auto_activities.py pre-existing failure (SQLite FK cycle, unrelated to folder changes) documented as out-of-scope"
patterns-established:
  - "Router: static path segments (/tree) must be declared before dynamic (:folder_id) in same prefix group"
  - "Service: per-document folder_ids fetch is called in each endpoint individually (not in service layer) to keep service pure"
requirements-completed: [FOLD-01, FOLD-02, FOLD-03, FOLD-04]
duration: ~20min
completed: 2026-04-13
---

# Phase 28 Plan 02: Folder REST API and Document Integration Summary

**11-endpoint FastAPI folders router with FolderTreeNode schemas, folder_ids in DocumentResponse, folder_id query filter on document list, and all 18 integration tests passing.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-04-13T07:14:00Z
- **Completed:** 2026-04-13T07:34:07Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Created `src/app/schemas/folder.py` with 6 Pydantic schemas: FolderCreate, FolderUpdate, FolderCopyRequest, FileDocumentRequest, FolderResponse, FolderTreeNode
- Created `src/app/routers/folders.py` with 11 endpoints covering the full cabinet/folder CRUD lifecycle: list cabinets, create cabinet (admin), tree, get folder with path, create subfolder, update (rename/move), delete (cascade soft-delete), copy, get documents, file document, unfile document
- Registered folders router in main.py under `/api/v1/folders` prefix
- Added `folder_ids: list[str] = []` to `DocumentResponse` schema
- Updated documents router to call `folder_service.get_document_folder_ids` in upload, get, update, checkout, force-unlock endpoints
- Added `folder_id` query param to `GET /api/v1/documents/` endpoint with subquery filter
- Implemented all 18 Wave-0 test stubs in `tests/test_folders.py` — 18/18 passing

## Task Commits

1. **Task 1: Pydantic schemas, folders router (11 endpoints), register in main.py** - `aed62eb` (feat)
2. **Task 2: folder_ids in DocumentResponse, folder_id filter, 18 tests passing** - `defdcfd` (feat)

## Files Created/Modified
- `src/app/schemas/folder.py` — 6 Pydantic schemas for folder CRUD, tree, filing
- `src/app/routers/folders.py` — 11-endpoint FastAPI router with `_build_response` helper
- `src/app/main.py` — Added `folders` import and `include_router` call
- `src/app/schemas/document.py` — Added `folder_ids: list[str] = []` to DocumentResponse
- `src/app/routers/documents.py` — Updated `_doc_response`, added `folder_id` param, calls to `get_document_folder_ids`
- `src/app/services/document_service.py` — Added `folder_id` param and subquery filter to `list_documents`
- `tests/test_folders.py` — Replaced 18 Wave-0 stubs with real assertions; updated `_create_cabinet` helper to use correct `/api/v1/folders/` endpoint

## Decisions Made
- GET /tree placed before /{folder_id} in the router to prevent FastAPI treating "tree" as a UUID path param (would cause 422 validation error)
- folder_id filter in list_documents uses `Document.id.in_(subquery)` rather than explicit JOIN to avoid conflicting with the existing ACL filter logic (which is already a complex OR join)
- `_doc_response` in documents.py accepts `folder_ids=None` (no-op, keeps backward compatibility) vs `folder_ids=[]` (explicit empty list)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] _create_cabinet helper used wrong endpoint path**
- **Found during:** Task 2 (implementing test stubs)
- **Issue:** Wave-0 test stubs called `/api/v1/folders/cabinets` but the router registers `POST /` not `POST /cabinets`
- **Fix:** Updated `_create_cabinet` helper to use `/api/v1/folders/` (correct endpoint per plan spec)
- **Files modified:** tests/test_folders.py
- **Verification:** 18/18 tests pass
- **Committed in:** defdcfd (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug in test helper)
**Impact on plan:** Essential fix — all 18 tests depended on correct endpoint URL.

## Issues Encountered
- `test_auto_activities.py` has a pre-existing failure (SQLite FK cycle between `activity_instances` and `workflow_instances` prevents table creation in correct order). This failure exists before this plan's changes and is out of scope. Documented in deferred-items.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 11 folder endpoints available at `/api/v1/folders/*`
- DocumentResponse includes `folder_ids` field (populated on every document GET/list/upload/update)
- `GET /api/v1/documents/?folder_id={id}` filter works
- Plan 28-03 (Folder UI) can consume these endpoints to build the cabinet/folder browser

---
*Phase: 28-cabinet-folder-hierarchy*
*Completed: 2026-04-13*
