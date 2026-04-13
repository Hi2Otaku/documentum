# Architecture Research: v1.3 Document-Centric ECM

**Domain:** Document-centric ECM integration into existing workflow engine
**Researched:** 2026-04-13
**Overall confidence:** HIGH

This document maps exactly how eight new ECM features integrate with the existing 26-phase codebase (~17,400 Python LOC, ~13,800 TypeScript LOC). Every recommendation accounts for existing models, services, routers, and frontend components.

---

## Critical Design Decisions

### Decision 1: Adjacency List + Recursive CTE (not ltree, not sysobject polymorphic base)

**Rejected: ltree extension.** Requires rewriting materialized paths for all descendants on every move/rename. The existing codebase uses zero PostgreSQL extensions beyond core. Adding ltree creates a maintenance dependency for marginal benefit -- cabinet/folder trees in an ECM are typically 3-8 levels deep, where recursive CTEs perform fine.

**Rejected: dm_sysobject polymorphic base table.** SQLAlchemy joined-table inheritance would require migrating the existing `documents` table to inherit from a new `sysobjects` table -- a destructive schema change touching every FK referencing `documents.id` (DocumentVersion, DocumentACL, WorkflowPackage, Rendition, Retention, Signature, VirtualDocumentChild). The migration risk is enormous for the existing 26-phase codebase. Instead, folders and documents share the same `BaseModel` (which already provides id, timestamps, soft-delete) and are kept as separate tables. This is the pragmatic choice.

**Chosen: Adjacency list with `parent_id` FK on `folders`.** Consistent with existing codebase patterns. Augmented with recursive CTE helper functions for tree queries (breadcrumb, subtree listing, ancestor walk for ACL). If performance bottlenecks appear later, add a denormalized `materialized_path` TEXT column without changing the core model.

### Decision 2: PostgreSQL tsvector for Full-Text Search (not Elasticsearch/Meilisearch)

The existing stack is PostgreSQL-centric. Adding an external search engine is premature for an internal tool. PostgreSQL's tsvector with GIN indexes handles full-text search well up to ~1M documents. The tsvector approach requires zero new infrastructure and is maintained by a PostgreSQL trigger (no application-level index sync). If scale demands it later, Meilisearch can be added behind the same search service interface.

### Decision 3: Separate `document_content_text` Table for Extracted Text

Extracted text from document files (PDFs, Word docs) can be megabytes. Storing it directly on the `documents` table would bloat every query that touches documents. A separate `document_content_text` table (1:1 with documents) keeps the documents table lean. The content search vector lives on this separate table and is JOINed only during search queries.

### Decision 4: Single `folders` Table for Cabinets + Folders

In Documentum, `dm_cabinet` extends `dm_folder`. We collapse both into one table with an `is_cabinet` boolean. Cabinets are root folders (`parent_id IS NULL` + `is_cabinet = true`). This avoids unnecessary join complexity.

---

## Data Model Changes

### New Tables/Models

#### 1. `document_types` -- new model `DocumentType`

Defines custom document types with metadata schemas. The type system Documentum calls dm_type.

```python
# src/app/models/document_type.py
class DocumentType(BaseModel):
    __tablename__ = "document_types"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_type_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("document_types.id"), nullable=True
    )
    # JSON Schema defining required/optional metadata fields
    metadata_schema: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_abstract: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    parent_type: Mapped["DocumentType | None"] = relationship(remote_side="DocumentType.id")
```

**Rationale:** `metadata_schema` stores a JSON Schema document that validates `Document.custom_properties`. Type inheritance via `parent_type_id` means a child type's schema extends the parent's. Validation at service layer via `jsonschema` library.

#### 2. `folders` -- new model `Folder`

Unified model for dm_cabinet and dm_folder.

