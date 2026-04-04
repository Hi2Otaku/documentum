---
phase: 09-auto-activities-workflow-agent-integration
plan: 03
subsystem: auto-activity-tests
tags: [testing, auto-activity, integration-api, registry, retry, skip]
dependency_graph:
  requires: [09-01-auto-method-registry, 09-02-workflow-agent]
  provides: [auto-activity-test-coverage, integration-api-test-coverage]
  affects: [builtin.py, workflows-router]
tech_stack:
  added: []
  patterns: [session-factory-patching, mock-celery-task, api-driven-state-setup]
key_files:
  created:
    - tests/test_auto_activities.py
    - tests/test_integration_api.py
  modified:
    - src/app/auto_methods/builtin.py
    - src/app/routers/workflows.py
decisions:
  - Test _execute_async by patching async_session_factory to use test SQLite StaticPool
  - Error logging test verifies method raises and AutoActivityLog model works (not full _execute_async error path with SQLite)
  - Poll test mocks execute_auto_activity.delay to avoid Celery broker dependency
  - Integration API reject test uses template without reject flow to prove endpoint accessibility
metrics:
  duration: 13min
  completed: "2026-04-04"
---

# Phase 9 Plan 3: Auto Activity and Integration API Tests Summary

22 tests covering auto method registry, ActivityContext, built-in methods, engine AUTO handling, execution logging, admin retry/skip endpoints, and external system REST API integration with two bugfixes in builtin.py and workflows router.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Auto activity tests (AUTO-01 through AUTO-05, INTG-01) | 64b1852 | tests/test_auto_activities.py, builtin.py, workflows.py |
| 2 | Integration API tests (INTG-02, INTG-03) | 899c2df | tests/test_integration_api.py |

## What Was Built

### test_auto_activities.py (18 tests)
- **Registry tests (AUTO-01)**: Discovers 4 builtins, retrieves callables, returns None for unknown, custom registration works
- **ActivityContext tests (AUTO-01)**: get_variable reads snapshot, set_variable updates in-memory dict
- **Built-in method tests (AUTO-03, INTG-01)**: send_email dev mode, change_lifecycle_state, modify_acl add, call_external_api with httpx mock
- **Engine AUTO handling (AUTO-01)**: Verifies AUTO activity left in ACTIVE state for Celery pickup
- **Execution tests (AUTO-04)**: Success execution creates log and completes activity; failure raises ValueError and triggers retry path
- **Admin endpoint tests (AUTO-05)**: Retry resets ERROR to ACTIVE; skip marks COMPLETE and advances workflow; both reject non-ERROR activities with 400

### test_integration_api.py (4 tests)
- **INTG-02**: External system starts workflow via JWT-authenticated POST; starts workflow with initial_variables override
- **INTG-03**: External system completes work item advancing workflow to FINISHED; reject endpoint accessible (returns 400 when no reject flow)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed modify_acl builtin missing principal_type argument**
- **Found during:** Task 1, test_modify_acl_add
- **Issue:** `create_acl_entry()` called with 4 positional args instead of 5; missing `principal_type` parameter caused `permission` PermissionLevel to be passed as `principal_type` string
- **Fix:** Added `"user"` as `principal_type` argument: `create_acl_entry(ctx.db, doc_id, target_user_id, "user", permission, ctx.user_id)`
- **Files modified:** src/app/auto_methods/builtin.py
- **Commit:** 64b1852

**2. [Rule 1 - Bug] Fixed skip endpoint double COMPLETE state transition**
- **Found during:** Task 1, test_skip_failed_activity
- **Issue:** Skip endpoint set activity state to COMPLETE before calling `_advance_from_activity`, which also tries ACTIVE->COMPLETE, causing "Invalid state transition: complete -> complete" ValueError
- **Fix:** Removed the COMPLETE state assignment; let `_advance_from_activity` handle the ACTIVE->COMPLETE transition
- **Files modified:** src/app/routers/workflows.py
- **Commit:** 64b1852

## Verification Results

- `python -m pytest tests/test_auto_activities.py tests/test_integration_api.py -v`: 22 passed
- `python -m pytest tests/ -x`: 233 passed (full suite, no regressions)
- test_auto_activities.py has 18 async test functions (>= 14 required)
- test_integration_api.py has 4 async test functions (>= 4 required)

## Known Stubs

None - all tests are fully implemented and passing.
