# Roadmap: Documentum Workflow Clone

## Milestones

- ✅ **v1.0 Core Engine** — Phases 1–11 (shipped)
- ✅ **v1.1 Full Frontend Experience** — Phases 12–15 (shipped 2026-04-06)
- ✅ **v1.2 Advanced Engine & Document Platform** — Phases 16–26 (shipped 2026-04-13)
- 🚧 **v1.3 Document-Centric ECM** — Phases 27–33 (active)

## Phases

<details>
<summary>✅ v1.0 Core Engine (Phases 1–11) — SHIPPED</summary>

Phases 1–11 delivered the complete workflow engine backend: Docker stack, database schema, authentication, audit trail, document management, workflow templates, process engine, visual designer, lifecycle/ACL integration, auto activities, delegation, work queues, BAM dashboards, and the contract approval demo workflow.

</details>

<details>
<summary>✅ v1.1 Full Frontend Experience (Phases 12–15) — SHIPPED 2026-04-06</summary>

Phases 12–15 delivered the complete web UI: navigation shell, inbox with work item management, document management pages, and workflow operations with start wizard and progress visualization.

</details>

<details>
<summary>✅ v1.2 Advanced Engine & Document Platform (Phases 16–26) — SHIPPED 2026-04-13</summary>

- [x] Phase 16: Notifications & Event Bus (4/4 plans) — 2026-04-06
- [x] Phase 17: Timer Activities & Escalation (3/3 plans) — 2026-04-06
- [x] Phase 18: Sub-Workflows (3/3 plans) — 2026-04-06
- [x] Phase 19: Event-Driven Activities (2/2 plans) — 2026-04-06
- [x] Phase 20: Document Renditions (3/3 plans) — 2026-04-06
- [x] Phase 21: Virtual Documents (2/2 plans) — 2026-04-06
- [x] Phase 22: Retention & Records Management (2/2 plans) — 2026-04-06
- [x] Phase 23: Digital Signatures (2/2 plans) — 2026-04-06
- [x] Phase 24: Infrastructure Wiring & Event Bus Integration (3/3 plans) — 2026-04-07
- [x] Phase 25: Virtual Documents Frontend Fix (1/1 plan) — 2026-04-07
- [x] Phase 26: Digital Signatures Alignment (1/1 plan) — 2026-04-07

See `.planning/milestones/v1.2-ROADMAP.md` for full phase details.

</details>

### 🚧 v1.3 Document-Centric ECM

**Milestone Goal:** Reorient the system from workflow-centric to document-centric, matching Documentum's ECM platform model -- where documents are the primary object and workflows exist to route them through structured processes.

- [ ] **Phase 27: Document Type System** — Custom document types with JSON Schema metadata validation and type inheritance
- [x] **Phase 28: Cabinet/Folder Hierarchy** — Navigable cabinet/folder tree with document filing and folder CRUD (completed 2026-04-13)
- [ ] **Phase 29: Folder ACL Inheritance** — Folder-level permissions that propagate down to contained documents
- [ ] **Phase 30: Full-Text Search & Content Extraction** — Text extraction pipeline and ranked search across document content and metadata
- [ ] **Phase 31: Document Relationships** — Typed directional links between documents (supersedes, references, is-part-of)
- [ ] **Phase 32: Document-First Navigation** — Browse UI with folder tree sidebar, content grid, and inline document detail
- [ ] **Phase 33: Saved Searches & Smart Folders** — Named search queries that persist and appear as virtual folders in the tree

## Phase Details

### Phase 27: Document Type System
**Goal**: Users can define custom document types with structured metadata schemas, assign types to documents, and have metadata validated automatically
**Depends on**: Nothing (first phase of v1.3)
**Requirements**: TYPE-01, TYPE-02, TYPE-03, TYPE-04, TYPE-05
**Success Criteria** (what must be TRUE):
  1. User can create a document type with a name and JSON Schema metadata definition, and see it listed in an admin page
  2. User can assign a type to a document and fill in type-specific metadata fields rendered dynamically from the schema
  3. System rejects a document save when required metadata fields (per the type schema) are missing, with descriptive error messages
  4. User can create a child type that inherits metadata fields from a parent type, and documents of the child type validate against both schemas
**Plans**: 4 plans
Plans:
- [x] 27-01-PLAN.md — Backend foundation: model, schemas, service, migration, test stubs
- [x] 27-02-PLAN.md — API layer: document_types CRUD router + document upload/update integration
- [x] 27-03-PLAN.md — Frontend admin: types page, table, create/edit dialogs, schema editor
- [x] 27-04-PLAN.md — Frontend integration: TypeSelector, TypeMetadataForm, table/detail mods
**UI hint**: yes

