---
phase: "21"
plan: "01"
subsystem: virtual-documents
tags: [virtual-documents, compound-documents, pdf-merge, document-assembly]
dependency_graph:
  requires: [documents]
  provides: [virtual-document-api, merged-pdf-generation]
  affects: [document-management]
tech_stack:
  added: [pypdf]
  patterns: [parent-child-assembly, cycle-detection, sort-order-compaction]
key_files:
  created:
    - src/app/models/virtual_document.py
    - src/app/schemas/virtual_document.py
    - src/app/services/virtual_document_service.py
    - src/app/routers/virtual_documents.py
  modified:
    - src/app/models/__init__.py
    - src/app/main.py
decisions:
  - "Used pypdf for PDF merging (lazy import, graceful error if not installed)"
  - "Cycle detection guard is a no-op for current model since virtual docs reference documents, not other virtual docs -- guard structure in place for future evolution"
  - "Sort order compaction on add/remove/reorder to maintain contiguous ordering"
metrics:
  duration: "3m"
  completed: "2026-04-06"
  tasks: 3
  files_created: 4
  files_modified: 2
---

# Phase 21 Plan 01: Virtual Document Models, API, and Merged PDF Summary

Virtual/compound document assembly with parent-child ordering, cycle detection guard, CRUD + child management API, and merged PDF generation via pypdf.

## What Was Built

### Task 1: Virtual Document Models (b0838fd)
- `VirtualDocument` model with title, description, owner FK, cascading children relationship
- `VirtualDocumentChild` model with sort_order, unique constraints on (vdoc, document) and (vdoc, sort_order)
- Models registered in `__init__.py` and `__all__`

### Task 2: Schemas and Service Layer (1af2c1c)
- Pydantic schemas: `VirtualDocumentCreate`, `VirtualDocumentUpdate`, `AddChildRequest`, `ReorderChildrenRequest`, response schemas with document metadata
- Service: full CRUD for virtual documents with pagination
- Child management: add (with sort_order shifting), remove (with compaction), reorder (with validation)
- Cycle detection: structural guard in place, currently returns False since virtual docs reference documents (not other virtual docs)
- Merged PDF: downloads latest version of each child from MinIO, merges PDFs using pypdf, skips non-PDF content

### Task 3: API Endpoints and Registration (d549f59)
- POST `/virtual-documents/` -- create
- GET `/virtual-documents/` -- list with pagination and optional owner filter
- GET `/virtual-documents/{id}` -- get with children
- PUT `/virtual-documents/{id}` -- update metadata
- DELETE `/virtual-documents/{id}` -- soft delete
- POST `/virtual-documents/{id}/children` -- add child document
- DELETE `/virtual-documents/{id}/children/{doc_id}` -- remove child
- PUT `/virtual-documents/{id}/children/reorder` -- reorder children
- GET `/virtual-documents/{id}/merge` -- download merged PDF
- Router registered in main.py

## Decisions Made

1. **pypdf for merging**: Lazy-imported in the merge function. Returns 501 if not installed rather than crashing at startup.
2. **Cycle detection is a structural no-op**: Since virtual documents reference `documents` table (not other virtual documents), true cycles cannot form. The guard function exists for future evolution if virtual-to-virtual nesting is added.
3. **Sort order compaction**: When children are added at a specific position or removed, existing sort orders are shifted to stay contiguous (0, 1, 2, ...).

## Deviations from Plan

None -- plan executed exactly as written.

## Known Stubs

None -- all endpoints are fully wired to the service layer and database.

## Self-Check: PASSED

- [x] src/app/models/virtual_document.py exists
- [x] src/app/schemas/virtual_document.py exists
- [x] src/app/services/virtual_document_service.py exists
- [x] src/app/routers/virtual_documents.py exists
- [x] Commit b0838fd exists
- [x] Commit 1af2c1c exists
- [x] Commit d549f59 exists
