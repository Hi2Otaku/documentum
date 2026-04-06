---
phase: 21-virtual-documents
plan: "02"
subsystem: frontend-virtual-documents
tags: [virtual-documents, frontend, react, ui-components]
dependency_graph:
  requires: [21-01]
  provides: [virtual-document-ui, virtual-document-api-client]
  affects: [DocumentsPage]
tech_stack:
  added: []
  patterns: [tabs-navigation, blob-download, children-reorder-ui]
key_files:
  created:
    - frontend/src/api/virtualDocuments.ts
    - frontend/src/components/virtual-documents/CreateVirtualDocumentDialog.tsx
    - frontend/src/components/virtual-documents/VirtualDocumentChildrenList.tsx
    - frontend/src/components/virtual-documents/AddChildDialog.tsx
    - frontend/src/components/virtual-documents/VirtualDocumentDetailPanel.tsx
  modified:
    - frontend/src/pages/DocumentsPage.tsx
decisions:
  - Used Radix Tabs for documents/virtual-documents view toggle instead of simple state toggle for accessibility
  - Inline SVG icons for chevron and X buttons to avoid adding icon library dependency
  - VirtualDocumentTable kept as internal component in DocumentsPage since it is only used there
metrics:
  duration: 3m
  completed: "2026-04-06T19:31:42Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 5
  files_modified: 1
---

# Phase 21 Plan 02: Virtual Document Frontend UI Summary

Complete frontend for virtual documents with API client, children management UI with reorder/remove controls, add-child dialog with search, create dialog, detail panel with PDF merge download, and tab-based integration into the existing DocumentsPage.

## What Was Built

### API Client (virtualDocuments.ts)
- 8 exported functions matching all backend virtual document endpoints
- `createVirtualDocument`, `fetchVirtualDocuments`, `fetchVirtualDocument` for CRUD
- `addChild`, `removeChild`, `reorderChildren` for children management
- `mergePdfUrl` and `downloadMergedPdf` for PDF generation with blob download trigger
- Full type definitions: VirtualDocumentResponse, VirtualDocumentChildResponse, PaginatedVirtualDocumentsResponse

### CreateVirtualDocumentDialog
- shadcn Dialog with title (required) and description (optional) form fields
- useMutation with query invalidation and toast notifications
- Reusable with custom trigger via props

### VirtualDocumentChildrenList
- Ordered list rendering with move-up/move-down/remove buttons per row
- Disabled states for first/last items on directional buttons
- Empty state message when no children exist
- Inline SVG icons (ChevronUp, ChevronDown, X) for compact ghost buttons

### AddChildDialog
- Search input that filters documents by title via fetchDocuments API
- Results list with "Add" button per document
- Already-added documents shown grayed out with "Already added" label
- useMutation for addChild with query invalidation

### VirtualDocumentDetailPanel
- Fetches virtual document by ID with useQuery
- Info card showing created/updated dates and child count
- Embedded VirtualDocumentChildrenList with reorder/remove mutations
- "Add Document" button opening AddChildDialog
- "Generate Merged PDF" button with loading state and blob download

### DocumentsPage Integration
- Radix Tabs component toggling between "Documents" and "Virtual Documents" views
- Documents tab retains all existing functionality unchanged
- Virtual Documents tab shows VirtualDocumentTable with title, children count, created date
- Selection opens VirtualDocumentDetailPanel in right panel
- "Create Virtual Document" button in virtual tab toolbar
- Pagination for virtual documents list

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 73b2645 | API client and create dialog |
| 2 | 4720c2a | Children list, add-child dialog, detail panel, page integration |

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None - all components are fully wired to API functions and use real query/mutation hooks.

## Self-Check: PASSED

All 5 created files and 1 modified file verified on disk. Both commits (73b2645, 4720c2a) verified in git log. TypeScript compiles cleanly with zero errors.
