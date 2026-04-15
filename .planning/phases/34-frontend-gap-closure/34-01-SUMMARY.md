---
phase: 34-frontend-gap-closure
plan: "01"
subsystem: frontend-documents
tags: [lifecycle-filter, acl-management, document-detail]
dependency_graph:
  requires: []
  provides: [lifecycle-state-filter, document-acl-ui]
  affects: [documents-page, document-detail-panel, documents-api]
tech_stack:
  added: []
  patterns: [query-parameter-passthrough, acl-panel-pattern]
key_files:
  created:
    - frontend/src/components/documents/DocumentACLPanel.tsx
  modified:
    - src/app/services/document_service.py
    - src/app/routers/documents.py
    - frontend/src/api/documents.ts
    - frontend/src/pages/DocumentsPage.tsx
    - frontend/src/components/documents/DocumentDetailPanel.tsx
decisions:
  - Used listUsers API for user principal dropdown; group selection uses manual UUID input since no listGroups API exists
metrics:
  duration: 2.5min
  completed: "2026-04-15"
---

# Phase 34 Plan 01: Lifecycle Filter & Document ACL UI Summary

Wired lifecycle_state filter from DocumentsPage dropdown through API to backend query, and created DocumentACLPanel component for managing document-level permissions from the detail panel.

## What Was Done

### Task 1: Lifecycle State Filter (Backend + Frontend)
- Added `lifecycle_state: str | None = None` parameter to `document_service.list_documents`
- Added filter clause `Document.lifecycle_state == lifecycle_state` to base conditions
- Added `lifecycle_state: str | None = Query(None)` to documents router list endpoint
- Added `lifecycle_state?: string` to `DocumentListParams` in frontend API
- Passed `stateFilter` value as `lifecycle_state` parameter in DocumentsPage `fetchDocuments` call
- Added `state` to useQuery queryKey for proper cache invalidation on filter change

**Commit:** `10e274c`

### Task 2: Document ACL Panel
- Added ACL types (`ACLEntryResponse`, `ACLEntryCreate`) and three API functions (`fetchDocumentACLs`, `addDocumentACL`, `removeDocumentACL`) to `documents.ts`
- Created `DocumentACLPanel` component with:
  - ACL entry list with principal type icon, truncated ID, permission level badge, and remove button
  - Add dialog with principal type select, user dropdown (via `listUsers`), permission level select
  - Color-coded permission badges (green=READ, blue=WRITE, orange=DELETE, red=ADMIN)
  - Loading skeleton and empty state matching RelationshipPanel pattern
- Wired `DocumentACLPanel` into `DocumentDetailPanel` as Section 9 between Relationships and FolderPickerDialog

**Commit:** `8f699c7`

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None - all data sources are wired to real API endpoints.

## Verification

- TypeScript compilation passes with no errors
- All acceptance criteria met for both tasks

## Self-Check: PASSED
