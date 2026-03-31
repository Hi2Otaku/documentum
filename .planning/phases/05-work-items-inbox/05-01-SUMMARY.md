---
phase: 05-work-items-inbox
plan: 01
subsystem: api
tags: [pydantic, sqlalchemy, workflow-engine, inbox, performer-resolution]

requires:
  - phase: 04-process-engine
    provides: engine_service with workflow advancement, WorkItem model, state transitions
provides:
  - REJECTED enum value on WorkItemState
  - WorkItemComment model with FKs and index
  - Inbox Pydantic schemas with nested activity/workflow/document summaries
  - resolve_performers() for SUPERVISOR/USER/GROUP performer types
  - Multi-work-item creation loop for group performers
  - WORK_ITEM_TRANSITIONS state machine set
affects: [05-work-items-inbox]

tech-stack:
  added: []
  patterns: [performer-resolution-via-match, per-performer-work-item-creation]

key-files:
  created:
    - src/app/schemas/inbox.py
  modified:
    - src/app/models/enums.py
    - src/app/models/workflow.py
    - src/app/services/engine_service.py

key-decisions:
  - "resolve_performers uses lazy import for user_groups to avoid circular dependency"
  - "Group performer type creates one work item per group member for shared inbox"

patterns-established:
  - "Performer resolution: match/case on performer_type string, return list[uuid.UUID]"
  - "Inbox schemas: nested summaries (ActivitySummary, WorkflowSummary, DocumentSummary) for rich cards"

requirements-completed: [INBOX-01, INBOX-07, PERF-01, PERF-02, PERF-03]

duration: 3min
completed: 2026-03-31
---

# Phase 05 Plan 01: Work Items Data Layer and Performer Resolution Summary

**REJECTED work-item state, WorkItemComment model, inbox Pydantic schemas, and resolve_performers() with multi-work-item creation for group performers**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-31T05:59:08Z
- **Completed:** 2026-03-31T06:02:06Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Added REJECTED value to WorkItemState enum for reject flow support
- Created WorkItemComment model with work_item_id FK (indexed), user_id FK, and content Text field
- Built comprehensive inbox Pydantic schemas with nested activity/workflow/document summaries
- Implemented resolve_performers() mapping SUPERVISOR, USER, and GROUP types to user IDs
- Replaced single work-item creation with per-performer loop so group activities create one work item per member
- Added WORK_ITEM_TRANSITIONS state machine set for inbox service state validation

## Task Commits

Each task was committed atomically:

1. **Task 1: Add REJECTED state, WorkItemComment model, and inbox schemas** - `d4fe957` (feat)
2. **Task 2: Add resolve_performers and multi-work-item creation to engine** - `b2a74cb` (feat)

## Files Created/Modified
- `src/app/models/enums.py` - Added REJECTED to WorkItemState enum
- `src/app/models/workflow.py` - Added WorkItemComment model and WorkItem.comments relationship
- `src/app/schemas/inbox.py` - New file with all inbox Pydantic schemas (11 models)
- `src/app/services/engine_service.py` - Added resolve_performers(), WORK_ITEM_TRANSITIONS, multi-work-item creation loop

## Decisions Made
- resolve_performers uses lazy import for user_groups table to avoid circular imports between workflow and user modules
- Group performer type creates one work item per group member (fan-out) rather than a single shared work item
- Unresolved performers create an unassigned work item (performer_id=None) rather than raising an error

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Data layer complete: WorkItemComment model, inbox schemas, performer resolution all ready
- Plans 05-02 (inbox service) and 05-03 (inbox API routes) can proceed
- WORK_ITEM_TRANSITIONS set ready for inbox service state validation
- All 15 existing workflow tests pass unchanged

---
*Phase: 05-work-items-inbox*
*Completed: 2026-03-31*
