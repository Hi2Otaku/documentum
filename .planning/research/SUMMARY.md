# Research Summary: v1.3 Document-Centric ECM

**Domain:** Enterprise Content Management -- cabinet/folder hierarchy, document types, full-text search, document-first navigation
**Researched:** 2026-04-13
**Overall confidence:** HIGH

---

## Resolved Architecture Decisions

Two conflicts emerged between researcher outputs. Both are resolved definitively below. These resolutions are non-negotiable constraints for every downstream phase plan.

### Resolution 1: No dm_sysobject Polymorphic Base Table

**What was proposed:** Stack researcher recommended SQLAlchemy joined-table polymorphic inheritance creating a physical `dm_sysobject` base table that folders and documents would inherit from.

**Why it was rejected:** The existing `documents` table carries 10+ foreign key references: `DocumentVersion`, `DocumentACL`, `WorkflowPackage`, `Rendition`, `RetentionPolicy`, `LegalHold`, `DocumentSignature`, `VirtualDocumentChild`, and more. Converting `documents.id` to a FK pointing at a new `sysobjects.id` primary key would require migrating every one of those tables in a single Alembic migration. This is a destructive, multi-table schema change against a 26-phase production codebase with significant data. The risk of broken FKs, failed migration rollbacks, and data loss is unacceptable.

**Chosen approach:** Keep `documents` and `folders` as separate, independent tables. Both extend the existing `BaseModel` mixin, which already provides `id`, `created_at`, `updated_at`, and soft-delete fields. This achieves the common attributes goal that dm_sysobject served conceptually, without touching a single existing FK reference. The Python mixin is the correct abstraction -- the schema stays unchanged.

**Impact on phases:** Phase 28 creates the `folders` table fresh, extending `BaseModel`. No migration of the `documents` table beyond adding 3 new nullable columns (`document_type_id`, `search_vector`, `owner_id`).

### Resolution 2: No ltree Extension -- Adjacency List + Recursive CTE

**What was proposed:** Stack researcher recommended PostgreSQL `ltree` extension combined with an adjacency list hybrid to enable O(1) subtree queries via GiST index.

**Why it was rejected:** ltree introduces three concrete problems for this use case. First, every folder move or rename requires rewriting the materialized path for all descendants -- a write-amplifying operation that is a known source of path desync bugs when transactions fail mid-update. Second, ltree label format restrictions (alphanumeric and underscore only) mean folder names with spaces, dots, or Unicode must be sanitized into opaque identifiers stored separately from the display name -- adding complexity with no benefit. Third, the existing codebase uses zero PostgreSQL extensions beyond core; adding ltree creates a new infrastructure dependency for marginal gain on ECM hierarchies that are typically 3-8 levels deep.

**Chosen approach:** Standard adjacency list with `parent_id` FK on the `folders` table, augmented with PostgreSQL recursive CTEs for tree queries (subtree listing, ancestor walk for ACL inheritance, breadcrumb path). A B-tree index on `folders.parent_id` ensures these queries execute in single-digit milliseconds at expected scale. If performance bottlenecks appear in the future (trees regularly exceeding 15 levels, hundreds of breadcrumb calls per second), a denormalized `materialized_path TEXT` column can be added alongside `parent_id` without changing the model or breaking existing code.

**Impact on phases:** Phase 28 uses simple `parent_id` FK. No PostgreSQL extension migration. Folder service implements recursive CTE helpers. Frontend lazy-loads tree nodes on expand.

---

## Stack Additions

No new infrastructure services are needed for v1.3. The existing PostgreSQL, Celery, Redis, MinIO, and FastAPI stack covers everything. No new PostgreSQL extensions are required -- tsvector/tsquery is built into PostgreSQL core.

Three new Python packages are added to production dependencies:

