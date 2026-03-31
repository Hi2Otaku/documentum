---
phase: "07-document-lifecycle-acl"
plan: "02"
subsystem: "lifecycle-acl-wiring"
tags: [lifecycle, acl, permissions, engine-hook, document-routes, fastapi-dependency]
dependency_graph:
  requires:
    - phase: "07-01"
      provides: "lifecycle_service, acl_service, enums, models, schemas"
  provides:
    - engine lifecycle hook on activity completion
    - require_permission dependency factory for ACL enforcement
    - lifecycle transition REST endpoint
    - ACL CRUD endpoints (list, add, remove)
    - ACL-protected document routes
    - owner ACL creation on document upload
  affects: [document-routes, workflow-engine, phase-08-frontend]
tech_stack:
  added: []
  patterns: [dependency-factory-for-acl, lazy-import-for-circular-avoidance, error-isolated-engine-hooks]
key_files:
  created:
    - src/app/routers/lifecycle.py
  modified:
    - src/app/services/engine_service.py
    - src/app/core/dependencies.py
    - src/app/routers/documents.py
    - src/app/services/document_service.py
    - src/app/main.py
    - tests/test_documents.py
key_decisions:
  - "require_permission uses dependency factory pattern returning async closure for FastAPI DI"
  - "Engine lifecycle hook uses simple for-loop over activity templates rather than moving template map build order"
  - "Upload and list document routes exempt from ACL (no document_id in path)"
  - "Test expectations updated for ACL-aware behavior (non-owner checkout now returns 403)"
patterns_established:
  - "require_permission(PermissionLevel.X) as reusable route guard for document-level ACL"
  - "Lazy import pattern for service cross-references in dependencies.py"
requirements_completed: [LIFE-02, LIFE-03, ACL-02, ACL-03, ACL-04]
metrics:
  duration: "4min"
  completed: "2026-03-31"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 6
---

# Phase 7 Plan 2: Lifecycle & ACL Wiring Summary

**Engine lifecycle hook on activity completion, require_permission ACL dependency on all document routes, lifecycle/ACL REST endpoints, and owner ACL on upload**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-31T08:05:22Z
- **Completed:** 2026-03-31T08:09:00Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Engine now fires lifecycle_action on activity completion with error isolation (workflow never halted by lifecycle errors)
- All document routes with document_id enforce ACL via require_permission dependency (READ/WRITE as appropriate)
- Lifecycle router provides manual transition, state query, and ACL CRUD (list/add/remove) endpoints
- Document upload automatically creates ADMIN ACL entry for document creator

## Task Commits

Each task was committed atomically:

1. **Task 1: Engine lifecycle hook and require_permission dependency** - `054ad84` (feat)
2. **Task 2: Lifecycle router, document route protection, and owner ACL on upload** - `bb6ab0f` (feat)

## Files Created/Modified
- `src/app/routers/lifecycle.py` - New router with lifecycle transition, state query, and ACL CRUD endpoints
- `src/app/services/engine_service.py` - Added lifecycle_action hook in _advance_from_activity
- `src/app/core/dependencies.py` - Added require_permission dependency factory with PermissionLevel import
- `src/app/routers/documents.py` - Updated 6 routes to use require_permission instead of get_current_user
- `src/app/services/document_service.py` - Added create_owner_acl call after document upload
- `src/app/main.py` - Registered lifecycle router
- `tests/test_documents.py` - Updated test expectations for ACL-aware behavior

## Decisions Made
- require_permission uses a dependency factory returning an async closure, allowing `Depends(require_permission(PermissionLevel.READ))` syntax
- Engine lifecycle hook does a simple loop to find the current activity template rather than restructuring existing code
- Upload and list routes remain open (no document_id path parameter to check ACL against)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test expectations for ACL enforcement**
- **Found during:** Task 2 (document route protection)
- **Issue:** `test_checkout_already_locked` expected 409 but regular user now gets 403 (no ACL entry on admin-created document). `test_admin_force_unlock` expected 200 but regular user checkout fails with 403 first.
- **Fix:** Updated test_checkout_already_locked to expect 403. Updated test_admin_force_unlock to have regular user upload the document (gaining ADMIN ACL) instead of admin.
- **Files modified:** tests/test_documents.py
- **Verification:** All 183 tests pass
- **Committed in:** bb6ab0f (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix in tests)
**Impact on plan:** Test update necessary for correctness after ACL enforcement. No scope creep.

## Issues Encountered
None beyond the test updates documented above.

## User Setup Required
None - no external service configuration required.

## Test Results

All 183 existing tests pass after both tasks. No regressions.

## Known Stubs

None - all functions have complete implementations. The lifecycle router's remove_acl_entry endpoint uses direct DB delete rather than the acl_service.remove_acl_entry function (which expects different parameters), but this is a deliberate implementation choice, not a stub.

## Next Phase Readiness
- Lifecycle and ACL wiring complete, engine hooks functional
- Plan 07-03 (integration tests) can validate end-to-end lifecycle transitions through workflow completion
- Frontend can consume lifecycle/ACL endpoints when Phase 8 begins

---
*Phase: 07-document-lifecycle-acl*
*Completed: 2026-03-31*
