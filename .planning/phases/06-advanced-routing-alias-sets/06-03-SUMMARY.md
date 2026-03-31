---
phase: 06-advanced-routing-alias-sets
plan: 03
subsystem: testing
tags: [pytest, integration-tests, routing, reject-flows, alias-sets, sequential, runtime-selection]

# Dependency graph
requires:
  - phase: 06-advanced-routing-alias-sets
    plan: 02
    provides: "Engine routing dispatch, reject flow traversal, sequential/runtime performers, alias resolution"
provides:
  - "22 integration tests covering all Phase 6 requirements end-to-end"
  - "Regression safety net for routing, reject, alias, sequential, runtime_selection features"
affects: [phase-07, verifier, ci-pipeline]

# Tech tracking
tech-stack:
  added: []
  patterns: [inline-template-creation-tests, per-user-token-generation-for-inbox-tests]

key-files:
  created:
    - tests/test_routing.py
    - tests/test_reject_flows.py
    - tests/test_aliases.py
    - tests/test_sequential.py
  modified:
    - src/app/services/template_service.py
    - src/app/services/engine_service.py
    - src/app/services/alias_service.py
    - src/app/schemas/template.py

key-decisions:
  - "routing_type, performer_list, display_label, alias_set_id were not wired from schemas to DB in Plan 06-01; fixed inline as blocking bug (Rule 1/3)"
  - "Engine double-finish guard added: break advancement loop when workflow already FINISHED (supports broadcast routing with multiple END activities)"
  - "Soft-deleted alias mappings filtered in get_alias_set via filtered eager load (SQLAlchemy .and_ clause)"

patterns-established:
  - "Per-user auth tokens created inline via create_access_token for inbox operation tests"
  - "Sequential/runtime_selection tests use workflow endpoint (not inbox) for completion to bypass performer_id check"

requirements-completed: [EXEC-08, EXEC-09, EXEC-10, EXEC-11, PERF-04, PERF-05, ALIAS-01, ALIAS-02, ALIAS-03]

# Metrics
duration: 14min
completed: 2026-03-31
---

# Phase 6 Plan 03: Integration Tests for Routing, Reject Flows, Aliases, and Sequential/Runtime Performers Summary

**22 integration tests proving all 9 Phase 6 requirements: three routing modes, reject flow traversal with variable preservation, alias CRUD with snapshot-at-start semantics, sequential performer ordering with reject-back, and runtime selection with group validation**

## Performance

- **Duration:** 14 min
- **Started:** 2026-03-31T07:11:00Z
- **Completed:** 2026-03-31T07:25:31Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Created 22 integration tests across 4 test files covering all Phase 6 requirements end-to-end
- Fixed 4 service-layer bugs where Plan 06-01 schema fields were not wired to the database (routing_type, performer_list, display_label, alias_set_id)
- Fixed engine double-finish guard for broadcast routing with multiple END activities
- Fixed alias service to filter soft-deleted mappings from eager-loaded relationships
- Full test suite green at 183 tests with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Routing tests (EXEC-08..10) and reject flow tests (EXEC-11)** - `d212d86` (test)
2. **Task 2: Alias CRUD tests (ALIAS-01..03) and sequential/runtime tests (PERF-04..05)** - `18b14f6` (test)

## Files Created/Modified
- `tests/test_routing.py` - 5 tests: performer-chosen (3), conditional (1), broadcast (1) -- 354 lines
- `tests/test_reject_flows.py` - 3 tests: reject traversal, no-reject-flow error, variable preservation -- 461 lines
- `tests/test_aliases.py` - 8 tests: CRUD (5), template alias (1), update independence (1), snapshot-at-start (1) -- 578 lines
- `tests/test_sequential.py` - 6 tests: sequential ordering (1), reject-back (1), reject-at-first error (1), runtime selection (1), missing/invalid performer errors (2) -- 715 lines
- `src/app/services/template_service.py` - Wire routing_type, performer_list, display_label, alias_set_id to model constructors
- `src/app/services/engine_service.py` - Add workflow FINISHED guard in advancement loop
- `src/app/services/alias_service.py` - Filter soft-deleted mappings in get_alias_set
- `src/app/schemas/template.py` - Add alias_set_id to ProcessTemplateCreate and ProcessTemplateUpdate

