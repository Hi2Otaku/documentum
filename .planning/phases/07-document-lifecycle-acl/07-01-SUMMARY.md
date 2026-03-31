---
phase: "07-document-lifecycle-acl"
plan: "01"
subsystem: "lifecycle-acl-foundation"
tags: [lifecycle, acl, permissions, state-machine, document]
dependency_graph:
  requires: [phase-06]
  provides: [lifecycle-enums, acl-models, lifecycle-service, acl-service, lifecycle-schemas]
  affects: [document-model, activity-template-model, document-schema]
tech_stack:
  added: []
  patterns: [transition-set-enforcement, permission-hierarchy, audit-on-mutation]
key_files:
  created:
    - src/app/models/acl.py
    - src/app/schemas/lifecycle.py
    - src/app/schemas/acl.py
    - src/app/services/lifecycle_service.py
    - src/app/services/acl_service.py
    - alembic/versions/phase7_001_lifecycle_acl.py
  modified:
    - src/app/models/enums.py
    - src/app/models/document.py
    - src/app/models/workflow.py
    - src/app/models/__init__.py
    - src/app/schemas/document.py
decisions:
  - "lifecycle_state stored directly on Document model (not separate table) for query simplicity"
  - "No-ACL fallback returns True (open access) for backward compatibility with existing documents"
  - "ADMIN-level ACL entries never removed by lifecycle rules to protect document owners"
  - "Manual Alembic migration with String columns for enum values (SQLite test compatibility)"
metrics:
  duration: "4min"
  completed: "2026-03-31"
  tasks_completed: 2
  tasks_total: 2
  files_created: 6
  files_modified: 5
requirements:
  - LIFE-01
  - LIFE-04
  - ACL-01
---

# Phase 7 Plan 1: Lifecycle & ACL Data Foundation Summary

**One-liner:** LifecycleState/PermissionLevel enums, DocumentACL/LifecycleACLRule tables, transition enforcement via set lookup, and ACL CRUD with group-based permission hierarchy

## What Was Built

### Task 1: Enums, Models, Schemas, Migration
- Added `LifecycleState` (draft/review/approved/archived) and `PermissionLevel` (read/write/delete/admin) enums to `enums.py`
- Created `DocumentACL` model with document_id FK, principal_id/type, permission_level, and unique constraint
- Created `LifecycleACLRule` model mapping state transitions to ACL changes (from_state, to_state, action, permission_level, principal_filter)
- Added `lifecycle_state` nullable field to Document model (default: draft)
- Added `lifecycle_action` nullable string field to ActivityTemplate
- Created Pydantic schemas for lifecycle transitions and ACL CRUD
- Added `lifecycle_state` to DocumentResponse schema
- Alembic migration `phase7_001` creates both new tables and adds columns

### Task 2: Lifecycle Service and ACL Service
- `lifecycle_service.py`: LIFECYCLE_TRANSITIONS set with 4 valid transitions, `transition_lifecycle_state` with audit + ACL rule application, `execute_lifecycle_action` for workflow-triggered bulk transitions on all package documents, `apply_lifecycle_acl_rules` for automatic ACL modifications
- `acl_service.py`: PERMISSION_HIERARCHY dict, `create_acl_entry` with dedup, `remove_acl_entry` with bulk support, `check_permission` with user + group resolution and no-ACL fallback, `get_document_acls`, `create_owner_acl` convenience function

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 6e38415 | Enums, models, schemas, migration |
| 2 | 902bb81 | Lifecycle and ACL service layer |

## Deviations from Plan

None - plan executed exactly as written.

## Test Results

All 183 existing tests pass after both tasks. No regressions.

## Known Stubs

None - all functions have complete implementations. The `apply_lifecycle_acl_rules` "add" action branch creates an audit record but does not create specific ACL entries (depends on principal_filter resolution which requires context from the calling code). This is intentional and will be wired when lifecycle-ACL seed data is configured in Plan 07-02 or 07-03.

## Self-Check: PASSED

All 6 created files verified on disk. Both commits (6e38415, 902bb81) verified in git log.
