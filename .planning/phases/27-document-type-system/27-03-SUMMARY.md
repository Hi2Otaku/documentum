---
phase: 27-document-type-system
plan: 03
subsystem: frontend
tags: [react, typescript, tanstack-query, shadcn-ui, document-types, admin-ui]

requires:
  - phase: 27-02
    provides: document_types CRUD API at /api/v1/document-types/ with DocumentTypeResponse shape

provides:
  - DocumentTypesPage admin page at /admin/types
  - DocumentTypeTable component with Name/Fields/Documents/Parent Type/Actions columns
  - CreateTypeDialog with JSON schema editor and parent type selection
  - EditTypeDialog pre-populated form with nested delete confirmation
  - SchemaEditor monospace textarea with JSON parse error display
  - documentTypes.ts API client with fetchDocumentTypes, createDocumentType, updateDocumentType, deleteDocumentType
  - SidebarNav Types link (adminOnly) using Tags icon
  - App.tsx route /admin/types inside AdminRoute group

affects:
  - 27-04 (integration tests can now exercise full UI + backend pipeline)

tech-stack:
  added: []
  patterns:
    - "useQuery with queryKey ['documentTypes'] for type list fetching"
    - "Dialog + form with useState for CRUD dialogs — same pattern as CheckInDialog"
    - "JSON.parse for schema validation before API submit with inline error display"
    - "Nested Dialog for delete confirmation with autoFocus on Cancel for safety"
    - "createColumnHelper<T> + useReactTable for admin table — same pattern as DocumentTable"

key-files:
  created:
    - frontend/src/api/documentTypes.ts
    - frontend/src/pages/DocumentTypesPage.tsx
    - frontend/src/components/admin/DocumentTypeTable.tsx
    - frontend/src/components/admin/CreateTypeDialog.tsx
    - frontend/src/components/admin/EditTypeDialog.tsx
    - frontend/src/components/admin/SchemaEditor.tsx
  modified:
    - frontend/src/components/layout/SidebarNav.tsx
    - frontend/src/App.tsx

key-decisions:
  - "JSON schema validation in dialog (client-side) before API call — validates JSON parse and presence of at least one property"
  - "Parent type dropdown filters to root-only types (parent_type_id === null) to prevent multi-level inheritance in UI"
  - "EditTypeDialog also filters out current type from parent options to prevent self-referential type"
  - "Delete confirmation auto-focuses Cancel button per accessibility spec"

requirements-completed: [TYPE-01]

duration: 3.5min
completed: 2026-04-13
---

# Phase 27 Plan 03: Document Type Admin UI Summary

**Document Types admin UI: DocumentTypesPage with CRUD table, CreateTypeDialog, EditTypeDialog with delete confirmation, SchemaEditor, API client, SidebarNav Types link, and App.tsx route wiring.**

## Performance

- **Duration:** ~3.5 min
- **Started:** 2026-04-13T04:05:53Z
- **Completed:** 2026-04-13T04:09:22Z
- **Tasks:** 2 of 2
- **Files modified:** 8 (6 created, 2 modified)

## Accomplishments

- Created `documentTypes.ts` API client: `fetchDocumentTypes`, `fetchDocumentType`, `createDocumentType`, `updateDocumentType`, `deleteDocumentType` — mirrors `documents.ts` pattern with auth headers and envelope unwrapping
- Created `DocumentTypeTable` with TanStack Table: Name (with description below), Fields, Documents, Parent Type, Actions (Edit button + three-dot DropdownMenu with Delete option), 5 skeleton rows, empty state matching copywriting contract
- Created `DocumentTypesPage` at `/admin/types`: header with Tags icon + title + Create Type CTA, useQuery for type list, CreateTypeDialog and EditTypeDialog conditionally rendered, query invalidation on CRUD success
- Created `SchemaEditor`: monospace textarea with `aria-describedby` pointing to error element, shows red `text-destructive` error message below
- Created `CreateTypeDialog`: name/description/parent type (root-only options)/schema fields, JSON parse validation + property count validation, "Save Type" submit, toast.success("Type created")
- Created `EditTypeDialog`: pre-populated form, "Delete Type" destructive button in footer, nested confirmation Dialog with `autoFocus` Cancel, toast.success("Type deleted") and toast.success("Type updated")
- Updated `SidebarNav`: added `Tags` icon import, `{ icon: Tags, label: "Types", route: "/admin/types", adminOnly: true }` after Query entry
- Updated `App.tsx`: added `DocumentTypesPage` import and `<Route path="/admin/types" element={<DocumentTypesPage />} />` inside AdminRoute

## Task Commits

1. **Task 1: Create API client and admin page shell with table** - `88e52eb` (feat)
2. **Task 2: Create type CRUD dialogs with schema editor** - `d937fa2` (feat)

## Files Created/Modified

- `frontend/src/api/documentTypes.ts` — New: API client with 5 exported functions and 3 exported interfaces
- `frontend/src/pages/DocumentTypesPage.tsx` — New: Admin page at /admin/types
- `frontend/src/components/admin/DocumentTypeTable.tsx` — New: Type list table with TanStack Table
- `frontend/src/components/admin/CreateTypeDialog.tsx` — New: Create form dialog
- `frontend/src/components/admin/EditTypeDialog.tsx` — New: Edit form + delete confirmation
- `frontend/src/components/admin/SchemaEditor.tsx` — New: JSON schema textarea editor
- `frontend/src/components/layout/SidebarNav.tsx` — Modified: added Tags import + Types nav item
- `frontend/src/App.tsx` — Modified: added DocumentTypesPage import + /admin/types route

## Decisions Made

- Client-side JSON schema validation validates both JSON parse correctness and presence of at least one property before calling the API, matching the UI spec error contract
- Parent type dropdown restricted to root types only (no existing parent) to prevent 3-level hierarchy in UI, consistent with backend max-1-level enforcement
- EditTypeDialog syncs state from type prop on open via useEffect to handle the case where the same dialog is reused with different types

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all components are wired to live API via useQuery/useMutation patterns.

## Self-Check: PASSED

Files verified:
- FOUND: frontend/src/api/documentTypes.ts
- FOUND: frontend/src/pages/DocumentTypesPage.tsx
- FOUND: frontend/src/components/admin/DocumentTypeTable.tsx
- FOUND: frontend/src/components/admin/CreateTypeDialog.tsx
- FOUND: frontend/src/components/admin/EditTypeDialog.tsx
- FOUND: frontend/src/components/admin/SchemaEditor.tsx
- FOUND: frontend/src/components/layout/SidebarNav.tsx (Tags added)
- FOUND: frontend/src/App.tsx (/admin/types route added)

Commits verified:
- FOUND: 88e52eb
- FOUND: d937fa2

TypeScript: No errors (tsc --noEmit passed)
Vite build: Production build succeeded (built in 889ms)

---
*Phase: 27-document-type-system*
*Completed: 2026-04-13*
