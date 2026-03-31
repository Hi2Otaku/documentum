---
phase: 06-advanced-routing-alias-sets
plan: 02
subsystem: api, engine
tags: [fastapi, sqlalchemy, routing, reject-flow, sequential-performer, alias-resolution]

# Dependency graph
requires:
  - phase: 06-advanced-routing-alias-sets
    plan: 01
    provides: "RoutingType enum, AliasSet/AliasMapping models, schema extensions, alias_service.resolve_alias_snapshot"
provides:
  - "Routing type dispatch in engine: conditional, performer_chosen, broadcast"
  - "reject_work_item engine function with REJECT flow traversal and activity reset"
  - "Sequential performer tracking with current_performer_index"
  - "Runtime selection with group membership validation"
  - "Alias resolution from workflow.alias_snapshot in resolve_performers"
  - "Alias snapshot creation at workflow start"
  - "selected_path and next_performer_id passthrough from routers to engine"
affects: [06-03, inbox-tests, routing-tests, reject-flow-tests]

# Tech tracking
tech-stack:
  added: []
  patterns: [routing-type-dispatch-match-case, reject-flow-traversal, sequential-performer-index-tracking]

key-files:
  created: []
  modified:
    - src/app/services/engine_service.py
    - src/app/services/inbox_service.py
    - src/app/routers/inbox.py
    - src/app/routers/workflows.py
    - tests/test_inbox.py

key-decisions:
  - "Reject flow tokens placed as immediately consumed since target activity is manually activated"
  - "selected_path cleared after first queue iteration to prevent carrying into auto-complete activities"
  - "Sequential rejection at index 0 raises ValueError rather than following reject flows (separate mechanism)"
  - "Test updated to expect 400 on reject without reject flow (D-03 compliance)"

patterns-established:
  - "Routing dispatch via match/case on activity_template.routing_type in advancement loop"
  - "Reject flow traversal resets target activity COMPLETE->ACTIVE with new work items (old items preserved)"
  - "Sequential performer: create next work item and return WITHOUT advancing workflow until last performer"

requirements-completed: [EXEC-08, EXEC-09, EXEC-10, EXEC-11, PERF-04, PERF-05]

# Metrics
duration: 6min
completed: 2026-03-31
---

# Phase 6 Plan 02: Engine Routing Dispatch, Reject Flows, Sequential/Runtime Performers, Alias Resolution Summary

**Three-way routing dispatch (conditional/performer-chosen/broadcast), reject flow traversal with activity reset, sequential performer index tracking, runtime selection with group validation, and alias snapshot resolution at workflow start**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-31T07:03:01Z
- **Completed:** 2026-03-31T07:09:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Implemented routing type dispatch in _advance_from_activity: conditional (existing behavior preserved), performer_chosen (selected_path matching), broadcast (all flows fire)
- Added reject_work_item function that traverses REJECT flow edges, resets target activities from COMPLETE to ACTIVE, and creates new work items for original performers
- Added sequential performer tracking: completion advances index, creates next work item without advancing workflow until last performer completes; rejection decrements index
- Added runtime selection validation against group membership before advancing
- Extended resolve_performers with alias (reads from workflow.alias_snapshot), sequential, and runtime_selection cases
- Added alias snapshot creation at workflow start from template's alias_set_id
- Wired selected_path and next_performer_id through inbox router -> inbox service -> engine service -> advancement loop

## Task Commits

Each task was committed atomically:

1. **Task 1: Engine service -- routing dispatch, reject flows, sequential/runtime performers, alias resolution** - `04240d6` (feat)
2. **Task 2: Inbox service and router passthrough for selected_path, next_performer_id, and engine reject** - `8b76515` (feat)

## Files Created/Modified
- `src/app/services/engine_service.py` - Routing dispatch, reject_work_item, sequential/runtime performer handling, alias resolution, alias snapshot at start
- `src/app/services/inbox_service.py` - Added selected_path/next_performer_id to complete_inbox_item, rewired reject_inbox_item to delegate to engine
- `src/app/routers/inbox.py` - Pass selected_path and next_performer_id from request to service
- `src/app/routers/workflows.py` - Pass selected_path and next_performer_id from request to engine
- `tests/test_inbox.py` - Updated test_reject_work_item to expect 400 when no reject flow defined (D-03)

## Decisions Made
- Reject flow execution tokens placed as immediately consumed since the target activity is manually activated inline (not via the queue)
- selected_path is cleared after the first queue iteration to prevent it from affecting auto-completing activities (start/end)
- Sequential rejection at index 0 raises ValueError rather than following reject flows -- these are separate mechanisms
- Existing reject test updated to expect error per D-03 (reject denied when no reject flow exists)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated existing reject test for D-03 compliance**
- **Found during:** Task 2 (inbox service/router passthrough)
- **Issue:** Existing test_reject_work_item expected 200 on reject, but the template has no reject flows. Per D-03, rejection without reject flows is now correctly denied.
- **Fix:** Renamed to test_reject_work_item_no_reject_flow and updated assertion to expect 400 with "No reject flow" error message
- **Files modified:** tests/test_inbox.py
- **Verification:** All 161 tests pass
- **Committed in:** 8b76515 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Necessary test update for correct D-03 behavior. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all engine logic is fully wired with actual routing dispatch, reject flow traversal, and performer resolution.

## Next Phase Readiness
- Engine fully implements all 3 routing types, reject flows, sequential/runtime performers, and alias resolution
- Plan 06-03 can now add comprehensive tests for all these behaviors
- All 161 existing tests pass with zero regressions

---
*Phase: 06-advanced-routing-alias-sets*
*Completed: 2026-03-31*
