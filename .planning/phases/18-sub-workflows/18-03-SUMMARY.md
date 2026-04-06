---
phase: 18-sub-workflows
plan: 03
subsystem: frontend-designer
tags: [sub-workflow, designer, react-flow, frontend]
dependency_graph:
  requires: [18-01]
  provides: [sub-workflow-designer-node]
  affects: [workflow-designer, process-builder]
tech_stack:
  added: []
  patterns: [react-flow-custom-node, properties-panel-conditional-section]
key_files:
  created:
    - frontend/src/components/nodes/SubWorkflowNode.tsx
  modified:
    - frontend/src/types/workflow.ts
    - frontend/src/types/designer.ts
    - frontend/src/components/nodes/index.ts
    - frontend/src/components/designer/NodePalette.tsx
    - frontend/src/components/designer/Canvas.tsx
    - frontend/src/components/designer/PropertiesPanel.tsx
decisions:
  - Purple double-border visual style distinguishes sub-workflow nodes from other activity types
  - Template selector uses simple fetch to /api/templates?state=active (no dedicated hook)
  - Variable mapping stored as Record<string, string> serialized from input rows
metrics:
  duration: 2m
  completed: 2026-04-06
---

# Phase 18 Plan 03: Sub-Workflow Designer Node Summary

SubWorkflowNode component with purple double-border styling, GitBranch icon, template selector dropdown, and variable mapping editor in PropertiesPanel.

## What Was Done

### Task 1: SubWorkflowNode component, type updates, and palette/canvas registration
- Added `sub_workflow` to `ActivityType` union in `workflow.ts` and `designer.ts`
- Added `subTemplateId` and `variableMapping` fields to `ActivityNodeData` interface
- Created `SubWorkflowNode.tsx` with purple double-border styling, GitBranch icon, template link status
- Registered `subWorkflowNode` and `sub_workflow` keys in `nodeTypes` (both aliases)
- Added Sub-Workflow palette item with purple accent and GitBranch icon before End
- Added `subWorkflowNode` entry in `DEFAULT_NODE_DATA` in Canvas
- Fixed MiniMap colors (auto=orange, sub_workflow=purple)
- **Commit:** `5554401`

### Task 2: Properties panel sub-workflow configuration section
- Added purple badge styling for `sub_workflow` activity type
- Created `SubWorkflowConfig` component with template selector dropdown fetching from `/api/templates?state=active`
- Added variable mapping editor with add/remove rows, syncing `Record<string, string>` to node data
- Component renders conditionally only for `sub_workflow` activity type
- **Commit:** `cdfd092`

### Task 3: Visual verification checkpoint
- Auto-approved (YOLO mode). TypeScript compiles cleanly with no errors.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed MiniMap color for auto nodes**
- **Found during:** Task 1
- **Issue:** Auto nodes used purple (#a855f7) in MiniMap but their visual style is orange. Sub-workflow nodes should be purple.
- **Fix:** Changed auto node MiniMap color to orange (#f97316) and assigned purple (#a855f7) to sub_workflow/subWorkflowNode
- **Files modified:** frontend/src/components/designer/Canvas.tsx
- **Commit:** 5554401

## Known Stubs

None. Template selector fetches from the real API endpoint. Variable mapping is fully wired to node data.

## Verification

- TypeScript compilation: PASSED (no errors)
- All acceptance criteria met for both tasks

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 5554401 | SubWorkflowNode component, type updates, palette/canvas registration |
| 2 | cdfd092 | Properties panel sub-workflow config section |

## Self-Check: PASSED