```python
# src/app/models/folder.py
class Folder(BaseModel):
    __tablename__ = "folders"
    __table_args__ = (
        UniqueConstraint("parent_id", "name", name="uq_folder_name_in_parent"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("folders.id"), nullable=True, index=True
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("users.id"), nullable=False
    )
    is_cabinet: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    acl_inherited: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    parent: Mapped["Folder | None"] = relationship(
        remote_side="Folder.id", back_populates="children"
    )
    children: Mapped[list["Folder"]] = relationship(back_populates="parent")
```

**Constraint:** Cabinets have `parent_id IS NULL` + `is_cabinet = true`. Non-cabinet folders must have a parent. Enforced via DB check constraint in migration.

#### 3. `folder_documents` -- association table

Many-to-many: documents can live in multiple folders (Documentum link/unlink semantics).

```python
# src/app/models/folder.py
folder_documents = Table(
    "folder_documents",
    BaseModel.metadata,
    Column("folder_id", Uuid(), ForeignKey("folders.id"), primary_key=True),
    Column("document_id", Uuid(), ForeignKey("documents.id"), primary_key=True),
    Column("linked_at", DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
    Column("linked_by", Uuid(), nullable=True),
)
```

#### 4. `folder_acl` -- new model `FolderACL`

Mirror of existing `DocumentACL` but for folders. Enables ACL inheritance down the folder tree.

```python
# src/app/models/folder_acl.py (or extend acl.py)
class FolderACL(BaseModel):
    __tablename__ = "folder_acl"
    __table_args__ = (
        UniqueConstraint(
            "folder_id", "principal_id", "principal_type", "permission_level",
            name="uq_folder_acl_entry",
        ),
    )

    folder_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("folders.id"), nullable=False, index=True
    )
    principal_id: Mapped[uuid.UUID] = mapped_column(Uuid(), nullable=False)
    principal_type: Mapped[str] = mapped_column(String(20), nullable=False)
    permission_level: Mapped[str] = mapped_column(
        Enum(PermissionLevel, name="permissionlevel"), nullable=False
    )
```

#### 5. `document_relationships` -- new model `DocumentRelationship`

Typed relationships between documents.

```python
# src/app/models/document_relationship.py
class RelationshipType(str, enum.Enum):
    SUPERSEDES = "supersedes"
    REFERENCES = "references"
    IS_PART_OF = "is_part_of"
    RELATED_TO = "related_to"

class DocumentRelationship(BaseModel):
    __tablename__ = "document_relationships"
    __table_args__ = (
        UniqueConstraint(
            "source_document_id", "target_document_id", "relationship_type",
            name="uq_document_relationship",
        ),
    )

    source_document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("documents.id"), nullable=False, index=True
    )
    target_document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("documents.id"), nullable=False, index=True
    )
    relationship_type: Mapped[str] = mapped_column(
        Enum(RelationshipType, name="relationshiptype"), nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
```

#### 6. `saved_searches` -- new model `SavedSearch`

Named queries acting as virtual folders.

```python
# src/app/models/saved_search.py
class SavedSearch(BaseModel):
    __tablename__ = "saved_searches"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("users.id"), nullable=False
    )
    query_definition: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    show_in_tree: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
```

#### 7. `document_content_text` -- new model `DocumentContentText`

Extracted text from document files for full-text content search.

```python
# src/app/models/document_content.py
class DocumentContentText(BaseModel):
    __tablename__ = "document_content_text"

    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("documents.id"), nullable=False, unique=True
    )
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )  # pending, processing, completed, failed
    content_search_vector: Mapped[None] = mapped_column(
        TSVECTOR, nullable=True  # GIN indexed
    )
```

### Modified Existing Models

#### `Document` model (`src/app/models/document.py`) -- 3 new columns

```python
# NEW columns to add:
document_type_id: Mapped[uuid.UUID | None] = mapped_column(
    Uuid(), ForeignKey("document_types.id"), nullable=True, index=True
)

search_vector: Mapped[None] = mapped_column(
    TSVECTOR, nullable=True  # GIN index + PostgreSQL trigger
)

owner_id: Mapped[uuid.UUID | None] = mapped_column(
    Uuid(), ForeignKey("users.id"), nullable=True
)
```