| Package | Version | Purpose | Rationale |
|---------|---------|---------|-----------|
| jsonschema | 4.x | Validate `Document.custom_properties` against type-specific JSON Schema definitions | Pydantic validates fixed schemas at compile time; jsonschema validates arbitrary user-defined schemas at runtime. Required for the document type system where admins define metadata schemas. |
| PyPDF2 | 3.x | Extract text from PDF files for full-text search indexing | Pure Python, no C dependency. Sufficient for text extraction. Lighter than PyMuPDF (C extension) and avoids the JVM requirement of Apache Tika. |
| python-docx | 1.1.x | Extract text from .docx Word files for full-text search indexing | Pure Python, lightweight. Covers the second most common document format after PDF. |

No new frontend npm packages are required. The folder tree component is built using existing shadcn/ui primitives (Collapsible, Button, DropdownMenu, ScrollArea) with React Query for data fetching. Beta-stage tree libraries (@headless-tree, react-arborist) are explicitly avoided. For ECM hierarchies at expected scale (hundreds of nodes, 3-8 levels), a custom implementation built on existing components gives full behavioral control without the stability risk.

---

## Feature Landscape

### Table Stakes

These features define the line between a workflow engine with document attachments and a genuine ECM platform. All must ship in v1.3.

| Feature | Complexity | Key Implementation Note |
|---------|------------|------------------------|
| Cabinet/folder hierarchy | Medium | Single `folders` table; `is_cabinet` boolean distinguishes cabinets (root) from folders. Adjacency list with recursive CTE. |
| Folder CRUD + move | Medium | Move updates `parent_id`; name uniqueness enforced per parent via DB unique constraint on `(parent_id, name)`. |
| Document-folder linking (multi-filing) | Low | Many-to-many `folder_documents` join table. Documents may live in multiple folders simultaneously (Documentum link/unlink semantics). |
| Document type definitions | Medium | `document_types` table with `metadata_schema` as JSON Schema. Validates `Document.custom_properties` on write via `jsonschema`. |
| Type inheritance | Medium | Self-referential `parent_type_id`. Schema merging at validation time (child schema merges with parent schema). |
| Full-text search | Medium | PostgreSQL tsvector on `documents` (metadata vector) + separate `document_content_text` table (body vector). GIN indexes. Trigger auto-updates metadata vector. |
| Search results with ranking | Low | `ts_rank` + `ts_headline` built into PostgreSQL. Zero extra infrastructure. |
| Metadata search and filtering | Low | Standard SQL WHERE clauses + JSONB operators on `custom_properties`. |
| Folder-level ACL inheritance | High | Recursive CTE walks folder tree upward to find effective permissions. Additive to existing `DocumentACL` -- does not replace it. |
| Breadcrumb navigation | Low | Single recursive CTE from folder to root. Cache recent breadcrumbs in React Query. |
| Document-first browse UI | High | New `BrowsePage` with split-panel layout: folder tree left, content grid center, detail panel right. Becomes default app route. |

### Differentiators

Features that match Documentum advanced capabilities beyond basic file storage.

| Feature | Value | Complexity |
|---------|-------|------------|
| Document relationships | Typed traceability links: supersedes, references, is-part-of, related-to. Junction table with `relationship_type` enum. | Low |
| Saved searches / smart folders | Named JSON queries appearing as virtual folders in the tree. Executed on access, paginated. | Medium |
| Type-specific metadata forms | Dynamic React form generated from JSON Schema at render time. Different types present different fields. | Medium |
| Content text extraction pipeline | Celery task extracts text from PDFs and Word docs on upload. Background, non-blocking, with status tracking. | Medium |

### Anti-Features (Do Not Build in v1.3)

| Anti-Feature | Reason |
|--------------|--------|
| dm_sysobject polymorphic base table | Destructive schema migration with 10+ FK dependencies. Resolved above. |
| ltree PostgreSQL extension | Path desync bugs, label restrictions, unnecessary for shallow hierarchies. Resolved above. |
| Elasticsearch / Meilisearch integration | New infrastructure service, sync complexity. PostgreSQL tsvector is sufficient for internal ECM. |
| Real-time collaborative editing | CRDT/OT complexity out of scope. Existing check-in/check-out covers the use case. |
| Content auto-classification (AI/ML) | Scope creep, not in Documentum spec. Future milestone. |
| Version tree branching | Linear major/minor versioning is sufficient. Branching adds significant complexity. |
| @headless-tree or react-arborist | Beta-stage or under-maintained. Custom shadcn/ui tree is simpler and more controllable. |

