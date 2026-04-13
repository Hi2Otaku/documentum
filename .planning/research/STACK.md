# Stack Research: v1.3 Document-Centric ECM

**Project:** Documentum Workflow Clone - v1.3 Document-Centric ECM
**Researched:** 2026-04-13
**Focus:** Stack additions for cabinet/folder hierarchy, document types, full-text search, relationships, saved searches

---

## New Dependencies Required

### Backend (Python)

| Package | Version | Purpose | Why |
|---------|---------|---------|-----|
| jsonschema | 4.x | JSON Schema validation for document type metadata | Validates `Document.custom_properties` against the type's `metadata_schema`. Standard library for JSON Schema validation. Pydantic alone cannot validate arbitrary user-defined schemas at runtime. |
| PyPDF2 | 3.x | Text extraction from PDF documents | Lightweight, pure Python. Extracts text for full-text search indexing. Chosen over PyMuPDF (C dependency, larger install) and Apache Tika (requires JVM). Sufficient for text extraction; not doing layout analysis. |
| python-docx | 1.1.x | Text extraction from Word documents | Extract text from .docx files for full-text search indexing. Lightweight, pure Python. |

### Frontend (npm)

No new packages required. The folder tree component will be built with existing shadcn/ui primitives (Collapsible, Button, DropdownMenu, ScrollArea) and React Query for data fetching. This avoids dependency on beta-stage tree libraries like @headless-tree which may have stability issues. For ECM folder trees (typically 3-8 levels, hundreds of nodes), a custom implementation is straightforward and gives full control over behavior.

### PostgreSQL Extensions

None required. The existing PostgreSQL 16+ installation already has built-in tsvector/tsquery support for full-text search. No ltree extension needed -- adjacency list with recursive CTE is used for folder hierarchy.

---

## Full-Text Search: PostgreSQL tsvector

**Recommendation: Use PostgreSQL's built-in tsvector/tsquery full-text search.**

### Why tsvector wins for this project

1. **No new infrastructure.** Already running PostgreSQL 16+. No Elasticsearch/Meilisearch/Typesense needed.
2. **Data consistency.** tsvector lives in the same database. No sync lag, no dual-write problems.
3. **Scale is appropriate.** Handles millions of documents with GIN indexes. Internal-use ECM with well under 1M docs.
4. **Sufficient features.** Stemming, stop words, ranking (ts_rank), phrase search, prefix matching, weighted fields, boolean operators.
5. **Already integrated.** SQLAlchemy 2.0 has native `func.to_tsvector()`, `func.to_tsquery()`, `func.ts_rank()` support.

### Implementation approach

- TSVECTOR column on `documents` table maintained by PostgreSQL trigger (not GENERATED, because we need cross-table content)
- Separate `document_content_text` table with its own TSVECTOR + GIN index for extracted body text
- Search query JOINs both vectors, weights metadata higher than body content
- Trigger auto-updates on INSERT/UPDATE of title, filename, author

### When to reconsider (external search engine)

- If fuzzy/typo-tolerant search becomes a hard requirement
- If document count exceeds 5M+ with sub-50ms latency requirement
- If multi-language documents need language auto-detection

**Confidence: HIGH**

---

## Hierarchy Approach: Adjacency List + Recursive CTE

**Recommendation: Use standard `parent_id` FK with recursive CTE queries.**

### Why adjacency list (not ltree)

1. **No PostgreSQL extension needed.** Keeps the stack simple and portable.
2. **No path desync risk.** ltree requires maintaining a materialized path that must stay in sync with parent_id on every move. This is a known source of bugs.
3. **No label format restrictions.** ltree labels can only contain alphanumeric chars and underscores. Folder names with spaces, dots, or Unicode require sanitization and separate display names.
4. **Sufficient performance.** ECM folder trees are typically 3-8 levels deep. Recursive CTEs with proper indexing handle this in single-digit milliseconds.
5. **Consistent with codebase.** The existing codebase uses zero PostgreSQL extensions. Standard FK relationships throughout.

### When to reconsider (ltree or materialized path)

- If folder trees regularly exceed 15+ levels deep
- If "find all descendants" queries are called hundreds of times per second
- If breadcrumb computation becomes a measurable bottleneck