**Migration strategy for `search_vector`:**
1. Add nullable TSVECTOR column
2. Create GIN index: `CREATE INDEX ix_documents_search_vector ON documents USING GIN(search_vector)`
3. Create PostgreSQL trigger to auto-update on INSERT/UPDATE of title, filename, author
4. Backfill existing rows in the same migration

**Migration for `owner_id`:** Backfill from `created_by` (stored as string UUID): `UPDATE documents SET owner_id = created_by::uuid WHERE created_by IS NOT NULL`

#### `enums.py` -- add `RelationshipType` enum

#### `models/__init__.py` -- register all new models

### Key Relationships

```
DocumentType (1) ------< (many) Document [via document_type_id]
DocumentType (1) ------< (many) DocumentType [self-ref: parent_type_id]

Folder (1) ------< (many) Folder [self-ref: parent_id]
Folder (many) >---< (many) Document [via folder_documents]
Folder (1) ------< (many) FolderACL

Document (1) ------< (many) DocumentRelationship [as source]
Document (1) ------< (many) DocumentRelationship [as target]
Document (1) ------< (0..1) DocumentContentText

User (1) ------< (many) SavedSearch
User (1) ------< (many) Folder [as owner]
```

**All existing relationships preserved unchanged:** Document->DocumentVersion->Rendition, Document->DocumentACL, Document->WorkflowPackage, Document->VirtualDocumentChild, Document->RetentionPolicy/LegalHold, Document->DocumentSignature.

---

## API Surface

### New Endpoints

#### Folder/Cabinet Management -- `src/app/routers/folders.py`

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/folders` | Create folder or cabinet |
| `GET` | `/api/folders` | List root cabinets |
| `GET` | `/api/folders/{id}` | Get folder details |
| `GET` | `/api/folders/{id}/children` | List child folders + documents |
| `GET` | `/api/folders/{id}/tree` | Get subtree (recursive, depth-limited) |
| `PUT` | `/api/folders/{id}` | Update folder metadata |
| `DELETE` | `/api/folders/{id}` | Delete folder (must be empty) |
| `POST` | `/api/folders/{id}/documents/{doc_id}` | File document into folder |
| `DELETE` | `/api/folders/{id}/documents/{doc_id}` | Unlink document from folder |
| `POST` | `/api/folders/{id}/move` | Move folder to new parent |
| `GET` | `/api/folders/{id}/breadcrumb` | Path from root to folder |

#### Folder ACL -- under folders router

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/folders/{id}/acl` | List folder ACL entries |
| `POST` | `/api/folders/{id}/acl` | Add ACL entry |
| `DELETE` | `/api/folders/{id}/acl/{entry_id}` | Remove ACL entry |
| `GET` | `/api/folders/{id}/effective-acl` | Computed inherited + direct ACL |

#### Document Types -- `src/app/routers/document_types.py`

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/document-types` | Create type (admin) |
| `GET` | `/api/document-types` | List all types |
| `GET` | `/api/document-types/{id}` | Get type with schema |
| `PUT` | `/api/document-types/{id}` | Update type (admin) |
| `DELETE` | `/api/document-types/{id}` | Delete if unused |
| `GET` | `/api/document-types/{id}/schema` | Merged schema (type + ancestors) |

#### Full-Text Search -- `src/app/routers/search.py`

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/search` | Full-text search with filters and facets |
| `POST` | `/api/search/reindex` | Trigger full reindex (admin) |

