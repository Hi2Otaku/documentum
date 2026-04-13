# Requirements: v1.3 Document-Centric ECM

Generated: 2026-04-13
Milestone: v1.3 Document-Centric ECM

---

## v1.3 Requirements

### Document Type System

- [x] **TYPE-01**: User can define a named document type with a JSON Schema metadata definition
- [x] **TYPE-02**: User can assign a type to a document at creation or edit time
- [x] **TYPE-03**: System validates document metadata against the assigned type's JSON Schema on save, rejecting missing required fields with descriptive errors
- [x] **TYPE-04**: User can define a document type that inherits schema fields from a parent type
- [ ] **TYPE-05**: Frontend renders type-specific metadata form fields based on the document's assigned type

### Cabinet/Folder Hierarchy

- [x] **FOLD-01**: User can create a cabinet (top-level container) and nested folders within any folder
- [x] **FOLD-02**: User can browse the full cabinet/folder tree via a hierarchical navigator
- [x] **FOLD-03**: User can file a document into one or more folders (multi-filing); removing from a folder does not delete the document
- [x] **FOLD-04**: User can move, rename, and copy folders; breadcrumb navigation shows the full path
- [x] **FOLD-05**: Permissions assigned to a folder are inherited by all documents within it (folder-level ACL propagation)

### Full-Text Search

- [ ] **SRCH-01**: System automatically extracts and indexes text from PDF and Word documents via a background Celery worker; extraction failures are logged and do not block document save
- [ ] **SRCH-02**: User can search documents by content (full-text body) and metadata fields (title, description, type-specific fields) with ranked results
- [ ] **SRCH-03**: User can scope a search to a specific folder, document type, or lifecycle state
- [ ] **SRCH-04**: User can save a named search query and retrieve it in future sessions
- [ ] **SRCH-05**: User can display a saved search as a smart folder in the folder tree

### Document Relationships

- [ ] **REL-01**: User can create a typed relationship between two documents (supersedes, references, is-part-of), with direction
- [ ] **REL-02**: User can view all relationships for a document in a relationships panel within the document detail view
- [ ] **REL-03**: User can navigate from a document to any related document via the relationship link

### Document Navigation

- [ ] **NAV-01**: User can access a `/browse` route as the document-first entry point with a collapsible folder tree sidebar
- [ ] **NAV-02**: User can expand/collapse the folder tree to navigate cabinets, folders, and subfolders; each node shows document count
- [ ] **NAV-03**: User can click a document in the folder listing to open its detail panel inline without leaving the browse view
- [ ] **NAV-04**: User sees a breadcrumb showing the full cabinet > folder > subfolder path and can click any segment to navigate up

---

## Future Requirements (Deferred)

- Text extraction beyond PDF and Word (Excel, PowerPoint, RTF, plain text) — Phase 30 extension
- Full-text indexing of custom_properties JSONB values — requires type system maturity first
- dm_sysobject polymorphic base table — deemed too risky (10+ FK references); revisit in v1.4 if needed
- ltree PostgreSQL extension for massive hierarchies — adjacency list + CTE is sufficient at current scale
- Materialized effective ACL caching — implement only if query-time resolution proves too slow under load

---

## Out of Scope

- **Multi-tenant isolation** — internal/personal use, adds complexity everywhere
- **Mobile native app** — web-responsive UI is sufficient
- **Real-time collaborative editing** — check-in/check-out prevents conflicts; OT/CRDT is excessive
- **Full PKI/CA infrastructure** — already in v1.2 out of scope; not re-opened here
- **Separate DB table per document type** — Documentum's legacy approach; JSONB + JSON Schema is the modern alternative
- **Elasticsearch / Typesense** — PostgreSQL tsvector handles the expected volume with zero new infrastructure
- **ltree PostgreSQL extension** — Unicode label restrictions and path-desync bugs outweigh the query performance benefit at this scale

---

## Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| TYPE-01 | Phase 27 | Complete |
| TYPE-02 | Phase 27 | Complete |
| TYPE-03 | Phase 27 | Complete |
| TYPE-04 | Phase 27 | Complete |
| TYPE-05 | Phase 27 | Pending |
| FOLD-01 | Phase 28 | Complete |
| FOLD-02 | Phase 28 | Complete |
| FOLD-03 | Phase 28 | Complete |
| FOLD-04 | Phase 28 | Complete |
| FOLD-05 | Phase 29 | Complete |
| SRCH-01 | Phase 30 | Pending |
| SRCH-02 | Phase 30 | Pending |
| SRCH-03 | Phase 30 | Pending |
| SRCH-04 | Phase 33 | Pending |
| SRCH-05 | Phase 33 | Pending |
| REL-01 | Phase 31 | Pending |
| REL-02 | Phase 31 | Pending |
| REL-03 | Phase 31 | Pending |
| NAV-01 | Phase 32 | Pending |
| NAV-02 | Phase 32 | Pending |
| NAV-03 | Phase 32 | Pending |
| NAV-04 | Phase 32 | Pending |