---

## Critical Pitfalls

### Pitfall 1: ACL Inheritance Permission Leaks (Phase 29)

Stale cached permissions after folder ACL changes cause restricted documents to become accessible to unauthorized users. This is a security vulnerability, not a performance problem.

**Prevention:** Compute effective permissions fresh on every request during initial implementation. Introduce caching only when performance data demands it, and invalidate on ACL change, folder move, and `inherit_acl` flag change. Write comprehensive tests covering: direct document ACL, inherited folder ACL, folder ACL override, folder move changing inherited permissions, and multi-filing scenarios where a document belongs to folders with different ACLs.

### Pitfall 2: Folder Deletion Cascading to Workflow-Attached Documents (Phase 28)

Deleting a folder that contains documents attached to active workflows orphans those workflow packages. Work items reference documents that can no longer be located.

**Prevention:** Require folders to be empty (no children, no filed documents) before deletion. Use soft-delete only (`is_deleted = true`). Before unfiling a document last folder link, check `retention_service.check_document_deletable()`. Do not use CASCADE on the `folder_documents` FK.

### Pitfall 3: Document Type Schema Evolution Breaks Existing Documents (Phase 27)

Adding a new required field to a type `metadata_schema` causes all existing documents of that type to fail validation on their next edit.

**Prevention:** Validate on write only, never on read. Block service-layer requests to add required fields without defaults. New fields must be optional by default or include a default value. Provide a migration utility for backfilling existing documents when schemas change.

### Pitfall 4: Silent Text Extraction Failures Kill Searchability (Phase 30)

A Celery extraction task fails silently (corrupt PDF, unsupported format, timeout). The document is uploaded successfully but never appears in content search results, with no indication to users or admins.

**Prevention:** Track `extraction_status` on `document_content_text`: pending, processing, completed, failed, unsupported. Log failures at WARNING level with `document_id`. Enforce a 60-second timeout per document. Retry transient failures with exponential backoff. Surface failed extractions in an admin view. Unsupported formats remain searchable by metadata tsvector.

### Pitfall 5: Search Vector Excludes Custom Properties (Phase 30)

The PostgreSQL trigger auto-updates the tsvector for `title`, `filename`, and `author` but not for `custom_properties` JSONB. Documents with important metadata in custom fields are unfindable by keyword search.

**Prevention:** Decide the searchability scope before writing the trigger. The recommended default for v1.3 is to exclude custom properties from the tsvector and expose them via JSONB operator filtering in the metadata search path. Document this decision so users understand what is and is not full-text searchable. The trigger can be extended later to include JSONB text values without changing the data model.

---

## Suggested Phase Structure

The architecture researcher dependency graph drives the build order. The critical path runs: types -> folders -> ACL -> search -> relationships -> browse UI -> saved searches.

### Phase 27: Document Type System

**Rationale:** Zero dependencies on other new features. Must execute before Phase 28 because it modifies the `Document` model (adds `document_type_id`), and consolidating Document model changes early avoids layered migrations. Provides metadata validation that improves document quality for all subsequent uploads. Low risk, clean scope.

- New: `DocumentType` model with self-referential `parent_type_id`, `document_type_service.py`, `document_types.py` router, request/response schemas
- Modified: `Document` model adds nullable `document_type_id` FK; `document_service` validates `custom_properties` against type schema on write
- Frontend: `DocumentTypesPage` (admin CRUD), `TypeSelector` dropdown, `TypeMetadataForm` (dynamic form from JSON Schema)
- New dependency: `jsonschema` package
- Pitfall to avoid: Schema evolution breaks existing docs -- validate on write only, block required-without-default field additions

