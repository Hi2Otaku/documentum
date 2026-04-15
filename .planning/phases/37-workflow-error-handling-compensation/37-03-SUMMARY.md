---
phase: 37-workflow-error-handling-compensation
plan: 03
subsystem: frontend-designer
tags: [workflow, error-handling, compensation, designer-ui]
dependency_graph:
  requires: [37-01]
  provides: [designer-error-handler-ui, designer-compensation-ui]
  affects: [PropertiesPanel, useSaveTemplate, DesignerPage, designer.ts]
tech_stack:
  added: []
  patterns: [self-referential-fk-resolution, second-pass-save]
key_files:
  created: []
  modified:
    - frontend/src/types/designer.ts
    - frontend/src/components/designer/PropertiesPanel.tsx
    - frontend/src/hooks/useSaveTemplate.ts
    - frontend/src/pages/DesignerPage.tsx
decisions:
  - Used second-pass update pattern for self-referential FK resolution (error_handler_activity_id and compensation_activity_id reference sibling activities in same template)
  - Eligible activity list excludes current node, start, and end activity types
metrics:
  duration: 1.5min
  completed: 2026-04-15
  tasks_completed: 1
  tasks_total: 1
  files_modified: 4
---

# Phase 37 Plan 03: Designer UI - Error Handler & Compensation Activity Selection Summary

Error handler and compensation activity dropdowns in the visual workflow designer PropertiesPanel, with second-pass save for self-referential FK resolution.

## What Was Done

### Task 1: Designer properties panel dropdowns + save hook + node conversion

1. **designer.ts**: Added `errorHandlerActivityId` and `compensationActivityId` optional fields to `ActivityNodeData` interface.

2. **PropertiesPanel.tsx**: Added `ErrorHandlingSection` component displayed for manual and auto activity types. Contains two dropdowns (Error Handler Activity, Compensation Activity) that list all other non-start/non-end activities in the current template. Uses ShieldAlert-style SVG icon.

3. **useSaveTemplate.ts**: Added `error_handler_activity_id: null` and `compensation_activity_id: null` to both create and update activity payloads (first pass). Added a second pass after all activities are created/updated that resolves frontend node IDs to backend IDs via `newIdMap` and issues update calls for activities that have error handler or compensation references set.

4. **DesignerPage.tsx**: Updated `activitiesToNodes` to read `error_handler_activity_id` and `compensation_activity_id` from backend response and map to `errorHandlerActivityId` and `compensationActivityId` in node data.

## Deviations from Plan

None - plan executed exactly as written.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 618b8d4 | feat(37-03): add error handler and compensation activity selection to workflow designer |

## Known Stubs

None - all fields are fully wired from backend load through to save with proper ID resolution.

## Verification

All 8 acceptance criteria passed (grep checks for required identifiers in all target files).