#### Document Relationships -- extend `src/app/routers/documents.py`

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/documents/{id}/relationships` | List relationships |
| `POST` | `/api/documents/{id}/relationships` | Create relationship |
| `DELETE` | `/api/documents/{id}/relationships/{rel_id}` | Remove relationship |

#### Saved Searches -- `src/app/routers/saved_searches.py`

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/saved-searches` | Save a search |
| `GET` | `/api/saved-searches` | List user's + public saved searches |
| `GET` | `/api/saved-searches/{id}` | Get definition |
| `GET` | `/api/saved-searches/{id}/results` | Execute saved search |
| `PUT` | `/api/saved-searches/{id}` | Update |
| `DELETE` | `/api/saved-searches/{id}` | Delete |

### Modified Endpoints

| Endpoint | Change |
|----------|--------|
| `POST /api/documents/` | Add optional `document_type_id` and `folder_id` params; validate custom_properties against type schema; dispatch text extraction task |
| `PUT /api/documents/{id}` | Add `document_type_id` to payload; re-validate custom_properties on type change |
| `GET /api/documents/` | Add `folder_id`, `document_type_id`, `q` query params for filtering |
| `DELETE /api/documents/{id}` | Clean up `folder_documents` entries |

### New Services

| Service File | Purpose |
|-------------|---------|
| `folder_service.py` | Folder/cabinet CRUD, tree queries (recursive CTE), filing, move |
| `document_type_service.py` | Type CRUD, schema inheritance, metadata validation |
| `search_service.py` | Full-text search, tsvector queries, faceted filtering, ranking |
| `relationship_service.py` | Document relationship CRUD |
| `saved_search_service.py` | Saved search CRUD, execution |
| `folder_acl_service.py` | Folder ACL CRUD, inheritance computation |
| `content_extraction_service.py` | Text extraction from files (PDF, Word, etc.) |

### New Celery Tasks

| Task | Trigger | Purpose |
|------|---------|---------|
| `extract_document_text` | On upload/checkin | Extract text from document file for search index |
| `reindex_all_documents` | Admin manual trigger | Full reindex of all document search vectors |

---

## Frontend Architecture

### New Pages/Routes

Add to `App.tsx`:

```typescript
<Route path="/browse" element={<BrowsePage />} />
<Route path="/browse/:folderId" element={<BrowsePage />} />
<Route path="/search" element={<SearchPage />} />
<Route element={<AdminRoute />}>
  <Route path="/admin/document-types" element={<DocumentTypesPage />} />
</Route>
```

#### BrowsePage -- Document-centric navigation hub

- **Left panel:** Folder tree (collapsible, lazy-loaded via `GET /api/folders/{id}/children`)
  - Root shows cabinets; expand to see child folders
  - Smart folders (saved searches with `show_in_tree=true`) with distinct icon
  - Context menu: New Folder, Rename, Delete, Properties, Permissions
- **Main panel:** Contents of selected folder (child folders + documents as table/grid)
  - Sort by name, date, type, size
  - Multi-select for batch operations
  - Upload drop zone auto-files into current folder
- **Right panel:** Detail panel for selected item (reuses `DocumentDetailPanel` pattern)
- **Breadcrumb bar:** Clickable path from root cabinet to current folder

#### SearchPage -- Full-text search with facets

- Search bar with debounced query input
- Results with highlighted snippets
- Facet sidebar: document type, lifecycle state, date range, folder, author
- "Save this search" button
- Saved searches list in sidebar

#### DocumentTypesPage (admin)

- CRUD table for document types
- Type hierarchy tree view
- JSON Schema editor for metadata_schema
- Preview of the metadata form users see during upload

### Modified Components

| Component | Changes |
|-----------|---------|
| `DocumentDetailPanel.tsx` | Add Location (folder paths), Relationships tab, Type display with type-specific metadata |
| `DocumentTable.tsx` | Add Type and Location columns; accept `folderId` prop for folder-scoped view |
| `DocumentDropZone.tsx` | Accept optional `folderId` prop for auto-filing |
| `DocumentsPage.tsx` | Add document type filter, full-text search input |
| `SidebarNav.tsx` | Restructure: Browse and Search as primary items |

### New Frontend Components

