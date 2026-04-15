---
phase: 41-import-export
plan: 01
subsystem: api
tags: [fastapi, celery, zipfile, minio, pydantic, import, export]

# Dependency graph
requires:
  - phase: 40-bulk-operations
    provides: BulkJob model for job tracking, bulk service patterns
provides:
  - Document export to ZIP with manifest.json, content files, folder hierarchy, ACLs, relationships
  - Document import from ZIP with skip/overwrite/rename conflict resolution
  - Async Celery-backed export and import job execution
  - REST API endpoints for export, import, job listing, and ZIP download
affects: [41-02-PLAN]

# Tech tracking
tech-stack:
  added: []
  patterns: [ZIP-based import/export with JSON manifest, multipart file upload for import, streaming download for export]

key-files:
  created:
    - src/app/schemas/import_export.py
    - src/app/services/import_export_service.py
    - src/app/tasks/import_export.py
    - src/app/routers/import_export.py
    - tests/test_import_export.py
  modified:
    - src/app/celery_app.py
    - src/app/main.py

key-decisions:
  - "Reuse BulkJob model with job_type='export'|'import' rather than creating new tables"
  - "Use module-level minio_client import in router to respect test monkeypatching"

patterns-established:
  - "ZIP manifest pattern: manifest.json at root with documents, folders, folder_filings, acls, relationships arrays"
  - "Import conflict resolution via conflict_strategy parameter (skip/overwrite/rename)"

requirements-completed: [IOEX-01, IOEX-02, IOEX-03, IOEX-04]

# Metrics
duration: 3min
completed: 2026-04-15
---

# Phase 41 Plan 01: Import/Export Backend Summary

**ZIP-based document import/export with manifest.json, folder hierarchy preservation, ACL/relationship transfer, and skip/overwrite/rename conflict resolution via Celery async jobs**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-15T06:35:03Z
- **Completed:** 2026-04-15T06:38:00Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Export creates ZIP packages with content files, metadata manifest, folder hierarchy, ACLs, and document relationships
- Import reads ZIP packages, recreates folders and documents with configurable conflict resolution (skip/overwrite/rename)
- Both operations run as background Celery jobs tracked via BulkJob model with progress/status
- REST API with multipart upload for import, streaming download for completed exports
- 8 API-level tests covering all endpoints and conflict strategies

## Task Commits

Each task was committed atomically:

1. **Task 1: Schemas + service layer + Celery tasks for export/import** - `88208e0` (feat)
2. **Task 2: API router + main.py wiring + download endpoint** - `0a13213` (feat)

## Files Created/Modified
- `src/app/schemas/import_export.py` - ExportRequest, ImportRequest, ImportExportJobResponse Pydantic schemas
- `src/app/services/import_export_service.py` - create_export_job, create_import_job, get_import_export_jobs service functions
- `src/app/tasks/import_export.py` - execute_export_job and execute_import_job Celery tasks with full async implementation
- `src/app/routers/import_export.py` - REST endpoints: POST /export, POST /import, GET /jobs, GET /jobs/{id}, GET /download/{id}
- `src/app/celery_app.py` - Added app.tasks.import_export to Celery include list
- `src/app/main.py` - Registered import_export router
- `tests/test_import_export.py` - 8 tests covering export, import, conflict strategies, job listing, download

## Decisions Made
- Reused BulkJob model with job_type="export"|"import" rather than creating separate models
- Used module-level minio_client import in router (not direct function import) to respect test monkeypatching

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed MinIO download_object reference binding in router**
- **Found during:** Task 2 (download endpoint)
- **Issue:** Direct `from app.core.minio_client import download_object` binds at import time, bypassing test monkeypatch
- **Fix:** Changed to `from app.core import minio_client` and call `minio_client.download_object()` to respect runtime patching
- **Files modified:** src/app/routers/import_export.py
- **Verification:** test_download_export_zip passes
- **Committed in:** 0a13213 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Essential for test correctness. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all data flows are fully wired.

## Next Phase Readiness
- Backend import/export API complete, ready for frontend UI in Plan 02
- Export ZIP format established with manifest.json spec for interoperability

---
*Phase: 41-import-export*
*Completed: 2026-04-15*
