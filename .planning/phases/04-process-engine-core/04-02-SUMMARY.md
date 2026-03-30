---
phase: 04-process-engine-core
plan: 02
subsystem: api
tags: [fastapi, sqlalchemy, workflow-engine, petri-net, token-routing]

# Dependency graph
requires:
  - phase: 04-process-engine-core/01
    provides: "ExecutionToken model, ActivityState enum, workflow schemas, expression evaluator"
  - phase: 03-workflow-templates
    provides: "ProcessTemplate CRUD, validation, installation, template_service"
provides:
  - "Core process engine service with start_workflow, complete_work_item, advancement loop"
  - "Workflow lifecycle HTTP endpoints (7 routes at /api/v1/workflows)"
  - "Token-based AND-join/OR-join activation logic"
  - "State transition enforcement for workflow and activity states"
affects: [04-process-engine-core/03, 05-work-queues, 06-advanced-routing, 09-bam-dashboards]

# Tech tracking
tech-stack:
  added: []
  patterns: [token-based-petri-net, iterative-advancement-loop, state-transition-maps]

key-files:
  created:
    - src/app/services/engine_service.py
    - src/app/routers/workflows.py
  modified:
    - src/app/main.py

key-decisions:
  - "Iterative queue-based advancement loop (queue.pop(0)) instead of recursion for stack safety"
  - "OR-join double-activation guard checks DORMANT state before activating to prevent duplicate work items"
  - "State transition enforced via WORKFLOW_TRANSITIONS and ACTIVITY_TRANSITIONS sets with _enforce helpers"
  - "complete_work_item reloads full template and rebuilds template_to_instance mapping for correctness"

patterns-established:
  - "Engine service pattern: start_workflow creates instance + advances; complete_work_item advances from activity"
  - "Token placement + consumption: tokens created on flow traversal, consumed when target activates"
  - "Performer override: dict[activity_template_id_str, user_id_str] checked before template performer_id"

requirements-completed: [EXEC-01, EXEC-02, EXEC-03, EXEC-04, EXEC-05, EXEC-06, EXEC-07, EXEC-12]

# Metrics
duration: 3min
completed: 2026-03-30
---

# Phase 4 Plan 2: Engine Service & Router Summary

**Token-based Petri-net process engine with iterative advancement loop, AND/OR-join routing, and 7 workflow lifecycle HTTP endpoints**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-30T14:27:07Z
- **Completed:** 2026-03-30T14:30:08Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Core engine service (~500 lines) implementing workflow instantiation, token-based advancement, and work item creation
- Iterative queue-based advancement loop with AND-join (all tokens required) and OR-join (first token fires) support
- 7 workflow lifecycle endpoints wired into main.py at /api/v1/workflows
- State transition enforcement via transition maps for both workflow and activity states

## Task Commits

Each task was committed atomically:

1. **Task 1: Create engine service with instantiation, advancement, and token management** - `a55b6d0` (feat)
2. **Task 2: Create workflow router and register in main.py** - `84359ac` (feat)

## Files Created/Modified
- `src/app/services/engine_service.py` - Core process engine: start_workflow, complete_work_item, advancement loop, token management, query functions
- `src/app/routers/workflows.py` - 7 HTTP endpoints for workflow lifecycle (start, list, detail, work-items, complete, variables CRUD)
- `src/app/main.py` - Added workflows router registration

## Decisions Made
- Iterative queue-based loop (queue.pop(0)) chosen over recursion for stack safety on deep workflow graphs (per D-03)
- OR-join double-activation guard: check target.state == ActivityState.DORMANT before activating to prevent duplicate work items when multiple branches arrive
- State transitions enforced as sets of valid (from, to) tuples -- ValueError raised on invalid transitions
- complete_work_item fully reloads template and rebuilds activity instance mapping to ensure fresh state after variable updates

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Engine service and router ready for integration testing in Plan 03
- All 99 existing tests continue to pass
- start_workflow, complete_work_item, and query functions available for import

## Self-Check: PASSED

All files exist. All commit hashes verified.

---
*Phase: 04-process-engine-core*
*Completed: 2026-03-30*
