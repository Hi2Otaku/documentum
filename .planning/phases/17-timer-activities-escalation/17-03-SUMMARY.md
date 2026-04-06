---
phase: 17-timer-activities-escalation
plan: "03"
subsystem: frontend-designer
tags: [timer, escalation, designer-ui, properties-panel]
dependency_graph:
  requires: [17-01]
  provides: [designer-deadline-ui]
  affects: [workflow-designer, activity-templates]
tech_stack:
  added: []
  patterns: [camelCase-snakeCase-mapping, conditional-panel-sections]
key_files:
  created: []
  modified:
    - frontend/src/types/designer.ts
    - frontend/src/types/workflow.ts
    - frontend/src/api/templates.ts
    - frontend/src/hooks/useSaveTemplate.ts
    - frontend/src/pages/DesignerPage.tsx
    - frontend/src/components/designer/PropertiesPanel.tsx
decisions:
  - Timer fields visible for both manual and auto activity types
  - Warning threshold defaults to auto (25% of deadline) via placeholder hint
metrics:
  duration: 2m
  completed: "2026-04-06T16:34:23Z"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 6
---

# Phase 17 Plan 03: Designer Deadline/Escalation UI Summary

Deadline duration, escalation action, and warning threshold fields added to the workflow designer PropertiesPanel, with full save/load cycle mapping between camelCase frontend and snake_case backend.

## Task Results

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add deadline/escalation fields to types and API | 63e7deb | designer.ts, workflow.ts, templates.ts, useSaveTemplate.ts, DesignerPage.tsx |
| 2 | Add Timer & Escalation section to PropertiesPanel | 1750fc0 | PropertiesPanel.tsx |

## What Was Built

### Task 1: Type & API Integration
- Added `expectedDurationHours`, `escalationAction`, `warningThresholdHours` to `ActivityNodeData` interface
- Added `expected_duration_hours`, `escalation_action`, `warning_threshold_hours` to `ActivityTemplate` interface
- Extended `addActivity` and `updateActivity` API function signatures with deadline fields
- Added deadline field mapping in `useSaveTemplate.ts` save path (camelCase to snake_case)
- Added deadline field mapping in `DesignerPage.tsx` load/hydrate path (snake_case to camelCase)

### Task 2: PropertiesPanel UI
- Added "Timer & Escalation" section that renders for both `manual` and `auto` activity nodes
- Deadline Duration: number input (hours, step 0.5) with "No deadline" placeholder
- Escalation Action: dropdown with options None / Priority Bump / Reassign to Supervisor / Notify Only
- Warning Threshold: number input with "Auto (25% of deadline)" placeholder
- All fields wire through `updateNodeData` for immediate persistence in designer state

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing type field] Added deadline fields to ActivityTemplate in workflow.ts**
- **Found during:** Task 1
- **Issue:** The plan only mentioned designer.ts and templates.ts, but the ActivityTemplate interface in workflow.ts (used by DesignerPage.tsx hydration) lacked the 3 deadline fields, which would cause TypeScript errors on `a.expected_duration_hours`
- **Fix:** Added `expected_duration_hours`, `escalation_action`, `warning_threshold_hours` to ActivityTemplate interface
- **Files modified:** frontend/src/types/workflow.ts
- **Commit:** 63e7deb

**2. [Rule 2 - Missing load path] Added hydration mapping in DesignerPage.tsx**
- **Found during:** Task 1
- **Issue:** The plan's step 4 directed adding load mapping in useSaveTemplate.ts, but the actual hydration path is in DesignerPage.tsx (activitiesToNodes function)
- **Fix:** Added camelCase mapping in DesignerPage.tsx activitiesToNodes function instead
- **Files modified:** frontend/src/pages/DesignerPage.tsx
- **Commit:** 63e7deb

## Known Stubs

None -- all fields are wired to real data paths (designer state -> save hook -> API -> backend -> load path -> designer state).

## Self-Check: PASSED
