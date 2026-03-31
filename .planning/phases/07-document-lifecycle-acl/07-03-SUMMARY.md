---
phase: "07-document-lifecycle-acl"
plan: "03"
subsystem: "lifecycle-acl-tests"
tags: [lifecycle, acl, integration-tests, permissions, audit]
dependency_graph:
  requires:
    - phase: "07-01"
      provides: "lifecycle_service, acl_service, enums, models, schemas"
    - phase: "07-02"
      provides: "lifecycle router, ACL-protected routes, engine lifecycle hook"
  provides:
    - 28 integration tests covering LIFE-01 through LIFE-04 and ACL-01 through ACL-04
  affects: []
tech_stack:
  added: []
  patterns: [direct-db-setup-for-unexposed-fields, lifecycle-acl-rule-seeding-in-tests]
key_files:
  created:
    - tests/test_lifecycle.py
    - tests/test_acl.py
  modified:
    - src/app/services/acl_service.py
key_decisions:
  - "lifecycle_action set via direct DB access in tests since field not exposed in API schema"
  - "ACL rule seeding done inline per test via LifecycleACLRule model insertion"
  - "Second test user created inline via helper function rather than conftest fixture to avoid conflicts"
metrics:
  duration: "5min"
  completed: "2026-03-31"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 1
requirements:
  - LIFE-01
  - LIFE-02
  - LIFE-03
  - LIFE-04
  - ACL-01
  - ACL-02
  - ACL-03
  - ACL-04
---

# Phase 7 Plan 3: Lifecycle & ACL Integration Tests Summary

**28 integration tests proving lifecycle state machine, workflow-triggered transitions, ACL enforcement with 403 on unauthorized access, group-based permissions, and audit trail for all mutations**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-31T08:12:09Z
- **Completed:** 2026-03-31T08:17:00Z
- **Tasks:** 2/2

## What Was Built

### Task 1: Lifecycle Integration Tests (LIFE-01 through LIFE-04)
- 13 tests in `tests/test_lifecycle.py`
- LIFE-01: 7 tests for valid transitions (DRAFT->REVIEW->APPROVED->ARCHIVED, reject back to DRAFT) and invalid transitions (skip REVIEW, ARCHIVED->DRAFT, DRAFT->ARCHIVED)
- LIFE-02: 3 tests for workflow-triggered transitions (single doc, multiple docs, failure does not halt workflow)
- LIFE-03: 2 tests for audit trail (successful and failed transitions)
- LIFE-04: 1 test for ACL rules applied on REVIEW->APPROVED transition (removes WRITE, preserves ADMIN)

### Task 2: ACL Integration Tests (ACL-01 through ACL-04)
- 15 tests in `tests/test_acl.py`
- ACL-01: 5 tests for ACL CRUD (create, list, delete, permission hierarchy, no-ACL fallback)
- ACL-02: 1 test for workflow-triggered ACL modification via lifecycle rules
- ACL-03: 2 tests for audit trail (grant and revocation)
- ACL-04: 7 tests for permission enforcement (403 on unauthorized GET/PUT/checkout, open upload/list, admin full access, group-based permission)

## Task Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | aea68da | Lifecycle tests + acl_service flush bug fix |
| 2 | d3dca1f | ACL integration tests |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] acl_service.create_acl_entry missing flush before return**
- **Found during:** Task 1
- **Issue:** `create_acl_entry` called `db.add(entry)` but never flushed, so the returned entry had `id=None` and `created_at=None`, causing Pydantic validation errors in the lifecycle router's add_acl_entry endpoint
- **Fix:** Added `await db.flush()` and `await db.refresh(entry)` after `db.add(entry)` in acl_service.py
- **Files modified:** src/app/services/acl_service.py
- **Commit:** aea68da

**Total deviations:** 1 auto-fixed (1 bug fix)

## Test Results

All 211 tests pass (183 existing + 13 lifecycle + 15 ACL). No regressions.

## Known Stubs

None - all test functions have complete assertions and all features are wired end-to-end.

## Self-Check: PASSED

All 2 created files verified on disk. Both commits (aea68da, d3dca1f) verified in git log.