## Decisions Made
- Fixed 4 missing field wirings as Rule 1/3 deviations (blocking for test execution)
- Added FINISHED guard as Rule 1 deviation (broadcast routing with multiple END activities causes double-finish)
- Filtered deleted mappings as Rule 1 deviation (soft-delete not respected in eager load)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Wire routing_type and performer_list in template_service.add_activity**
- **Found during:** Task 1 (routing tests)
- **Issue:** Plan 06-01 added routing_type and performer_list to ActivityTemplate model and schema, but template_service.add_activity did not include them in the constructor. All activities saved routing_type as NULL, defaulting to "conditional".
- **Fix:** Added routing_type=data.routing_type and performer_list=data.performer_list to ActivityTemplate constructor
- **Files modified:** src/app/services/template_service.py
- **Verification:** Performer-chosen routing test passes (routing_type="performer_chosen" persisted)
- **Committed in:** d212d86 (Task 1)

**2. [Rule 3 - Blocking] Wire display_label in template_service.add_flow**
- **Found during:** Task 1 (routing tests)
- **Issue:** FlowTemplate constructor in add_flow did not include display_label. Performer-chosen routing couldn't match flows by label.
- **Fix:** Added display_label=data.display_label to FlowTemplate constructor
- **Files modified:** src/app/services/template_service.py
- **Verification:** Performer-chosen routing correctly selects flow by display_label
- **Committed in:** d212d86 (Task 1)

**3. [Rule 1 - Bug] Engine double-finish guard for multiple END activities**
- **Found during:** Task 1 (broadcast routing test)
- **Issue:** Broadcast routing fires all outgoing flows; with 2 END activities, both auto-complete and get queued. First END finishes workflow, second tries FINISHED->FINISHED transition (ValueError).
- **Fix:** Added `if workflow.state == WorkflowState.FINISHED: break` at top of advancement while loop
- **Files modified:** src/app/services/engine_service.py
- **Verification:** Broadcast routing test passes with both END activities completing
- **Committed in:** d212d86 (Task 1)

**4. [Rule 3 - Blocking] Wire alias_set_id in template creation and schema**
- **Found during:** Task 2 (alias template tests)
- **Issue:** ProcessTemplateCreate/Update schemas and template_service.create_template did not support alias_set_id. Templates couldn't reference alias sets.
- **Fix:** Added alias_set_id field to schemas and constructor
- **Files modified:** src/app/schemas/template.py, src/app/services/template_service.py
- **Committed in:** 18b14f6 (Task 2)

**5. [Rule 1 - Bug] Soft-deleted alias mappings returned by get_alias_set**
- **Found during:** Task 2 (alias mapping removal test)
- **Issue:** selectinload(AliasSet.mappings) loaded ALL mappings including soft-deleted ones. After removing a mapping, it still appeared in the response.
- **Fix:** Used filtered eager load: selectinload(AliasSet.mappings.and_(AliasMapping.is_deleted == False))
- **Files modified:** src/app/services/alias_service.py
- **Committed in:** 18b14f6 (Task 2)

---

**Total deviations:** 5 auto-fixed (2 bugs, 3 blocking)
**Impact on plan:** All fixes necessary for Plan 06-01/06-02 features to work correctly through the HTTP API. These were missing wirings between existing schema fields and the database layer, not new functionality.

## Issues Encountered
None beyond the auto-fixed deviations above.

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all tests exercise real engine logic end-to-end through the HTTP API.

## Next Phase Readiness
- Phase 6 is fully complete: all routing modes, reject flows, alias sets, and performer types tested end-to-end
- 183 total tests providing comprehensive regression safety
- Ready for Phase 7 (or next milestone phase)

---
*Phase: 06-advanced-routing-alias-sets*
*Completed: 2026-03-31*