| Component | Purpose |
|-----------|---------|
| `components/folders/FolderTree.tsx` | Recursive tree with lazy loading, context menu |
| `components/folders/FolderTreeNode.tsx` | Single expandable node |
| `components/folders/FolderBreadcrumb.tsx` | Clickable path |
| `components/folders/CreateFolderDialog.tsx` | Create folder/cabinet |
| `components/folders/FolderACLEditor.tsx` | ACL management for folders |
| `components/search/SearchBar.tsx` | Full-text search input |
| `components/search/SearchResults.tsx` | Results with snippets |
| `components/search/SearchFacets.tsx` | Facet filter sidebar |
| `components/search/SaveSearchDialog.tsx` | Save current search |
| `components/document-types/TypeSelector.tsx` | Type selection dropdown |
| `components/document-types/TypeMetadataForm.tsx` | Dynamic form from JSON Schema |
| `components/documents/RelationshipPanel.tsx` | View/manage relationships |

### Navigation Changes

Sidebar nav restructure (`SidebarNav.tsx`):

```typescript
const NAV_ITEMS: NavItem[] = [
  { icon: FolderTree, label: "Browse", route: "/browse", adminOnly: false },    // NEW primary
  { icon: Search, label: "Search", route: "/search", adminOnly: false },         // NEW
  { icon: Inbox, label: "Inbox", route: "/inbox", adminOnly: false },
  { icon: FileText, label: "Documents", route: "/documents", adminOnly: false },
  { icon: GitBranch, label: "Workflows", route: "/workflows", adminOnly: false },
  { icon: LayoutTemplate, label: "Templates", route: "/templates", adminOnly: false },
  { icon: BarChart3, label: "Dashboard", route: "/dashboard", adminOnly: true },
  { icon: Database, label: "Query", route: "/query", adminOnly: true },
  { icon: Settings2, label: "Doc Types", route: "/admin/document-types", adminOnly: true },
];
```

**Default route change:** Root redirect changes from `/inbox` to `/browse` -- signaling the document-centric reorientation.

### New API Client Modules

`frontend/src/api/folders.ts`, `search.ts`, `documentTypes.ts`, `savedSearches.ts`

---

## Build Order

### Dependency Graph

```
Document Types (independent)
    |
    v
Folders/Cabinets ---------> Folder ACL Inheritance
    |                              |
    +---> Document Filing ---------+
    |                              |
    v                              v
Full-Text Search          Browse UI (integration phase)
    |                              ^
    v                              |
Document Relationships      all features feed in
    |
    v
Saved Searches / Smart Folders (needs search + browse)
```

### Suggested Phase Sequence

#### Phase 27: Document Type System
**Why first:** Zero dependencies on other new features. Modifies Document model (adds `document_type_id`), so do this before other Document-modifying phases. Provides metadata validation that improves document quality for all subsequent uploads. Low risk, clear scope.

- New: `DocumentType` model, `document_type_service.py`, router, schemas
- Modify: `Document` model (+document_type_id), `document_service` (schema validation)
- Frontend: `DocumentTypesPage`, `TypeSelector`, `TypeMetadataForm`
- New dependency: `jsonschema` package

#### Phase 28: Cabinet/Folder Hierarchy + Document Filing
**Why second:** Core infrastructure. Three later phases depend on folders existing. Filing and folders are inseparable.

- New: `Folder` model, `folder_documents` table, `folder_service.py`, router, schemas
- New column: `Document.owner_id` (backfill from `created_by`)
- Frontend: `FolderTree`, `FolderBreadcrumb`, `CreateFolderDialog`, basic browse layout
- Events: `folder.created`, `folder.moved`, `document.filed`, `document.unfiled`

#### Phase 29: Folder ACL Inheritance
**Why third:** Needs folders. Critical security layer before browse UI goes to production users.

- New: `FolderACL` model, `folder_acl_service.py`
- Modify: `acl_service.check_permission()` -- add folder ACL fallback path
- Modify: `core/dependencies.py` -- extend `require_permission` for folder scoping
- Frontend: `FolderACLEditor`