### Phase 28: Cabinet/Folder Hierarchy + Document Filing

**Rationale:** Core structural infrastructure. Three subsequent phases (ACL inheritance, browse UI, saved searches) depend on folders existing. Filing and the folder model are inseparable and should ship together.

- New: `Folder` model (`parent_id`, `is_cabinet`, `acl_inherited`), `folder_documents` many-to-many association table, `folder_service.py` with recursive CTE helpers, `folders.py` router, schemas
- Modified: `Document` model adds nullable `owner_id` column (backfilled from `created_by`); document upload/CRUD endpoints accept optional `folder_id`
- Frontend: `FolderTree`, `FolderTreeNode`, `FolderBreadcrumb`, `CreateFolderDialog`, basic browse layout scaffold
- Events: `folder.created`, `folder.moved`, `document.filed`, `document.unfiled`
- Pitfall to avoid: Deletion cascading -- require empty folders, soft-delete, check workflow attachments before unfiling

### Phase 29: Folder ACL Inheritance

**Rationale:** Must follow Phase 28 (needs folders). Security layer required before the browse UI is exposed to general users in Phase 32. Entirely additive to existing `DocumentACL` -- no existing permissions are changed.

- New: `FolderACL` model (mirrors `DocumentACL` structure), `folder_acl_service.py` with recursive CTE ancestor walk
- Modified: `acl_service.check_permission()` gains folder ACL fallback path; `core/dependencies.py` gains `require_folder_permission` dependency
- ACL resolution order: (1) direct `DocumentACL`, (2) inherited `FolderACL` walking tree upward via recursive CTE, (3) workflow participant fallback, (4) open access backward compat
- Frontend: `FolderACLEditor` component
- Pitfall to avoid: Permission leaks -- no caching initially, fresh computation per request, comprehensive inheritance test suite required

### Phase 30: Full-Text Search + Content Extraction

**Rationale:** Independent of folder ACL, but placed after Phase 29 so search results can display folder paths (requires folder data to exist). Documents from Phase 27-28 onward are indexed from day one; admin reindex task backfills earlier uploads.

- New: `DocumentContentText` model with `content_search_vector` TSVECTOR and `extraction_status` enum; `search_service.py`; `content_extraction_service.py`; `search.py` router; `extract_document_text` and `reindex_all_documents` Celery tasks
- Modified: `Document` model adds nullable `search_vector` TSVECTOR column + GIN index + PostgreSQL trigger; document upload and checkin dispatch extraction task
- Frontend: `SearchPage`, `SearchBar`, `SearchResults` with `ts_headline` snippets, `SearchFacets` sidebar
- New dependencies: `PyPDF2`, `python-docx`
- Pitfall to avoid: Silent extraction failures (status tracking, admin view, retry with backoff); custom properties excluded from tsvector by default (document the decision)

### Phase 31: Document Relationships

**Rationale:** Independent of folders and search. Only requires the existing `Document` model. Low risk, clear scope, quick win that closes a Documentum feature gap before the final integration phase.

- New: `DocumentRelationship` model with `RelationshipType` enum (supersedes, references, is_part_of, related_to); `relationship_service.py`; endpoints under `/api/documents/{id}/relationships`
- Frontend: `RelationshipPanel` tab in existing `DocumentDetailPanel`
- No new dependencies, no schema changes to existing tables

### Phase 32: Document-First Navigation (Browse UI Integration)

**Rationale:** Integration phase requiring all of Phase 27-31 to be complete. Brings the document-centric paradigm together into a coherent UI. Default route change from `/inbox` to `/browse` signals the milestone completion.

- New: Full `BrowsePage` implementation (three-panel layout: folder tree left, content grid center, detail panel right)
- Modified: `App.tsx` default route `/inbox` -> `/browse`; `SidebarNav.tsx` restructured with Browse and Search as primary nav items; `DocumentDetailPanel` gains Location, Relationships, and Type sections; `DocumentTable` gains Type and Location columns; `DocumentDropZone` accepts optional `folderId` prop
- Performance: virtual list for large content grids, debounced tree expansion, React Query caching with appropriate stale times
- Pitfall to avoid: Slow initial tree load -- lazy-load children on expand, root shows cabinets only on mount