At that point, add a denormalized `materialized_path` TEXT column alongside parent_id without changing the model.

**Confidence: HIGH**

---

## Existing Stack Handles These (No additions needed)

| Capability | Existing Component | How It Covers v1.3 |
|------------|-------------------|---------------------|
| Document type metadata schemas | PostgreSQL JSON + Pydantic | Type schemas stored as JSON in `document_types` table. `custom_properties` validated against schema via `jsonschema` at service layer. |
| ACL inheritance | PostgreSQL + existing ACL model | New `FolderACL` table mirrors `DocumentACL`. Compute effective permissions by walking folder tree with recursive CTE. |
| Document relationships | PostgreSQL FKs + junction table | `document_relationships` table with source_id, target_id, relationship_type enum. |
| Saved searches / smart folders | PostgreSQL JSON | Store query definition as JSON. Execute at read time. Named query with parameters. |
| Background text extraction | Celery workers | Queue Celery task on upload. Worker downloads from MinIO, extracts text, writes to DB. |
| Real-time folder updates | Redis pub/sub + WebSocket | Existing event bus pattern. Emit events on folder mutations. |
| Tree UI styling | shadcn/ui + Tailwind | Custom tree component using Collapsible, Button, ScrollArea from existing component library. |
| Folder tree API | FastAPI | Standard CRUD endpoints with recursive CTE helpers. |

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Full-text search | PostgreSQL tsvector | Elasticsearch 8.x | Adds JVM service, sync complexity. Overkill for internal ECM. |
| Full-text search | PostgreSQL tsvector | Typesense/Meilisearch | Separate service to deploy and sync. Not needed when PostgreSQL FTS suffices. |
| Hierarchy model | Adjacency list + CTE | ltree extension | Path desync bugs, label format restrictions, unnecessary extension dependency. |
| Hierarchy model | Adjacency list + CTE | Nested sets | Complex mutations, poor concurrent write performance. |
| Hierarchy model | Adjacency list + CTE | Closure table | O(n^2) storage for hierarchy relationships. |
| Schema validation | jsonschema | Custom Pydantic validator | jsonschema is the standard for validating JSON against JSON Schema. Pydantic validates fixed schemas, not user-defined dynamic schemas. |
| Text extraction (PDF) | PyPDF2 | PyMuPDF | C dependency, larger install footprint. PyPDF2 is pure Python and sufficient for text extraction. |
| Text extraction (PDF) | PyPDF2 | Apache Tika | Requires JVM, heavy Docker image. Overkill for text extraction. |
| Tree UI | Custom shadcn/ui | @headless-tree | Beta-stage library, unknown stability. Custom tree with existing components is straightforward for expected scale. |
| Tree UI | Custom shadcn/ui | react-arborist | Less actively maintained, heavier bundle, not shadcn-native. |
| Base model | Separate tables | SQLAlchemy polymorphic inheritance (dm_sysobject) | Requires migrating existing documents table, breaking 10+ FK references. Enormous migration risk. |

---

## Installation Summary

### Python (pip/uv)

```bash
# New production dependencies
pip install jsonschema PyPDF2 python-docx
```

### Frontend (npm)

```bash
# No new packages needed
# Tree component built with existing shadcn/ui primitives
```

### PostgreSQL

```sql
-- No new extensions needed
-- tsvector/tsquery is built into PostgreSQL core
```

---

## Sources

- [PostgreSQL Full-Text Search Documentation](https://www.postgresql.org/docs/current/textsearch-tables.html) -- HIGH confidence
- [PostgreSQL GIN Index for Text Search](https://www.postgresql.org/docs/current/textsearch-indexes.html) -- HIGH confidence
- [SQLAlchemy 2.0 PostgreSQL Dialect](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html) -- HIGH confidence
- [jsonschema PyPI](https://pypi.org/project/jsonschema/) -- HIGH confidence
- [PyPDF2 PyPI](https://pypi.org/project/PyPDF2/) -- HIGH confidence
- [python-docx PyPI](https://pypi.org/project/python-docx/) -- HIGH confidence
- [PostgreSQL ltree documentation](https://www.postgresql.org/docs/current/ltree.html) -- HIGH confidence (evaluated, not recommended)
