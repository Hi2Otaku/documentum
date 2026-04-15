---
phase: 37-workflow-error-handling-compensation
plan: 01
subsystem: workflow-engine
tags: [error-handling, compensation, workflow, sqlalchemy, fastapi]

requires:
  - phase: 36-identity-sso
    provides: latest migration head (phase36_001)
provides:
  - Error handler and compensation columns on ActivityTemplate
  - Error tracking fields on ActivityInstance (error_message, error_details, completed_order)
  - handle_activity_error function for activating error handler activities
  - execute_compensation function for reverse-order compensation execution
  - trigger_compensation API-callable entry point
  - Auto-activity integration with error handler system
affects: [37-02, 37-03, workflow-api, workflow-designer]

tech-stack:
  added: []
  patterns: [error-handler-fk-pattern, compensation-reverse-ordering, completed-order-tracking]

key-files:
  created:
    - alembic/versions/phase37_001_error_handlers.py
  modified:
    - src/app/models/workflow.py
    - src/app/schemas/template.py
    - src/app/schemas/workflow.py
    - src/app/services/engine_service.py
    - src/app/tasks/auto_activity.py
    - frontend/src/types/workflow.ts
    - frontend/src/types/designer.ts

key-decisions:
  - "Self-referential FKs on activity_templates for error_handler and compensation activity links"
  - "completed_order tracked incrementally via max+1 query in _advance_from_activity"
  - "Compensation halts workflow (HALTED state) requiring operator to resume or terminate"

patterns-established:
  - "Error handler pattern: activity template points to another activity template as its error handler via FK"
  - "Compensation ordering: completed_order integer assigned at completion time, used for reverse traversal"

requirements-completed: [WFERR-01, WFERR-02, WFERR-03]

duration: 3min
completed: 2026-04-15
---

# Phase 37 Plan 01: Error Handler and Compensation Data Model + Engine Logic Summary

**Error handler activation on activity failure with reverse-order compensation execution via completed_order tracking**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-15T05:38:26Z
- **Completed:** 2026-04-15T05:41:30Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- ActivityTemplate now has error_handler_activity_id and compensation_activity_id self-referential FKs
- ActivityInstance tracks error_message, error_details, and completed_order for failure tracking and compensation ordering
- Engine functions handle_activity_error, execute_compensation, trigger_compensation added
- Auto-activity task integrates with error handler system after max retries exceeded

## Task Commits

Each task was committed atomically:

1. **Task 1: DB migration + model + schema updates** - `6929b51` (feat)
2. **Task 2: Engine error handler execution and compensation logic** - `c35c27b` (feat)

## Files Created/Modified
- `alembic/versions/phase37_001_error_handlers.py` - Migration adding error handler/compensation columns
- `src/app/models/workflow.py` - ActivityTemplate and ActivityInstance model updates
- `src/app/schemas/template.py` - Create/Update/Response schemas with new fields
- `src/app/schemas/workflow.py` - ActivityInstanceResponse with error_message/error_details
- `src/app/services/engine_service.py` - Error handler, compensation, and completed_order logic
- `src/app/tasks/auto_activity.py` - Error handler integration in auto activity failure paths
- `frontend/src/types/workflow.ts` - ActivityTemplate interface with new fields
- `frontend/src/types/designer.ts` - ActivityNodeData with errorHandlerActivityId/compensationActivityId

## Decisions Made
- Self-referential FKs on activity_templates for error handler and compensation links (same table)
- completed_order uses max+1 query pattern for monotonic ordering within a workflow
- Compensation sets workflow to HALTED state (operator must resume or terminate)
- Error handler in auto_activity uses separate session to avoid rollback contamination

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Error handler and compensation data model and engine logic complete
- Ready for Plan 02 (API endpoints for error handler and compensation) and Plan 03 (frontend UI)
- All schemas and types already updated for API consumption

---
*Phase: 37-workflow-error-handling-compensation*
*Completed: 2026-04-15*