**Extended ACL resolution order:**
1. Direct `DocumentACL` (existing, unchanged)
2. Folder ACL inheritance walk via recursive CTE (new)
3. Workflow participant fallback (existing)
4. No ACL = open access (existing backward compat)

#### Phase 30: Full-Text Search
**Why fourth:** Independent of folders but placed after them so results show folder paths.

- New: `Document.search_vector` (TSVECTOR + GIN index + trigger), `DocumentContentText` model
- New: `search_service.py`, `content_extraction_service.py`, search router
- New Celery task: `extract_document_text`
- Modify: document upload/checkin to dispatch extraction
- Frontend: `SearchPage`, `SearchBar`, `SearchResults`, `SearchFacets`
- New dependencies: `PyPDF2`, `python-docx`

**Search query combines metadata + content vectors:**
```sql
SELECT d.*, ts_rank(d.search_vector, q) AS meta_rank,
       ts_rank(ct.content_search_vector, q) AS content_rank
FROM documents d
LEFT JOIN document_content_text ct ON ct.document_id = d.id,
     to_tsquery('english', :query) q
WHERE d.search_vector @@ q OR ct.content_search_vector @@ q
ORDER BY (ts_rank(d.search_vector, q) * 2 + ts_rank(ct.content_search_vector, q)) DESC
```

#### Phase 31: Document Relationships
**Why fifth:** Simple, independent. Only needs existing Document model. Low risk, quick win.

- New: `DocumentRelationship` model, `RelationshipType` enum, `relationship_service.py`
- New endpoints under `/api/documents/{id}/relationships`
- Frontend: `RelationshipPanel` in `DocumentDetailPanel`

#### Phase 32: Document-First Navigation (Browse UI Integration)
**Why sixth:** Integration phase. Requires folders (28), ACL (29), search (30), types (27), relationships (31). Brings the document-centric paradigm together.

- New: `BrowsePage` (full implementation)
- Modify: `App.tsx` default route `/inbox` -> `/browse`
- Modify: `SidebarNav.tsx` -- restructure with Browse and Search as primary
- Modify: `DocumentDetailPanel` -- add Location, Relationships, Type sections
- Modify: `DocumentTable` -- add Type, Location columns
- Performance: virtualized list, debounced tree expansion, React Query caching

#### Phase 33: Saved Searches / Smart Folders
**Why last:** Depends on search (30) and browse UI (32) both existing.

- New: `SavedSearch` model, `saved_search_service.py`, router
- Frontend: `SaveSearchDialog`, smart folder nodes in `FolderTree`
- Modify: `SearchPage` -- "Save this search" button

---

## Integration Points with Existing System

### Event Bus

All new features emit via `event_bus.emit()` (existing singleton in `src/app/services/event_bus.py`). New event types: `document_type.*`, `folder.*`, `document.filed/unfiled`, `folder_acl.*`, `document.relationship_*`, `saved_search.*`. These feed the notification system (Phase 16) and can trigger event-driven workflow activities (Phase 19).

### ACL System

Existing `DocumentACL` + `check_permission()` in `acl_service.py` (lines 136-218) unchanged. Extension is additive: when no direct document ACL exists and the document is filed in a folder, walk up the folder tree checking `FolderACL`. The `require_permission` FastAPI dependency in `core/dependencies.py` needs a parallel `require_folder_permission` for folder endpoints.

### Workflow Engine

`WorkflowPackage.document_id` FK unchanged. Workflows don't need to know about folders. Only UI change: workflow package display shows document's folder path for context. Optional: document types can restrict valid lifecycle states via `metadata_schema`.

### Audit Trail

All operations use existing `create_audit_record()`. New entity_type values: `folder`, `folder_acl`, `document_type`, `document_relationship`, `saved_search`.

### Retention System

