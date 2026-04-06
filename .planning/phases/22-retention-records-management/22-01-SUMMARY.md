---
phase: 22-retention-records-management
plan: "01"
subsystem: retention
tags: [retention, records-management, policies, document-governance]
dependency_graph:
  requires: [document-model, audit-service, auth-dependencies]
  provides: [retention-policy-crud, document-retention-assignment, legal-hold-model]
  affects: [document-deletion, document-detail-view]
tech_stack:
  added: []
  patterns: [service-layer-crud, admin-only-endpoints, soft-delete, computed-fields]
key_files:
  created:
    - src/app/models/retention.py
    - src/app/schemas/retention.py
    - src/app/services/retention_service.py
    - src/app/routers/retention.py
    - alembic/versions/phase22_001_retention.py
    - tests/test_retention.py
  modified:
    - src/app/models/enums.py
    - src/app/models/__init__.py
    - src/app/main.py
decisions:
  - "Used soft-delete pattern consistent with existing codebase for retention assignments"
  - "Added timezone-naive datetime handling in is_expired computed field to support SQLite test environment"
metrics:
  duration: 5m
  completed: "2026-04-06T19:50:53Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 6
  files_modified: 3
  test_count: 24
  test_pass: 24
---

# Phase 22 Plan 01: Retention Policy Models, Service, and API Summary

Retention policy CRUD API with document assignment, supporting admin management of retention periods and disposition actions via REST endpoints.

## What Was Built

### Task 1: Models, enums, migration, and schema definitions (TDD)
- Added `DispositionAction` enum (archive, delete) to `src/app/models/enums.py`
- Created `RetentionPolicy`, `DocumentRetention`, `LegalHold` SQLAlchemy models in `src/app/models/retention.py`
- Created Pydantic schemas with computed fields (`is_expired`, `is_active`) in `src/app/schemas/retention.py`
- Created Alembic migration `phase22_001` for three new tables with indexes and constraints
- Updated `src/app/models/__init__.py` with new exports

### Task 2: Retention service, router, and registration
- Created `src/app/services/retention_service.py` with full CRUD for policies and document-assignment operations
- Created `src/app/routers/retention.py` with admin-only REST endpoints at `/retention`
- Registered router in `src/app/main.py`
- Assign endpoint computes `expires_at` from policy's `retention_period_days`
- Duplicate assignment detection returns 409

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 (RED) | 3bba07b | Failing tests for retention models, enums, schemas |
| 1 (GREEN) | 603ebc0 | Models, enums, schemas, migration implementation |
| 2 | 1c2931e | Service, router, API tests, main.py registration |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed timezone-naive datetime comparison in is_expired**
- **Found during:** Task 2 (API test for list_document_retentions)
- **Issue:** SQLite returns timezone-naive datetimes, causing `can't compare offset-naive and offset-aware datetimes` error in the `is_expired` computed field
- **Fix:** Added timezone-aware normalization in `DocumentRetentionResponse.is_expired` before comparison
- **Files modified:** src/app/schemas/retention.py
- **Commit:** 1c2931e

## Known Stubs

None - all endpoints are fully wired with working data sources.

## Verification

All 24 tests pass:
- 3 enum tests
- 4 model tests (RetentionPolicy, DocumentRetention, LegalHold)
- 7 schema validation tests
- 10 API endpoint tests (CRUD + assignment)

## Self-Check: PASSED
