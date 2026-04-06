---
phase: 15-workflow-operations
plan: "03"
subsystem: frontend-workflows
tags: [wizard-dialog, react-flow, progress-graph, workflow-start, multi-step-form]
dependency_graph:
  requires: [15-01, 15-02]
  provides: [start-workflow-wizard, workflow-progress-graph, phase-15-complete]
  affects: []
tech_stack:
  added: []
  patterns: [multi-step-wizard, read-only-react-flow, state-colored-nodes, dagre-layout]
key_files:
  created:
    - frontend/src/components/workflows/StartWorkflowDialog.tsx
    - frontend/src/components/workflows/WizardStepIndicator.tsx
    - frontend/src/components/workflows/TemplatePickerStep.tsx
    - frontend/src/components/workflows/DocumentAttachStep.tsx
    - frontend/src/components/workflows/VariablesStep.tsx
    - frontend/src/components/workflows/ReviewStep.tsx
    - frontend/src/components/workflows/WorkflowProgressGraph.tsx
  modified:
    - frontend/src/pages/WorkflowsPage.tsx
    - frontend/src/components/workflows/WorkflowDetailPanel.tsx
decisions:
  - "Progress graph uses lightweight inline node components instead of reusing designer nodes (no Handles needed for read-only view)"
  - "Wizard state managed with useState only (no Zustand) per anti-pattern guidance"
metrics:
  duration: 3min
  completed: "2026-04-06T10:21:58Z"
---

# Phase 15 Plan 03: Start Workflow Wizard & Progress Graph Summary

**4-step wizard dialog for starting workflows plus read-only React Flow progress graph with state-colored activity nodes**

## What Was Built

### Task 1: Start Workflow Wizard Dialog (6 components)

- **WizardStepIndicator**: Horizontal step indicator with dots, connector lines, and labels (Template/Documents/Variables/Review). Active, completed, and inactive states with oklch colors.
- **TemplatePickerStep**: Fetches active/installed templates and renders selectable cards with name/description. Loading skeletons, empty state messaging.
- **DocumentAttachStep**: Fetches documents and renders checkbox list for optional attachment. Lifecycle state badges shown.
- **VariablesStep**: Fetches template detail for variable definitions. Renders type-appropriate inputs (Input for string/integer, Switch for boolean). Auto-initializes defaults on load.
- **ReviewStep**: Summary card with template name, document count with titles, and variable name=value pairs in monospace.
- **StartWorkflowDialog**: Container dialog (640px max-width) managing wizard state. Next/Back navigation, step 1 Next disabled until template selected. Launch button calls startWorkflow API, shows toast on success/error, resets state on close.

### Task 2: Progress Graph & Page Wiring (1 component, 2 updates)

- **WorkflowProgressGraph**: Read-only React Flow graph fetching workflow detail and template structure. Builds state map from activity instances. Four inline progress node components (start/end/manual/auto) with state-colored borders (green=complete, blue=active, gray=dormant, amber=paused, red=error). Uses dagre auto-layout (LR direction). No Handle elements, no drag/connect/select interactions.
- **WorkflowsPage**: Wired StartWorkflowDialog with wizardOpen state.
- **WorkflowDetailPanel**: Replaced progress tab placeholder with WorkflowProgressGraph component.

## Deviations from Plan

None - plan executed exactly as written.

## Commits

| # | Hash | Message |
|---|------|---------|
| 1 | 5d271d7 | feat(15-03): add Start Workflow wizard dialog with 4-step form |
| 2 | e6c6302 | feat(15-03): add WorkflowProgressGraph and wire wizard into pages |

## Verification

- TypeScript compilation passes (`npx tsc --noEmit` clean)
- All acceptance criteria met for both tasks
- No stubs or placeholder content remaining

## Known Stubs

None - all components are fully wired to API data sources.
