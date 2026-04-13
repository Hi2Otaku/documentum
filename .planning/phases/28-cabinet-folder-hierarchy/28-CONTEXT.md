---
phase: 28
name: Cabinet/Folder Hierarchy
status: ready-for-research
requirements: [FOLD-01, FOLD-02, FOLD-03, FOLD-04]
depends_on: Phase 27 (complete)
auto_decided: true
---

# Phase 28: Cabinet/Folder Hierarchy — Context

## Goal

Users can organize documents in a navigable cabinet/folder tree and file documents into one or more folders.

## Decisions

### Data Model

**Cabinet vs Folder: single `folders` table**
- Cabinets are just folders with `parent_id = NULL` — no separate table, no separate model
- `is_cabinet` boolean flag on the folders table for clarity in API responses and UI
- Follows the same self-referential FK pattern as `document_types.parent_type_id`
- Table: `folders` (id, name, description, parent_id FK folders.id, is_cabinet, created_at, updated_at, created_by, is_deleted)

**Document-folder filing: many-to-many junction**
- A document can be filed in multiple folders (FOLD-03)
- Table: `document_folders` (document_id FK documents.id, folder_id FK folders.id, filed_at, filed_by) — composite PK
- Filing is a relationship, not a move; documents are not "in" one folder

**Path resolution: recursive CTE**
- STATE.md decision: no ltree extension — adjacency list + recursive CTEs
- `WITH RECURSIVE` CTE to compute full path (list of ancestor folders up to cabinet)
- Path is computed on demand (not stored) — acceptable at current scale

### API Design

**Endpoints:**
- `GET /api/v1/folders/` — list root cabinets (is_cabinet=true)
- `POST /api/v1/folders/` — create cabinet (no parent_id)
- `GET /api/v1/folders/tree` — full tree for navigation (recursive, returns nested JSON)
- `GET /api/v1/folders/{id}` — get folder with full path breadcrumb
- `POST /api/v1/folders/{id}/children` — create subfolder inside this folder
- `PUT /api/v1/folders/{id}` — rename or move (change name and/or parent_id)
- `DELETE /api/v1/folders/{id}` — soft delete (recursive: soft-deletes subtree, unfiles documents)
- `POST /api/v1/folders/{id}/copy` — shallow copy (copies folder structure, re-links existing documents without duplicating files)
- `GET /api/v1/folders/{id}/documents` — list documents filed in this folder (paginated)
- `POST /api/v1/folders/{id}/documents` — file a document into this folder body: `{document_id: string}`
- `DELETE /api/v1/folders/{id}/documents/{document_id}` — unfile document from this folder

**Document API changes:**
- `DocumentResponse` gets `folder_ids: string[]` — list of folder IDs this document is filed in
- Upload endpoint does NOT auto-file (filing is a separate action) — avoids complexity with multi-filing
- `GET /api/v1/documents/` list endpoint gets optional `folder_id` filter param

### Frontend Scope (Phase 28)

**Included in Phase 28:**
- Folder management page at `/admin/folders` (admin-only for cabinet creation; regular users can create subfolders if they have write permission)
- Tree navigator component (`FolderTree`) — expandable/collapsible nodes, document count per node
- File/Unfile document from document detail panel — "Add to Folder" button opens folder picker
- Breadcrumb component for folder path display

**Deferred to Phase 32:**
- Full `/browse` route with folder tree sidebar as primary navigation
- Document grid view inside a folder (folder-as-content-view)
- Inline document detail panel from browse view

**Rationale:** Phase 28 delivers the data model and CRUD plumbing. Phase 32 is the polished document-first navigation experience. The FolderTree component built in Phase 28 will be reused in Phase 32.

### Copy Behavior

**Shallow copy:**
- Creates new folder node(s) mirroring the source subtree structure
- Re-links documents from source folders to new copy folders via new `document_folders` rows
- Does NOT duplicate document files in MinIO or create new Document records
- Copy target: user specifies destination parent (defaults to same parent as source)

### Move Behavior

- `PUT /api/v1/folders/{id}` with new `parent_id` changes the folder's parent
- Move validates no circular reference (can't move a folder into its own subtree)
- Documents automatically appear in new location (they reference folder by ID)

### Tree Depth

- Unlimited nesting depth (adjacency list supports this)
- `GET /api/v1/folders/tree` returns full tree — no lazy loading in Phase 28
- Phase 32 may optimize to lazy-load children on expand if tree becomes very large

### Delete Behavior

- Soft delete (consistent with all other models — `is_deleted = true`)
- Recursive: deleting a cabinet soft-deletes all subfolders
- Documents are NOT deleted — only `document_folders` rows for the deleted folder are removed
- If a document's only folder filing is the deleted folder, document becomes "unfiled" (folder_ids = [])

## Code Context

### Reusable Patterns

```
backend:
  - src/app/models/document_type.py       # parent_type_id FK pattern to copy for Folder.parent_id
  - src/app/services/document_type_service.py  # service layer pattern
  - src/app/routers/document_types.py     # router pattern with paginated list + CRUD
  - alembic/versions/phase27_001_document_types.py  # migration pattern

frontend:
  - frontend/src/api/documentTypes.ts     # API client pattern (fetch, create, update, delete)
  - frontend/src/components/admin/DocumentTypeTable.tsx  # TanStack Table admin table pattern
  - frontend/src/components/documents/DocumentDetailPanel.tsx  # detail panel extension point
  - frontend/src/components/documents/TypeSelector.tsx  # selector with useQuery pattern
```

### Integration Points

```
backend:
  - src/app/models/document.py            # Add folder_ids to DocumentResponse (via relationship)
  - src/app/routers/documents.py          # Add folder_id filter to list endpoint
  - src/app/schemas/document.py           # Add folder_ids field to DocumentResponse schema

frontend:
  - frontend/src/api/documents.ts         # Add folder_ids to DocumentResponse interface
  - frontend/src/components/documents/DocumentDetailPanel.tsx  # Add "Add to Folder" section
  - frontend/src/App.tsx                  # Add /admin/folders route
  - frontend/src/components/layout/SidebarNav.tsx  # Add Folders nav item
```

## Canonical Refs

- `.planning/ROADMAP.md` — Phase 28 success criteria and plan count
- `.planning/REQUIREMENTS.md` — FOLD-01 through FOLD-04 requirements
- `.planning/STATE.md` — adjacency list + recursive CTE decision, no ltree
- `src/app/models/document_type.py` — parent_type_id FK precedent
- `src/app/models/document.py` — Document model to extend
- `src/app/routers/document_types.py` — Router pattern to follow
- `alembic/versions/phase27_001_document_types.py` — Migration pattern

## Plans

3 plans:
- 28-01: Backend model, migration, service (Folder model, document_folders, FolderService with CTE path resolution)
- 28-02: API layer (folder CRUD endpoints, filing endpoints, document list folder_id filter, folder_ids in DocumentResponse)
- 28-03: Frontend (FolderTree component, admin folders page, filing UI in DocumentDetailPanel, SidebarNav link)
