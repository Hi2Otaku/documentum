---
phase: 39-advanced-join-semantics
plan: 02
subsystem: workflow-designer-ui
tags: [join-semantics, designer, properties-panel, react]

requires:
  - phase: 39-advanced-join-semantics
    plan: 01
    provides: backend TriggerType enum with n_of_m_join, cancelling_join, timeout_join
provides:
  - advanced join configuration UI in workflow designer PropertiesPanel
affects:
  - frontend/src/components/designer/PropertiesPanel.tsx
  - frontend/src/types/designer.ts
  - frontend/src/types/workflow.ts

tech-stack:
  added: []
  patterns:
    - conditional form fields based on selected join type
    - clear dependent fields on type switch

key-files:
  created: []
  modified:
    - frontend/src/components/designer/PropertiesPanel.tsx
    - frontend/src/types/designer.ts
    - frontend/src/types/workflow.ts

decisions:
  - Threshold input max bound to incomingEdgeCount for visual feedback
  - Amber warning text for cancelling join to alert designers of destructive behavior
  - Clear joinThreshold and joinTimeoutHours when switching to AND/OR join types

metrics:
  duration: 1min
  completed: "2026-04-15T06:14:00Z"
  tasks_completed: 2
  tasks_total: 2
---

# Phase 39 Plan 02: Advanced Join UI in Workflow Designer Summary

Extended the workflow designer PropertiesPanel with 5 join types (AND, OR, N-of-M, Cancelling, Timeout) and conditional threshold/timeout input fields.

## What Was Done

### Task 1: Extend PropertiesPanel with advanced join controls (abe4ff6)

1. **Updated type definitions** in `designer.ts` and `workflow.ts`:
   - Extended `TriggerType` union with `n_of_m_join`, `cancelling_join`, `timeout_join`
   - Added `joinThreshold` (number | null) and `joinTimeoutHours` (number | null) to `ActivityNodeData`

2. **Replaced trigger type dropdown** in `PropertiesPanel.tsx`:
   - Old: 2-option dropdown (AND-join, OR-join)
   - New: 5-option dropdown with descriptive labels

3. **Added conditional input fields**:
   - N-of-M and Cancelling joins show a threshold number input (min=1, max=incomingEdgeCount)
   - Cancelling join additionally shows an amber warning about branch cancellation
   - Timeout join shows a timeout hours input (min=0.1, step=0.1)

4. **Cleanup on type switch**: Switching to AND-join or OR-join clears joinThreshold and joinTimeoutHours

### Task 2: Verify advanced join UI (checkpoint:human-verify)

Auto-approved in YOLO mode. TypeScript compiles clean.

## Deviations from Plan

None -- plan executed exactly as written.

## Decisions Made

1. **Threshold max bound to incomingEdgeCount**: Provides visual feedback in the input's max attribute so designers know the valid range.
2. **Amber warning for cancelling join**: Uses `text-amber-600` to alert designers that incomplete branches will be cancelled -- a destructive behavior worth highlighting.
3. **Field cleanup on type switch**: Prevents stale threshold/timeout values from being saved when switching back to basic join types.

## Known Stubs

None -- all fields are wired to `updateNodeData` which persists to template save.

## Self-Check: PASSED
