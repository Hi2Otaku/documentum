---
phase: "22"
plan: "02"
subsystem: retention-records-management
tags: [retention, legal-hold, deletion-guard, records-management]
dependency_graph:
  requires: []
  provides: [retention-policies, document-retention-assignment, legal-holds, deletion-blocking]
  affects: [document-delete-endpoint]
tech_stack:
  added: []
  patterns: [service-layer-guard, soft-delete-blocking, audit-logging]
key_files:
  created:
    - src/app/models/retention.py
    - src/app/schemas/retention.py
    - src/app/services/retention_service.py
    - src/app/routers/retention.py
    - alembic/versions/phase22_001_retention.py
    - tests/test_retention.py
  modified:
    - src/app/models/__init__.py
    - src/app/routers/documents.py
    - src/app/main.py
decisions:
  - DispositionAction enum defined locally in retention model (archive/delete)
  - Legal hold uses released_at null check for active status
  - Retention check happens before document soft-delete in delete endpoint
metrics:
  duration: 6m
  completed: 2026-04-06
  tasks: 4
  files_created: 6
  files_modified: 3
  tests_added: 20
  tests_passing: 20
---

# Phase 22 Plan 02: Retention Policies, Legal Holds & Deletion Blocking Summary

Complete retention and records management with policy CRUD, document assignment, legal holds, and deletion blocking via service-layer guard on document delete endpoint.

## What Was Built

### Task 1: Retention Models & Migration (7a1b517)
- **RetentionPolicy** model: name, description, retention_period_days, disposition_action (archive/delete)
- **DocumentRetention** model: links documents to policies with applied_at/expires_at
- **LegalHold** model: document_id, reason, placed_by, placed_at, released_at
- Alembic migration `phase22_001` creating all three tables with proper FK constraints

### Task 2: Schemas & Service Layer (caf069d)
- Pydantic request/response schemas for all three entities plus RetentionStatusResponse
- **retention_service** with full CRUD for policies, document-policy assignment/removal, legal hold placement/release
- **check_document_deletable** guard function checking active retentions (non-expired) and active holds (unreleased)
- Full audit logging on all mutations

### Task 3: API Endpoints & Delete Guard (31a043c)
- `POST/GET/PUT/DELETE /retention-policies` -- admin-only policy management
- `POST /documents/{id}/retention` -- assign policy to document (auto-calculates expiration)
- `DELETE /documents/{id}/retention/{retention_id}` -- remove assignment
- `POST /documents/{id}/legal-hold` -- place hold
- `DELETE /documents/{id}/legal-hold/{hold_id}` -- release hold
- `GET /documents/{id}/retention-status` -- combined retention + hold status view
- Document delete endpoint now calls check_document_deletable, returns 403 with clear message when blocked

### Task 4: Tests (b1a0bd0)
- 20 comprehensive tests covering all retention functionality
- Policy CRUD, auth enforcement, assignment, deletion blocking, legal holds, status endpoint

## Deviations from Plan

None -- plan executed exactly as written.

## Known Stubs

None -- all endpoints are fully wired with real service logic and database operations.

## Self-Check: PASSED

All 6 created files verified. All 4 task commits verified. 20/20 tests passing.