### Phase 33: Saved Searches / Smart Folders

**Rationale:** Depends on both search (Phase 30) and the browse UI (Phase 32). Smart folders appear as virtual nodes in the folder tree; they require both the query execution infrastructure and the tree component to render correctly.

- New: `SavedSearch` model with `query_definition` JSON and `show_in_tree` flag; `saved_search_service.py`; `saved_searches.py` router
- Modified: `SearchPage` gains Save this search button; `FolderTree` renders smart folder nodes with distinct icon when `show_in_tree = true`
- Pitfall to avoid: Complex saved search performance -- paginate results, 30-second TTL cache, loading states in UI

---

## Open Questions

These decisions are unresolved and must be handled during individual phase planning, not pre-decided here.

| Question | Relevant Phase | Why Unresolved |
|----------|---------------|----------------|
| Should `custom_properties` JSONB be included in the `search_vector` tsvector trigger? | Phase 30 | Requires product decision on user expectation vs. trigger complexity. Recommended default: exclude, expose via JSONB filtering. Confirm before writing trigger. |
| What is the maximum enforced folder depth? | Phase 28 | Architecture recommends 15 levels as service-layer limit. Confirm before hardcoding. |
| Should text extraction run for all existing documents on upgrade, or only new uploads going forward? | Phase 30 | Admin-triggered `reindex_all_documents` handles backfill, but timing and resource impact depend on existing document volume. Decide during phase planning. |
| Which additional file formats beyond PDF and .docx should be supported for text extraction in v1.3? | Phase 30 | Plain text (.txt) is trivial. RTF, HTML, .xlsx, .pptx each require additional packages. Confirm scope before implementation. |
| Should saved searches be user-private by default or shareable? | Phase 33 | `SavedSearch.is_public` flag exists in the model, but default behavior and UI treatment need a product decision. |

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All recommended technologies (PostgreSQL tsvector, adjacency list CTE, jsonschema, PyPDF2, python-docx) are mature and production-proven. Zero experimental choices. |
| Features | HIGH | Documentum ECM model is well-specified. Table stakes and anti-features are clear. Feature dependencies are fully mapped. |
| Architecture | HIGH | Both conflicts resolved with simpler, lower-risk alternatives consistent with the existing codebase patterns. The 7-table data model is fully specified with exact column definitions. |
| Pitfalls | HIGH | Pitfalls are grounded in concrete analysis of the existing schema (10+ FK references counted). Prevention strategies are specific and actionable, not theoretical. |

---

## Sources

Aggregated from all four research files:

- [PostgreSQL Full-Text Search Documentation](https://www.postgresql.org/docs/current/textsearch-tables.html) -- HIGH confidence
- [PostgreSQL GIN Index for Text Search](https://www.postgresql.org/docs/current/textsearch-indexes.html) -- HIGH confidence
- [PostgreSQL ltree Documentation](https://www.postgresql.org/docs/current/ltree.html) -- HIGH confidence (evaluated, not recommended)
- [SQLAlchemy 2.0 PostgreSQL Dialect](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html) -- HIGH confidence
- [jsonschema PyPI](https://pypi.org/project/jsonschema/) -- HIGH confidence
- [PyPDF2 PyPI](https://pypi.org/project/PyPDF2/) -- HIGH confidence
- [python-docx PyPI](https://pypi.org/project/python-docx/) -- HIGH confidence
- [Documentum Object Types](https://argondigital.com/blog/ecm/object-types/) -- MEDIUM confidence
- [Documentum Type Hierarchy](https://documentumexpert.wordpress.com/2012/08/11/hierarchical-list-of-documentum-types/) -- MEDIUM confidence
- Codebase analysis: all model, service, router, and frontend files examined -- HIGH confidence
