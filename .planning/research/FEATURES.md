# Feature Landscape: v1.3 Document-Centric ECM

**Domain:** Enterprise Content Management -- document-first ECM features
**Researched:** 2026-04-13

## Table Stakes

Features that make the system a genuine ECM platform. Missing any of these and it remains "a workflow engine with document attachments."

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Cabinet/folder hierarchy | Every ECM has folder-based organization. Users expect to browse documents by navigating a tree. | Medium | Adjacency list with parent_id. Cabinets are root folders (parent_id IS NULL, is_cabinet=true). |
| Folder CRUD + move | Users need to create, rename, move, and delete folders. Moving a folder moves its contents. | Medium | Move updates parent_id + revalidates name uniqueness in new parent. |
| Document-folder linking | Documents must live in folders. A document can exist in multiple folders (Documentum link/unlink). | Low | Many-to-many `folder_documents` join table. |
| Document type definitions | Admins define document types (Invoice, Contract, Policy) with type-specific required metadata. | Medium | `document_types` table with JSON Schema definition. Validates `custom_properties` on write. |
| Type inheritance | Types extend a base type. "Invoice" inherits common fields from "Financial Document." | Medium | Self-referential `parent_type_id`. Schema merging at validation time. |
| Full-text search | Users expect to search document content, not just titles. | Medium | PostgreSQL tsvector on documents (metadata) + document_content_text (body). GIN indexes. |
| Search results with ranking | Results sorted by relevance with snippets showing matches. | Low | ts_rank + ts_headline built into PostgreSQL. |
| Metadata search / filtering | Filter by type, author, date range, lifecycle state, custom properties. | Low | Standard SQL WHERE clauses + JSONB operators. |
| Folder-level ACL inheritance | Permissions on a cabinet flow down to children unless overridden. | High | Recursive CTE walks folder tree upward. Merge folder ACL with direct document ACL. |
| Breadcrumb navigation | Show full path: Cabinet > Folder > Subfolder > Document. | Low | Recursive CTE from folder to root. |
| Document-first browse UI | Folder tree + content grid as primary navigation. | High | New BrowsePage. Becomes default route (replacing /inbox). |

## Differentiators

Features beyond basic ECM that match Documentum's advanced capabilities.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Document relationships | Typed links: supersedes, references, is-part-of. Enables traceability. | Low | Junction table with relationship_type enum. |
| Saved searches / smart folders | Named queries appearing as folders in tree. | Medium | JSON query definition. Executed on access. Distinct icon in tree. |
| Multi-filing | Document in multiple folders simultaneously. | Low | Supported by folder_documents many-to-many. Needs "File to folder" UI action. |
| Type-specific metadata forms | Different types render different metadata forms. | Medium | Dynamic form generated from JSON Schema at frontend. |
| Content text extraction | Auto-extract searchable text from PDFs, Word docs. | Medium | Celery task: download from MinIO, extract, store in document_content_text. |

## Anti-Features

Features to explicitly NOT build in v1.3.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| dm_sysobject polymorphic base | Migrating documents table breaks 10+ FK references. Enormous risk. | Keep documents and folders as separate tables sharing BaseModel. |
| ltree PostgreSQL extension | Path desync bugs, label restrictions, unnecessary for shallow hierarchies. | Adjacency list with recursive CTE. |
| Elasticsearch integration | JVM service, sync complexity. Overkill for internal ECM. | PostgreSQL tsvector with GIN indexes. |
| Real-time collaborative editing | CRDT/OT complexity. Documentum uses check-in/check-out. | Keep existing check-in/check-out. |
| Content auto-classification (AI) | Scope creep. Not in Documentum spec. | Future milestone. |
| Version tree (branching) | Significant complexity. Linear versioning sufficient. | Keep linear major/minor versioning. |

## Feature Dependencies

```
Document Type System (independent) -----> Upload validates against type schema

Cabinet/Folder Hierarchy --> Document-Folder Linking --> Multi-filing
    |                              |
    v                              v
Folder ACL Inheritance      Document-First Browse UI
    |                              ^
    v                              |
Breadcrumb Navigation        Search Page UI <-- Full-Text Search
                                                      |
                                                      v
                                              Saved Searches / Smart Folders

Document Relationships (independent)
```

## MVP Recommendation

Prioritize:
1. Document type system (structured metadata, no external deps)
2. Cabinet/folder hierarchy + document filing (foundation for browse)
3. Folder ACL inheritance (security non-negotiable)
4. Full-text search + content extraction (core ECM expectation)
5. Document-first navigation UI (makes it usable)

Defer:
- Folder templates: Nice-to-have, post-v1.3
- Type-specific detail views: Generic detail view initially

## Sources

- Documentum specification (project reference)
- Existing codebase analysis (models, ACL, document model)
- [Documentum Object Types](https://argondigital.com/blog/ecm/object-types/) -- MEDIUM confidence