### Phase 28: Cabinet/Folder Hierarchy
**Goal**: Users can organize documents in a navigable cabinet/folder tree and file documents into one or more folders
**Depends on**: Phase 27 (type system must exist so folders can be typed)
**Requirements**: FOLD-01, FOLD-02, FOLD-03, FOLD-04
**Success Criteria** (what must be TRUE):
  1. User can create a cabinet (top-level container) and create nested folders within any existing folder
  2. User can browse the full folder tree by expanding/collapsing nodes in a hierarchical navigator
  3. User can file a document into multiple folders and remove it from a folder without deleting the document
  4. User can move, rename, and copy folders, and see the full path via breadcrumb navigation
**Plans**: 3 plans
Plans:
- [x] 28-01-PLAN.md — Backend foundation: Folder model, migration, FolderService with CTE operations
- [x] 28-02-PLAN.md — API layer: folders router, document API integration, test implementation
- [x] 28-03-PLAN.md — Frontend: FolderTree, admin page, filing UI, navigation wiring
**UI hint**: yes

### Phase 29: Folder ACL Inheritance
**Goal**: Folder-level permissions flow down to documents, so users only see documents they are authorized to access when browsing
**Depends on**: Phase 28 (folders must exist)
**Requirements**: FOLD-05
**Success Criteria** (what must be TRUE):
  1. User with read permission on a folder can see all documents filed in that folder (and its subfolders) without per-document ACL entries
  2. User without folder permission cannot see documents that rely solely on inherited folder ACL for access
  3. Direct document-level ACL entries override inherited folder permissions when both exist
**Plans**: TBD

### Phase 30: Full-Text Search & Content Extraction
**Goal**: Users can search across document content and metadata with ranked results, powered by automatic text extraction from uploaded files
**Depends on**: Phase 28 (folder context for scoped search)
**Requirements**: SRCH-01, SRCH-02, SRCH-03
**Success Criteria** (what must be TRUE):
  1. After uploading a PDF or Word document, its text content becomes searchable within seconds via a background extraction worker
  2. User can search by keyword and see ranked results with highlighted snippets showing where the match occurred
  3. User can narrow search results by folder, document type, or lifecycle state
  4. Extraction failures are logged and surfaced (not silent) -- the document remains accessible but is marked as not indexed
**Plans**: TBD
**UI hint**: yes

### Phase 31: Document Relationships
**Goal**: Users can create and navigate typed relationships between documents, establishing traceability links
**Depends on**: Nothing (only requires existing Document model)
**Requirements**: REL-01, REL-02, REL-03
**Success Criteria** (what must be TRUE):
  1. User can create a typed, directional relationship between two documents (e.g., "Document A supersedes Document B")
  2. User can view all relationships for a document in a dedicated panel within the document detail view
  3. User can click a relationship link to navigate directly to the related document
**Plans**: TBD
**UI hint**: yes

### Phase 32: Document-First Navigation
**Goal**: Users experience a document-centric application where browsing by folder is the primary entry point, with all document context (type, location, relationships) visible inline
**Depends on**: Phase 27, 28, 29, 30, 31 (consumes all backend features)
**Requirements**: NAV-01, NAV-02, NAV-03, NAV-04
**Success Criteria** (what must be TRUE):
  1. User can access `/browse` as the default application entry point with a collapsible folder tree sidebar
  2. User can expand/collapse folder tree nodes to navigate cabinets and subfolders, with document counts shown on each node
  3. User can click a document in the content grid to open its detail panel inline (without leaving the browse view), showing type, location, and relationships
  4. User sees a clickable breadcrumb showing the full cabinet > folder > subfolder path and can navigate up by clicking any segment
**Plans**: TBD
**UI hint**: yes

### Phase 33: Saved Searches & Smart Folders
**Goal**: Users can save search queries for reuse and display them as virtual folders in the folder tree
**Depends on**: Phase 30, 32 (search infrastructure + browse tree)
**Requirements**: SRCH-04, SRCH-05
**Success Criteria** (what must be TRUE):
  1. User can save a search query with a name and retrieve it in a future session
  2. User can mark a saved search to appear as a smart folder in the folder tree, and clicking it displays the search results as if browsing a folder
**Plans**: TBD
**UI hint**: yes

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1–11. Core Engine | v1.0 | 47/47 | Complete | 2026-03-30 |
| 12–15. Full Frontend | v1.1 | 4/4 | Complete | 2026-04-06 |
| 16–26. Advanced Engine | v1.2 | 26/26 | Complete | 2026-04-13 |
| 27. Document Type System | v1.3 | 4/4 | Complete | 2026-04-13 |
| 28. Cabinet/Folder Hierarchy | v1.3 | 3/3 | Complete    | 2026-04-13 |
| 29. Folder ACL Inheritance | v1.3 | 0/? | Not started | — |
| 30. Full-Text Search & Content Extraction | v1.3 | 0/? | Not started | — |
| 31. Document Relationships | v1.3 | 0/? | Not started | — |
| 32. Document-First Navigation | v1.3 | 0/? | Not started | — |
| 33. Saved Searches & Smart Folders | v1.3 | 0/? | Not started | — |
