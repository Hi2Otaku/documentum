---
phase: 41-import-export
plan: 02
subsystem: ui
tags: [react, import-export, drag-and-drop, tanstack-query, shadcn]

requires:
  - phase: 41-import-export/01
    provides: Backend API endpoints for import/export operations
provides:
  - Import/Export API client with multipart upload support
  - ExportDialog component for browse page integration
  - ImportExportPage with file upload, conflict strategy, and job history
  - Admin route and sidebar navigation for Import/Export
affects: [browse-page, admin-navigation]

tech-stack:
  added: []
  patterns: [drag-and-drop file upload zone, conditional polling for job status, blob download via hidden anchor]

key-files:
  created:
    - frontend/src/api/importExport.ts
    - frontend/src/components/browse/ExportDialog.tsx
    - frontend/src/pages/ImportExportPage.tsx
  modified:
    - frontend/src/App.tsx
    - frontend/src/components/layout/SidebarNav.tsx
    - frontend/src/pages/BrowsePage.tsx

key-decisions:
  - "Native HTML radio buttons instead of shadcn RadioGroup (component not installed) for conflict strategy selection"
  - "Drag-and-drop zone uses styled div with dragover/dragleave/drop handlers rather than external library"
  - "Expandable row pattern for job detail results in job history table"

patterns-established:
  - "Blob download pattern: fetch with auth headers, create blob URL, trigger via hidden anchor, revoke URL"
  - "FormData upload without Content-Type header to let browser set multipart boundary"

requirements-completed: [IOEX-01, IOEX-02, IOEX-03, IOEX-04]

duration: 2.5min
completed: 2026-04-15
---

# Phase 41 Plan 02: Import/Export Frontend Summary

**Full admin UI for document import/export with drag-and-drop ZIP upload, conflict strategy selection, and job history with conditional polling and download**

## What Was Built

### Task 1: API Client + Export Dialog + Import/Export Page
- **API client** (`importExport.ts`): Full client matching bulk.ts patterns with authHeaders, handle401, query key factory. Supports export (JSON POST), import (FormData multipart POST), job listing, single job fetch, and authenticated blob download.
- **ExportDialog** (`ExportDialog.tsx`): Modal dialog with ACL and relationship inclusion checkboxes, item count summary, mutation-driven export trigger with loading state.
- **ImportExportPage** (`ImportExportPage.tsx`): Two-section admin page. Import section has drag-and-drop file zone, target folder input, Skip/Overwrite/Rename conflict strategy radio group. Job history section shows all import/export jobs with type/status badges, expandable per-item results, download button for completed exports, and conditional 3-second polling for active jobs.

### Task 2: Route + Nav + Browse Integration
- Route `/admin/import-export` registered under AdminRoute in App.tsx
- Package icon nav item added to admin section in SidebarNav.tsx
- Export button in BrowsePage header toolbar, enabled when documents are selected or a folder is active
- ExportDialog rendered in BrowsePage, receiving selected document IDs and current folder ID

## Deviations from Plan

None - plan executed exactly as written.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | c3e10a9 | API client, export dialog, and import/export admin page |
| 2 | 30384bf | Route registration, nav item, and browse page export wiring |

## Self-Check: PASSED
