---
phase: 14-document-management
plan: 02
subsystem: frontend-documents
tags: [upload, drag-drop, table, pagination, filters, split-pane]
dependency_graph:
  requires: [14-01]
  provides: [document-drop-zone, document-table, documents-page]
  affects: [14-03]
tech_stack:
  added: []
  patterns: [sequential-upload, client-side-filter, debounced-search, split-pane-layout]
key_files:
  created:
    - frontend/src/components/documents/DocumentDropZone.tsx
    - frontend/src/components/documents/UploadProgressItem.tsx
    - frontend/src/components/documents/DocumentTable.tsx
  modified:
    - frontend/src/pages/DocumentsPage.tsx
decisions:
  - "State filter is client-side (API does not support lifecycle_state param)"
  - "Title/author filters debounced at 300ms with useEffect+setTimeout pattern"
  - "Upload progress uses indeterminate style (no real progress events from fetch)"
metrics:
  duration: 3m
  completed: "2026-04-06T07:55:00Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 3
  files_modified: 1
---

# Phase 14 Plan 02: Documents Page with Upload and Browsing Summary

Drag-and-drop upload zone with sequential multi-file upload, filterable paginated document table with 6 columns, and split-pane layout matching InboxPage pattern.

## Task Results

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | DocumentDropZone and UploadProgressItem | 6f70ed1 | DocumentDropZone.tsx, UploadProgressItem.tsx |
| 2 | DocumentTable and DocumentsPage | 2f04b81 | DocumentTable.tsx, DocumentsPage.tsx |

## What Was Built

### Task 1: DocumentDropZone and UploadProgressItem
- **UploadProgressItem**: Compact row (h-9) showing filename, Progress bar, and success/error icon
- **DocumentDropZone**: Dashed-border drop zone (120px) accepting drag-and-drop and file picker
- Sequential upload loop (for loop, not Promise.all) with per-file status tracking
- Toast notifications via sonner (success per file, error with message)
- Auto-dismiss progress list after 3 seconds, then return to default drop zone view
- Author defaults from authStore username

### Task 2: DocumentTable and DocumentsPage
- **DocumentTable**: TanStack Table with 6 columns (Title with filename subtitle, Author, State badge, Version, Lock indicator, Updated relative date)
- Filter bar: title Input, author Input, lifecycle state Select (All/Draft/Review/Approved/Archived)
- Client-side state filter (filters array, not sent to API)
- Skeleton loading state (5 rows), DocumentEmptyState when no results
- Pagination footer with page info and Previous/Next buttons
- **DocumentsPage**: Full page replacing placeholder, with drop zone at top and split-pane below
- Debounced title/author filters (300ms) via useEffect+setTimeout
- Filter/page changes reset selection and page number
- Detail panel placeholder with "Select a document" text (Plan 03 will replace)

## Deviations from Plan

None - plan executed exactly as written.

## Decisions Made

1. **Client-side state filter**: The API does not support a lifecycle_state query parameter, so state filtering happens in the component by filtering the documents array.
2. **Debounce pattern**: Used useEffect+setTimeout rather than a custom hook, keeping it simple and dependency-free.
3. **Indeterminate upload progress**: Since fetch API does not provide upload progress events, the Progress bar shows indeterminate state during upload and 100% on completion.

## Known Stubs

- Detail panel in DocumentsPage shows placeholder text "Select a document" -- this is intentional and will be replaced by DocumentDetailPanel in Plan 03.

## Verification

- `tsc --noEmit` passes cleanly (0 errors)
- All 3 created files and 1 modified file verified
- DocumentsPage renders at /documents route (already wired from Phase 12)
- Drop zone handles drag-and-drop and file picker
- Table has 6 columns with filters and pagination
- Split-pane layout matches InboxPage pattern

## Self-Check: PASSED
