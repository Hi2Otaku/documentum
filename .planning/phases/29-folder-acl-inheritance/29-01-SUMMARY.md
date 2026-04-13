---
phase: 29-folder-acl-inheritance
plan: "01"
subsystem: backend/acl
tags: [acl, folder, permissions, inheritance, recursive-cte, sqlalchemy]
dependency_graph:
  requires: [phase28-cabinet-folder-hierarchy]
  provides: [folder-acl-model, folder-acl-inheritance-in-check-permission, acl-filtered-folder-documents]
  affects: [document_service.list_documents, folder_service.get_folder_documents, acl_service.check_permission]
tech_stack:
  added: []
  patterns: [recursive-cte-ancestor-walk, per-document-n+1-acl-filter, subquery-cte-descendant-walk]
key_files:
  created:
    - src/app/models/acl.py (FolderACL class added)
    - alembic/versions/add_folder_acl.py
    - tests/test_folder_acl.py
  modified:
    - src/app/schemas/acl.py (FolderACLEntryCreate, FolderACLEntryResponse added)
    - src/app/services/acl_service.py (_get_ancestor_folder_ids, check_permission extended, folder ACL CRUD)
    - src/app/services/folder_service.py (get_folder_documents extended with user_id/is_superuser)
    - src/app/services/document_service.py (list_documents extended with folder ACL branch)
decisions:
  - "_get_ancestor_folder_ids() extracted as shared CTE helper for reuse by check_permission and future get_access_source"
  - "N+1 per-document check_permission approach for get_folder_documents (acceptable with page_size cap)"
  - "list_documents uses subquery descendant CTE approach instead of N+1 (handles larger result sets)"
  - "Direct document ACL overrides folder ACL entirely — folder ACL only runs when no direct DocumentACL entries exist"
metrics:
  duration: "4 min"
  completed: "2026-04-13"
  tasks_completed: 3
  files_changed: 7
---

# Phase 29 Plan 01: Folder ACL Inheritance Backend Summary

FolderACL model with recursive CTE ancestor walk, extended check_permission with folder inheritance, ACL-filtered folder/document listing, and 12 passing FOLD-05 tests.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 0 | Wave 0 stub tests for Nyquist compliance | 64462d4 | tests/test_folder_acl.py |
| 1 | FolderACL model, schemas, migration, service CRUD + check_permission | 33f6f04 | acl.py, schemas/acl.py, acl_service.py, add_folder_acl.py |
| 2 | ACL-filtered document listing + comprehensive test suite | c45d657 | folder_service.py, document_service.py, test_folder_acl.py |

## What Was Built

**FolderACL model** (`src/app/models/acl.py`): New `FolderACL` class mirroring `DocumentACL`, with `folder_id` FK to `folders.id`, `principal_id`, `principal_type`, `permission_level`, and unique constraint `uq_folder_acl_entry`.

**Schemas** (`src/app/schemas/acl.py`): `FolderACLEntryCreate` (without folder_id — comes from URL path) and `FolderACLEntryResponse` with `from_attributes=True`.

**Alembic migration** (`alembic/versions/add_folder_acl.py`): Creates `folder_acl` table with `create_type=False` on `permissionlevel` enum (already exists from `document_acl` migration). Revision chain: `phase29_001` revises `phase28_001`.

**`_get_ancestor_folder_ids()` shared helper** (`acl_service.py`): Recursive CTE walking up parent_id chain from given folder IDs. Returns all ancestor IDs including self. Used by `check_permission()` for folder ACL inheritance and will be reused by `get_access_source()` in Plan 02.

**Extended `check_permission()`** (`acl_service.py`): Added `is_superuser: bool = False` parameter (bypass at top). When `total_entries == 0` (no direct DocumentACL), instead of immediately returning True, now walks ancestor folders via `_get_ancestor_folder_ids()`, checks for FolderACL entries, and resolves access. Backward compat: no folder ACL entries → open access. Direct document ACL → folder ACL skipped entirely.

**Folder ACL CRUD** (`acl_service.py`): `create_folder_acl_entry` (idempotent), `get_folder_acls`, `remove_folder_acl_entry`, `check_folder_permission` (for ACL management gating in Plan 02 API layer).

**Extended `get_folder_documents()`** (`folder_service.py`): Added `user_id` and `is_superuser` params. When user_id provided and not superuser, fetches all documents then filters via per-document `check_permission()` before pagination. N+1 acceptable with page_size cap.

**Extended `list_documents()`** (`document_service.py`): Added folder ACL inheritance branch using descendant CTE subqueries. Replaces old `notin_(docs_with_acl)` branch with three-way logic: direct ACL OR (no direct ACL AND not in ACL folder) OR (no direct ACL AND folder grants access).

## Test Coverage

12 tests in `tests/test_folder_acl.py` covering all FOLD-05 sub-requirements:
- Folder READ grants document access
- No folder permission hides documents
- Direct ACL overrides folder ACL (folder path skipped)
- No folder ACL = open access (backward compat)
- Multi-folder OR logic
- Superuser bypass
- Nested folder inheritance (grandparent ACL → subfolder → document)
- Group-based folder ACL
- get_folder_documents filtered for non-superusers
- CRUD operations (create, idempotent duplicate, list, remove, remove non-existent)
- Placeholder for access_source (Plan 02)

No regressions: 15 existing `test_acl.py` tests pass unchanged.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

`test_access_source_field` in `tests/test_folder_acl.py` (line ~228): intentional placeholder for Plan 02's API test that will verify the `access_source` field in document responses. This is the only stub, and it does not prevent Plan 01's goal from being achieved.

## Self-Check: PASSED

All 5 key files found. All 3 task commits verified (64462d4, 33f6f04, c45d657).
