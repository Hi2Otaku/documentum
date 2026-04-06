---
phase: 20-document-renditions
plan: 03
title: "Rendition Frontend UI"
subsystem: frontend/documents
tags: [renditions, frontend, ui, react-query]
dependency_graph:
  requires: ["20-01", "20-02"]
  provides: ["rendition-status-ui", "pdf-download-ui", "rendition-retry-ui"]
  affects: ["document-detail-panel", "document-list"]
tech_stack:
  added: []
  patterns: ["refetchInterval polling", "useMutation for retry", "file-type icon column"]
key_files:
  created:
    - frontend/src/components/documents/RenditionStatusBadge.tsx
  modified:
    - frontend/src/api/documents.ts
    - frontend/src/components/documents/VersionHistoryList.tsx
    - frontend/src/components/documents/DocumentTable.tsx
decisions:
  - "Used simpler file-type icon column in DocumentTable instead of per-row thumbnail queries to avoid N+1 query issues"
  - "Actual thumbnail rendering deferred to VersionHistoryList where renditions are already fetched per version"
metrics:
  duration: "1m 25s"
  completed: "2026-04-06"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 4
---

# Phase 20 Plan 03: Rendition Frontend UI Summary

Frontend rendition status badges with PDF download, retry actions, auto-polling for pending renditions, and file-type icons in the document table.

## What Was Done

### Task 1: Rendition API client and RenditionStatusBadge component (7454db6)
- Added `RenditionResponse` interface, `fetchRenditions`, `renditionDownloadUrl`, `retryRendition`, and `thumbnailUrl` to `frontend/src/api/documents.ts`
- Created `RenditionStatusBadge` component showing pending (spinning loader), ready (checkmark), and failed (X icon) states with appropriate Badge variants

### Task 2: Version history rendition display and document table thumbnails (891c7ff)
- Extended `VersionHistoryList` with per-version rendition queries using `fetchRenditions`
- Added `refetchInterval` that polls every 3 seconds while any rendition is pending
- PDF download button appears when rendition is ready (uses fetch+blob for auth)
- Retry button appears when rendition has failed, using `useMutation` with query invalidation
- Added `FileTypeIcon` component to `DocumentTable` showing content-type-aware icons (image, PDF, spreadsheet, generic file) as the first column

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None - all components are wired to real API endpoints and will display live data when the backend rendition pipeline (Plan 01/02) is running.

## Self-Check: PASSED

- All 4 files exist on disk
- Commits 7454db6 and 891c7ff verified in git log
