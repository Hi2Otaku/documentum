---
phase: 13-inbox-work-items
plan: 02
subsystem: frontend-inbox
tags: [inbox-table, detail-panel, comments, split-pane, tanstack-table]
dependency_graph:
  requires: [13-01]
  provides: [inbox-page, inbox-table, detail-panel, comment-ui]
  affects: [13-03]
tech_stack:
  added: []
  patterns: [split-pane-layout, tanstack-table-server-pagination, useMutation-toast-pattern]
key_files:
  created:
    - frontend/src/components/inbox/InboxTable.tsx
    - frontend/src/components/inbox/InboxDetailPanel.tsx
    - frontend/src/components/inbox/CommentList.tsx
    - frontend/src/components/inbox/CommentCompose.tsx
  modified:
    - frontend/src/pages/InboxPage.tsx
decisions:
  - "State filter uses 'all' as default value instead of empty string since Radix Select requires non-empty values"
  - "Server-side pagination only (no client-side sorting) via getCoreRowModel without getSortedRowModel"
  - "Complete/Reject/Delegate buttons rendered but non-functional until Plan 03 wires dialogs"
metrics:
  duration: 3min
  completed: 2026-04-06
---

# Phase 13 Plan 02: Inbox Table, Detail Panel & Comments Summary

Split-pane inbox page with TanStack Table (5 columns, state filter, pagination), detail panel with workflow context card and acquire action, and comment list/compose with mutation feedback

## What Was Done

### Task 1: InboxTable with TanStack Table, Filtering, and Pagination
- Created `frontend/src/components/inbox/InboxTable.tsx` with 217 lines
- 5 column definitions using createColumnHelper: task (activity.name), workflow (template_name with truncate), priority (PriorityIcon centered), state (WorkItemStateBadge), created (date formatted)
- State filter bar (48px height, bg-secondary/50) with shadcn Select: All, Available, Acquired, Delegated
- Pagination footer with Previous/Next buttons and "Page X of Y" indicator
- Skeleton loading state with 5 rows
- InboxEmptyState for empty list
- Selected row highlighting with bg-accent and border-l-[3px] border-primary

### Task 2: InboxDetailPanel, CommentList, CommentCompose, and InboxPage
- Created `CommentList` displaying comments with Avatar initials, content, and timestamps
- Created `CommentCompose` with Textarea ("Write a comment..."), useMutation calling addComment, and toast.success/toast.error feedback
- Created `InboxDetailPanel` with: empty state ("Select a work item"), loading skeletons, header with activity name + state badge + priority icon, workflow context Card (template, workflow state, assigned to, due date, created), instructions section, action buttons (Acquire for available items; Complete/Reject/Delegate for acquired items), Separator, and Comments section
- Acquire button wired with useMutation calling acquireWorkItem, invalidates inbox queries, shows toast.success("Task acquired")
- Replaced InboxPage placeholder with full split-pane layout: Tabs (My Inbox / Queues), left pane (flex-1 min-w-[400px]) with InboxTable, right pane (w-[420px] border-l) with InboxDetailPanel
- Queues tab shows InboxEmptyState placeholder
- Responsive: detail panel hidden below lg breakpoint with hidden lg:block
- State filter change and page change both reset selection and page

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 41855f4 | feat(13-02): build InboxTable with TanStack Table, filtering, and pagination |
| 2 | ed083ed | feat(13-02): build InboxDetailPanel, CommentList, CommentCompose, and wire InboxPage |

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

- **Complete button** (`InboxDetailPanel.tsx`, line ~148): Button exists but has no onClick handler. Plan 03 wires with dialog.
- **Reject button** (`InboxDetailPanel.tsx`, line ~151): Button exists but has no onClick handler. Plan 03 wires with dialog.
- **Delegate button** (`InboxDetailPanel.tsx`, line ~154): Button exists but has no onClick handler. Plan 03 wires with dialog.
- **Queues tab** (`InboxPage.tsx`, line ~82): Shows InboxEmptyState placeholder. Plan 03 fills in queue browsing.

These are all intentional and will be resolved by Plan 03 as documented in the plan.

## Verification

- TypeScript compiles cleanly (`npx tsc --noEmit` passes with no errors)
- InboxPage no longer contains "Coming Soon"
- Split-pane layout: table left (flex-1 min-w-[400px]), detail right (w-[420px] border-l)
- Tabs render: "My Inbox" and "Queues"
- State filter Select with 4 options (All, Available, Acquired, Delegated)
- Table renders 5 columns (task, workflow, priority, state, created)
- Pagination renders at table footer
- Detail panel shows "Select a work item" when nothing selected
- Acquire button visible for available items with toast feedback
- Comments section renders with CommentList and CommentCompose

## Self-Check: PASSED

All 5 files found. Both commits (41855f4, ed083ed) verified in git log.
