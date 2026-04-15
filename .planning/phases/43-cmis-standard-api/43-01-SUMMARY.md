---
phase: 43-cmis-standard-api
plan: "01"
subsystem: cmis
tags: [cmis, browser-binding, api, interoperability]
dependency_graph:
  requires: [document_service, folder_service, auth]
  provides: [cmis_browser_binding, cmis_service, cmis_schemas]
  affects: [main.py]
tech_stack:
  added: []
  patterns: [cmis-browser-binding, property-mapping, cmisselector-dispatch]
key_files:
  created:
    - src/app/services/cmis_service.py
    - src/app/schemas/cmis.py
    - src/app/routers/cmis.py
    - src/tests/test_cmis.py
  modified:
    - src/app/main.py
decisions:
  - "CMIS Browser Binding succinct format (not verbose XML) for all responses"
  - "Auto-detect document vs folder by trying document lookup first for getObject"
  - "First cabinet as CMIS root folder; auto-create if none exists"
  - "Celery Task.delay/apply_async mocked at base class level for test isolation"
metrics:
  duration: "28min"
  completed: "2026-04-15"
  tasks_completed: 2
  tasks_total: 2
  test_count: 22
  files_created: 4
  files_modified: 1
requirements:
  - CMIS-01
  - CMIS-02
  - CMIS-04
---

# Phase 43 Plan 01: CMIS Browser Binding Core Summary

CMIS 1.1 Browser Binding translation layer mapping OASIS standard JSON protocol onto existing document_service and folder_service, with bidirectional property mapping and full auth enforcement.

## What Was Built

### CMIS Service Layer (src/app/services/cmis_service.py)
- Bidirectional property mapping between CMIS names (cmis:objectId, cmis:name, etc.) and internal model fields (id, title, filename, etc.)
- Repository info with CMIS 1.1 capabilities (ACL manage, query metadataonly, get descendants/folder tree, multifiling, unfiling)
- Type definitions for cmis:document (13 properties) and cmis:folder (8 properties)
- to_cmis_document/to_cmis_folder conversion with version-aware content length
- from_cmis_properties reverse mapping for create/update operations

### CMIS Schemas (src/app/schemas/cmis.py)
- CmisObjectResponse: succinctProperties dict with optional allowableActions
- CmisObjectListResponse: paginated object list with hasMoreItems/numItems
- CmisRepositoryInfo: full CMIS 1.1 repo info model
- CmisTypeDefinition: type with propertyDefinitions

### CMIS Browser Binding Router (src/app/routers/cmis.py)
- GET /cmis/browser: repository info (CMIS-01)
- GET /cmis/browser/type?typeId=cmis:document|cmis:folder: type definitions
- GET /cmis/browser/root: root folder children
- GET /cmis/browser/root/{id}?cmisselector=object|children|descendants|parents|content
- POST /cmis/browser/root: createDocument (multipart), createFolder
- POST /cmis/browser/root/{id}: update, delete, move, checkOut, checkIn, cancelCheckOut, createDocument, createFolder
- CMIS-style error responses (objectNotFound, invalidArgument, constraint, permissionDenied, notSupported)
- All endpoints require JWT authentication (CMIS-04)

### Tests (src/tests/test_cmis.py)
- 13 unit tests for service layer (property mapping, type definitions, conversion)
- 9 integration tests for HTTP endpoints (repo info, create/get/delete document, children, descendants, move, auth enforcement)
- Celery Task.delay mocked at base class level for Redis-free test execution

## Decisions Made

1. **Succinct format only**: All responses use succinctProperties (flat dict), not verbose CMIS property objects. This is the standard Browser Binding approach.
2. **Document-first resolution**: getObject auto-detects type by trying document lookup first, then folder. Avoids requiring clients to specify type.
3. **First cabinet as root**: CMIS root folder is the first cabinet in the system; auto-created if none exists.
4. **Celery mock strategy**: Patching Task.delay and Task.apply_async at the Celery base Task class level prevents all Redis connection attempts in tests.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Celery Redis connection blocking tests**
- **Found during:** Task 2 integration tests
- **Issue:** Document upload triggers Celery tasks (rendition, extraction, audit chain) that try to connect to Redis, causing 110s timeout per test
- **Fix:** Mocked celery.app.task.Task.delay and Task.apply_async at base class level in test fixture
- **Files modified:** src/tests/test_cmis.py
- **Commit:** 4c0004f

**2. [Rule 1 - Bug] Cabinet creation endpoint URL**
- **Found during:** Task 2 integration tests
- **Issue:** Tests used `/api/v1/folders/cabinets` but actual endpoint is `POST /api/v1/folders/`
- **Fix:** Corrected URL in all test helper methods
- **Files modified:** src/tests/test_cmis.py
- **Commit:** 4c0004f

## Known Stubs

None. All endpoints are fully wired to existing services.

## Self-Check: PASSED
