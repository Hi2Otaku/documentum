---
phase: 29-folder-acl-inheritance
plan: 02
subsystem: api-layer
tags: [folder-acl, api, rest-endpoints, access-source, document-response]
dependency_graph:
  requires: [29-01]
  provides: [folder-acl-api-endpoints, access-source-field]
  affects: [documents-router, folders-router, acl-service, document-schema]
tech_stack:
  added: []
  patterns: [admin-permission-gating, model-copy-for-response-extension, shared-cte-helper]
key_files:
  created: []
  modified:
    - src/app/routers/folders.py
    - src/app/schemas/document.py
    - src/app/services/acl_service.py
    - src/app/routers/documents.py
    - tests/test_folder_acl.py
decisions:
  - "Use model_copy(update=...) pattern to extend DocumentResponse with access_source without breaking existing callers"
  - "Test permission_level must use lowercase enum values ('read', not 'READ') matching PermissionLevel.value"
  - "test_access_source_field uses admin token (document uploader) since owner ACL is created on upload; regular user correctly gets 403"
metrics:
  duration: ~10min
  completed_date: "2026-04-13"
  tasks_completed: 2
  files_modified: 5
---

# Phase 29 Plan 02: Folder ACL API Layer Summary

API layer for folder ACL: CRUD endpoints on /folders/{id}/acl, ACL-filtered document listing, and access_source field on document detail responses exposing how a user gained access to a document.

## What Was Built

**Task 1: Folder ACL CRUD endpoints + ACL-filtered folder documents**

Added three new endpoints to `src/app/routers/folders.py`:
- `GET /folders/{folder_id}/acl` — list folder ACL entries (requires ADMIN on folder or superuser)
- `POST /folders/{folder_id}/acl` — create folder ACL entry (requires ADMIN on folder or superuser)
- `DELETE /folders/{folder_id}/acl/{acl_id}` — remove folder ACL entry (requires ADMIN on folder or superuser)

Updated `GET /folders/{folder_id}/documents` to pass `user_id` and `is_superuser` to `folder_service.get_folder_documents()`, enabling ACL-based filtering introduced in Plan 01.

**Task 2: access_source field on document detail + API tests**

Added `get_access_source()` function to `acl_service.py`:
- Uses shared `_get_ancestor_folder_ids()` helper (no CTE duplication)
- Returns `{"access_source": "direct"|"folder_inherited"|"open", "access_source_folder_name": str|None}`
- Superusers always return "direct"
- Documents with direct DocumentACL entries return "direct"
- Documents with folder ACL on ancestor chain return "folder_inherited" + folder name
- Documents with no ACL anywhere return "open"

Added `access_source` and `access_source_folder_name` optional fields to `DocumentResponse` schema (backward compatible — None by default).

Updated `GET /documents/{document_id}` endpoint to compute and include access_source in the response via `model_copy(update=access_info)`.

Added 4 API-level test functions to `tests/test_folder_acl.py`:
- `test_folder_acl_api_crud` — full GET/POST/DELETE cycle
- `test_folder_acl_api_requires_admin` — 403 for non-admin
- `test_get_folder_documents_acl_filtered` — ACL filtering via HTTP
- `test_access_source_field` — access_source field present in document detail response

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed PermissionLevel enum case in test data**
- **Found during:** Task 2 (test run)
- **Issue:** Plan template used `"READ"` (uppercase) but `PermissionLevel` enum values are lowercase (`"read"`), causing 422 Unprocessable Entity on POST /folders/{id}/acl
- **Fix:** Changed test payloads from `"READ"` to `"read"` to match actual enum values
- **Files modified:** `tests/test_folder_acl.py`
- **Commit:** f5de227

**2. [Rule 1 - Bug] Fixed test_access_source_field test logic**
- **Found during:** Task 2 (test run)
- **Issue:** Plan template used `regular_token` to access a document that only has an owner ACL for the admin uploader; regular user correctly gets 403
- **Fix:** Changed test to use admin headers (the document owner), which correctly shows `"direct"` access_source
- **Files modified:** `tests/test_folder_acl.py`
- **Commit:** f5de227

## Test Results

- `tests/test_folder_acl.py`: 15/15 passed (11 service-level + 4 API-level)
- `tests/test_acl.py`, `test_auth.py`, `test_documents.py`, `test_folders.py`: all passed
- Pre-existing failure in `test_auto_activities.py::test_execute_auto_activity_success` confirmed unrelated to this plan (SQLite foreign key cycle in workflow engine, present before changes)

## Self-Check

### Created files check
- No new files created (all modifications to existing files)

### Commits check
- 12b7a63: feat(29-02): folder ACL CRUD endpoints + ACL-filtered folder documents
- f5de227: feat(29-02): access_source on document detail + API-level tests

## Self-Check: PASSED
