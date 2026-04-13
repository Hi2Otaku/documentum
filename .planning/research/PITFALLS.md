# Domain Pitfalls: v1.3 Document-Centric ECM

**Domain:** Adding document-centric ECM features to existing workflow engine
**Researched:** 2026-04-13

## Critical Pitfalls

### Pitfall 1: ACL Inheritance Creates Permission Leaks

**What goes wrong:** Folder ACL changes don't propagate correctly to documents. A restricted document becomes accessible because its parent folder's ACL was relaxed and stale cached permissions are served.

**Why it happens:** ACL inheritance computed by walking folder tree. Premature caching with wrong invalidation serves stale permissions.

**Consequences:** Security vulnerability. Restricted documents accessible to unauthorized users.

**Prevention:**
- Compute effective permissions fresh on every request initially (no caching until performance data demands it)
- When caching: invalidate on ACL change, folder move, inherit_acl flag change
- Always filter results through ACL checks -- never return unfiltered lists
- Comprehensive tests: direct ACL, inherited, override, folder move, multi-filing with different folder ACLs

**Detection:** Audit log review. Automated test suite with inheritance scenarios.

### Pitfall 2: Polymorphic Base Table Migration Destroys Existing Schema

**What goes wrong:** Introducing a `sysobjects` polymorphic base table requires moving `documents.id` to FK to `sysobjects.id`. Every table referencing `documents.id` (10+ tables: DocumentVersion, DocumentACL, WorkflowPackage, Rendition, RetentionPolicy, LegalHold, DocumentSignature, VirtualDocumentChild) must be migrated.

**Why it happens:** Over-engineering the Documentum dm_sysobject concept.

**Consequences:** Broken foreign keys, failed migrations, potential data loss.

**Prevention:** Do NOT introduce a polymorphic sysobject base table. Keep `documents` and `folders` as separate tables extending `BaseModel`. This is the v1.3 architecture decision.

**Detection:** Flag any proposal for a `sysobjects` table as rejected.

### Pitfall 3: Folder Deletion Cascading to Workflow-Attached Documents

**What goes wrong:** Deleting a folder cascades to delete or orphan documents attached to active workflows.

**Why it happens:** CASCADE on folder_documents FK, or hard-delete without checking workflow attachments.

**Consequences:** Active workflows lose document packages. Work items reference missing documents.

**Prevention:**
- Require folders to be empty before deletion
- Soft-delete only (is_deleted = true)
- Check all folder documents for active workflow attachments
- Check retention/legal hold before unfiling last folder link

**Detection:** Service-layer validation. No CASCADE on folder_documents.

## Moderate Pitfalls

### Pitfall 4: Text Extraction Failures Silently Kill Searchability

**What goes wrong:** Celery text extraction fails (corrupt PDF, unsupported format) and document never appears in search results.

**Prevention:**
- Track `extraction_status`: pending/processing/completed/failed/unsupported
- Log failures at WARNING level with document_id
- Admin UI showing failed extractions
- Retry with backoff for transient failures
- 60-second timeout per document
- Unsupported formats still searchable by metadata

### Pitfall 5: Document Type Schema Evolution Breaks Existing Documents

**What goes wrong:** Type schema changes (new required field) but existing documents lack the field.

**Prevention:**
- Validate on write only, never on read
- New fields optional by default or provide default value
- Migration utility for backfilling when schema changes
- Block adding required fields without defaults at service layer

### Pitfall 6: Recursive CTE Performance on Deep/Wide Trees

**What goes wrong:** Unexpectedly deep (20+ levels) or wide (thousands of children) hierarchies slow down.

**Prevention:**
- Enforce max folder depth (15 levels) at service layer
- Paginate children queries
- Index on `folders.parent_id`
- Lazy-load tree nodes in frontend
- Monitor with realistic data volumes

### Pitfall 7: Search Vector Misses Custom Properties

**What goes wrong:** PostgreSQL trigger updates tsvector for title/filename/author but not custom_properties JSONB. Documents with important metadata in custom_properties are unfindable.

**Prevention:**
- Decide early: include custom_properties in search vector?
- If yes: trigger-based approach extracting text values from JSONB
- If no (recommended initially): separate metadata filtering via JSONB operators, add to tsvector later
- Document the decision so users know what is/isn't searchable

### Pitfall 8: ltree Path Desync Bugs

**What goes wrong:** If ltree were used: materialized path gets out of sync with parent_id after concurrent moves or failed transactions.

**Prevention:** This pitfall is why v1.3 uses adjacency list + recursive CTE instead of ltree. No materialized path means no desync risk.

## Minor Pitfalls

### Pitfall 9: Slow Folder Tree Initial Load

**What goes wrong:** Loading entire tree on page mount takes noticeable time.

**Prevention:** Lazy-load: fetch root cabinets initially, children on expand. React Query staleTime for caching.

### Pitfall 10: Saved Search Query Performance

**What goes wrong:** Complex saved searches execute slowly every time smart folder is opened.

**Prevention:** Paginate results. Loading state in UI. Cache with short TTL (30s).

### Pitfall 11: Breadcrumb N+1 Queries

**What goes wrong:** Loading each ancestor folder individually.

**Prevention:** Single recursive CTE returning all ancestors. Cache recently accessed breadcrumbs.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Document type system (27) | Schema evolution breaks existing docs (5) | Validate on write only, additive changes |
| Folders + filing (28) | Deletion cascading (3) | Require empty folders, soft-delete |
| Folder ACL (29) | Permission leaks (1) | No caching initially, comprehensive tests |
| Full-text search (30) | Silent extraction failures (4) | Track status, monitoring, retry |
| Full-text search (30) | Custom properties not searchable (7) | Decide scope early, metadata filters |
| Browse UI (32) | Slow tree loading (9) | Lazy-load, React Query cache |
| Saved searches (33) | Complex query performance (10) | Paginate, cache with TTL |

## Sources

- Codebase analysis: 10+ tables reference documents.id -- HIGH confidence
- PostgreSQL recursive CTE performance -- HIGH confidence
- PostgreSQL tsvector trigger limitations -- HIGH confidence
- Documentum ACL inheritance model -- MEDIUM confidence
