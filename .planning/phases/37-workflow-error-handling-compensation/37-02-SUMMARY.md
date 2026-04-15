---
phase: 37-workflow-error-handling-compensation
plan: "02"
subsystem: workflow-error-ui
tags: [error-handling, compensation, retry, skip, frontend, operator-ui]
dependency_graph:
  requires: [37-01]
  provides: [error-display-ui, compensation-trigger-ui]
  affects: [workflow-operations-page]
tech_stack:
  added: []
  patterns: [useMutation-with-toast, collapsible-details, error-card-pattern]
key_files:
  created:
    - frontend/src/components/workflows/ActivityErrorPanel.tsx
  modified:
    - src/app/routers/workflows.py
    - src/app/schemas/workflow.py
    - frontend/src/api/workflows.ts
    - frontend/src/components/workflows/WorkflowDetailPanel.tsx
    - frontend/src/components/workflows/AdminActionBar.tsx
decisions:
  - Used native button toggle for collapsible error details (no Collapsible shadcn component available)
  - Placed ActivityErrorPanel before Process Variables in details tab for visibility
metrics:
  duration: 2min
  completed: 2026-04-15T05:47:00Z
  tasks_completed: 2
  tasks_total: 2
  files_changed: 6
---

# Phase 37 Plan 02: Error Display UI and Operator Actions Summary

Operator-facing error UI with retry, skip, and compensation controls integrated into the workflow operations page.

## What Was Built

### Task 1: Compensation endpoint + frontend API functions
- Added `POST /{workflow_id}/compensate` endpoint to workflows router (admin-only, calls `engine_service.trigger_compensation`)
- Added `error_message` and `error_details` fields to `ActivityInstanceResponse` schema
- Added `retryActivity`, `skipActivity`, `triggerCompensation` functions to frontend API client
- Fixed skip endpoint to handle manual activities (method_name fallback to "manual_skip")

### Task 2: ActivityErrorPanel component + integration
- Created `ActivityErrorPanel` component that filters activities in "error" state
- Each errored activity shows: AlertTriangle icon, Error badge, error_message text, collapsible error_details JSON
- Retry button (RefreshCw icon) resets activity to ACTIVE state
- Skip button (SkipForward icon) marks activity COMPLETE and advances workflow
- Both use useMutation with toast feedback and query invalidation
- Integrated into WorkflowDetailPanel details tab (above Process Variables)
- Added Compensate button (Undo icon) to AdminActionBar, visible for running/failed workflows

## Commits

| # | Hash | Message |
|---|------|---------|
| 1 | f5b08b2 | feat(37-02): add compensation endpoint and retry/skip/compensate API functions |
| 2 | 27e5c46 | feat(37-02): ActivityErrorPanel with retry/skip and Compensate button |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing functionality] Added error_message/error_details to ActivityInstanceResponse schema**
- **Found during:** Task 1
- **Issue:** Schema lacked error fields needed by frontend to display error details
- **Fix:** Added `error_message: str | None` and `error_details: dict | None` to ActivityInstanceResponse
- **Files modified:** src/app/schemas/workflow.py

**2. [Rule 1 - Bug] Fixed skip endpoint method_name for manual activities**
- **Found during:** Task 1
- **Issue:** Skip endpoint assumed method_name exists (auto activities only); manual activities have None
- **Fix:** Added fallback to "manual_skip" when method_name is None
- **Files modified:** src/app/routers/workflows.py

**3. [Rule 3 - Blocking] No Collapsible shadcn component**
- **Found during:** Task 2
- **Issue:** Plan specified shadcn Collapsible but component not installed in project
- **Fix:** Used native button toggle with useState for expand/collapse behavior
- **Files modified:** frontend/src/components/workflows/ActivityErrorPanel.tsx

## Known Stubs

None -- all components are wired to real API endpoints.

## Self-Check: PASSED
