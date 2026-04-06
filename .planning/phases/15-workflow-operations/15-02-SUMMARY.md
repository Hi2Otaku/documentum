---
phase: 15-workflow-operations
plan: 02
subsystem: ui
tags: [react, tanstack-table, workflows, admin-controls, split-pane]

requires:
  - phase: 15-01
    provides: "Workflow API client, types, WorkflowStateBadge, WorkflowEmptyState"
provides:
  - "WorkflowTable with 5-column TanStack Table, pagination, filters, row selection"
  - "WorkflowDetailPanel with metadata, tabs, admin actions, process variables"
  - "AdminActionBar with halt/resume/terminate buttons (admin-only)"
  - "TerminateDialog with double-confirmation requiring TERMINATE input"
  - "WorkflowVariablesList displaying process variable names, types, and values"
  - "WorkflowsPage split-pane layout replacing placeholder"
affects: [15-03]

tech-stack:
  added: []
  patterns: ["Split-pane workflow page mirroring Documents/Inbox pattern", "Admin-only action bar with auth store check", "Double-confirmation destructive dialog"]

key-files:
  created:
    - frontend/src/components/workflows/WorkflowTable.tsx
    - frontend/src/components/workflows/WorkflowVariablesList.tsx
    - frontend/src/components/workflows/AdminActionBar.tsx
    - frontend/src/components/workflows/TerminateDialog.tsx
    - frontend/src/components/workflows/WorkflowDetailPanel.tsx
  modified:
    - frontend/src/pages/WorkflowsPage.tsx

key-decisions:
  - "Template/state filters shown only for admin users in filter bar"
  - "Client-side supervisor_id filtering for regular users"
  - "wizardOpen state prepared for Plan 03 StartWorkflowDialog integration"

patterns-established:
  - "Admin-only UI: useAuthStore isSuperuser check with conditional rendering"
  - "Double-confirmation dialog: require exact string input before enabling destructive action"

requirements-completed: [WF-02, WF-03]

duration: 3min
completed: 2026-04-06
---

# Phase 15 Plan 02: Workflow Instance Table & Admin Controls Summary

**Split-pane WorkflowsPage with paginated instance table, detail panel with metadata/variables, and admin halt/resume/terminate controls with double-confirmation**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-06T10:14:26Z
- **Completed:** 2026-04-06T10:17:12Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

### Task 1: WorkflowTable, WorkflowVariablesList, AdminActionBar, TerminateDialog
- Created WorkflowTable with 5 columns (Name, Template, State, Started By, Started) using TanStack Table
- Template and state filter dropdowns in filter bar (admin-only)
- Pagination footer with Previous/Next buttons
- Selected row highlighting with `bg-accent border-l-[3px] border-primary`
- WorkflowVariablesList displaying variable name, type badge, and value in monospace
- AdminActionBar with halt/resume/terminate buttons gated by isSuperuser
- TerminateDialog requiring user to type "TERMINATE" before confirming

### Task 2: WorkflowDetailPanel and WorkflowsPage
- WorkflowDetailPanel with header (name + state badge), admin actions, tabs (Details/Progress)
- Details tab: metadata card (template, started by, started, completed) + process variables
- Progress tab: placeholder for Plan 03 graph
- WorkflowsPage: split-pane layout matching Documents/Inbox pattern
- Admin path uses fetchWorkflowsAdmin with server-side template/state filters
- Regular user path uses fetchWorkflows with client-side supervisor_id filtering
- Start Workflow button sets wizardOpen state (dialog wired in Plan 03)

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

| File | Location | Stub | Resolution |
|------|----------|------|------------|
| WorkflowDetailPanel.tsx | Progress tab | "Progress graph coming in Plan 03" placeholder | Plan 03 will add WorkflowProgressGraph |
| WorkflowsPage.tsx | wizardOpen state | State variable set but no dialog rendered | Plan 03 will add StartWorkflowDialog |
| WorkflowDetailPanel.tsx | Header | process_template_id.slice(0,8) as name | Will be enriched by template lookup in Plan 03 |

## Self-Check: PASSED