Documents under retention/legal hold cannot be unfiled from their last folder. `folder_service.unfile_document()` must check `retention_service.check_document_deletable()` when the document would have zero remaining folder links.

### Virtual Documents

Virtual documents (Phase 21) don't participate in folder hierarchy. No changes needed.

### Renditions

Text extraction (Phase 30) can reuse the rendition worker's LibreOffice installation for extracting text from Office formats.

### Existing Search/Query

The existing `/api/query` (DQL-like, admin-only) coexists with new `/api/search` (user-facing full-text). Different purposes: search finds by content keywords; query handles structured metadata/workflow queries.

---

## Component Boundary Summary

```
EXISTING (modify)                          NEW (create)
=================                          ============

models/
  document.py ......... +document_type_id,   document_type.py
                         +search_vector,      folder.py (+ folder_documents)
                         +owner_id            folder_acl.py
  enums.py ............ +RelationshipType    document_relationship.py
  __init__.py ......... +new imports          document_content.py
                                              saved_search.py

services/
  acl_service.py ...... +folder ACL fallback  folder_service.py
  document_service.py . +type validation,     document_type_service.py
                         +folder filing,       search_service.py
                         +text extraction      relationship_service.py
                         dispatch              folder_acl_service.py
                                              saved_search_service.py
                                              content_extraction_service.py

routers/
  documents.py ........ +type/folder params   folders.py
                         +relationship         document_types.py
                         endpoints             search.py
                                              saved_searches.py

tasks/
  (existing unchanged)                        content_extraction.py

schemas/
  document.py ......... +type_id, folder_id   folder.py
                                              document_type.py
                                              search.py
                                              document_relationship.py
                                              saved_search.py

frontend/
  pages/ .............. DocumentsPage mods    BrowsePage.tsx
  App.tsx ............. +routes, / -> /browse  SearchPage.tsx
  components/layout/                          DocumentTypesPage.tsx
    SidebarNav.tsx .... +Browse,Search,Types
  components/documents/                       folders/ (5 components)
    DocumentDetailPanel +location,type,rels   search/ (4 components)
    DocumentTable ..... +type,location cols   document-types/ (2 components)
    DocumentDropZone .. +folderId prop        documents/RelationshipPanel.tsx
  api/ ................ documents.ts mods     folders.ts, search.ts,
                                              documentTypes.ts, savedSearches.ts
```

---

## Scalability Considerations

| Concern | At 1K docs | At 100K docs | At 1M docs |
|---------|------------|--------------|------------|
| Folder tree loading | Eager load all | Lazy-load children, React Query cache | Virtual scrolling, paginate per level |
| Full-text search | tsvector trivial | GIN index <100ms | Add pg_trgm for fuzzy; consider Meilisearch |
| ACL inheritance walk | 3-5 levels, trivial | Cache effective ACL in Redis (60s TTL) | Materialize effective ACL table |
| Content text extraction | Sync ok | Celery queue essential | Multiple extraction workers |
| Type schema validation | In-memory <1ms | Same | Cache compiled schemas per type |

---

## Sources

- [PostgreSQL Full-Text Search: Tables and Indexes](https://www.postgresql.org/docs/current/textsearch-tables.html) -- HIGH confidence
- [PostgreSQL GIN Index for Text Search](https://www.postgresql.org/docs/current/textsearch-indexes.html) -- HIGH confidence
- [PostgreSQL ltree Extension](https://www.postgresql.org/docs/current/ltree.html) -- HIGH confidence (evaluated, not recommended)
- [SQLAlchemy PostgreSQL TSVECTOR](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html) -- HIGH confidence
- [Documentum Object Types](https://argondigital.com/blog/ecm/object-types/) -- MEDIUM confidence
- [Documentum Type Hierarchy](https://documentumexpert.wordpress.com/2012/08/11/hierarchical-list-of-documentum-types/) -- MEDIUM confidence
- Codebase analysis: all model, service, router, and frontend files examined -- HIGH confidence
