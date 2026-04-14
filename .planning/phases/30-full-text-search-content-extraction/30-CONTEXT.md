# Phase 30: Full-Text Search & Content Extraction - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous mode — recommended defaults selected)

<domain>
## Phase Boundary

This phase delivers full-text search across document content and metadata, powered by automatic text extraction from uploaded files. Users can search by keyword, see ranked results with highlighted snippets, and narrow results by folder, document type, or lifecycle state. Extraction runs asynchronously via Celery workers — failures are logged and surfaced but do not block document operations.

</domain>

<decisions>
## Implementation Decisions

### Search Backend
- **D-01:** Use PostgreSQL full-text search (`tsvector`/`tsquery`) — no Elasticsearch. PostgreSQL is already in the stack, supports ranking (`ts_rank`), phrase search, and stemming. Avoids adding a new service to docker-compose.
- **D-02:** Create a `search_vector` column (type `tsvector`) on the Document model, populated from title + author + extracted content. Use a GIN index for fast lookup.
- **D-03:** Search ranking uses `ts_rank` with normalization. Results ordered by relevance score descending.

### Text Extraction
- **D-04:** Use `pdfplumber` for PDF text extraction (lightweight, text-based PDFs). Use `python-docx` for Word (.docx) extraction.
- **D-05:** Plain text files (.txt, .md, .csv) are read directly without a library.
- **D-06:** Unsupported file types are marked as "not indexed" — the document remains accessible but not searchable by content.

### Extraction Pipeline
- **D-07:** Follow the existing rendition task pattern: Celery async task triggered after document upload. Task fetches file from MinIO, extracts text, stores extracted content in a `fulltext_content` TEXT column on DocumentVersion, then updates the `search_vector` on Document.
- **D-08:** Use the existing `extraction` or `default` Celery queue. Add task routing if needed.
- **D-09:** Retry failed extractions up to 2 times (matching rendition pattern). Log failures to audit trail with extraction error details.
- **D-10:** Add `extraction_status` field to Document: `pending` | `completed` | `failed` | `not_applicable`. Surface this in the document detail panel.

### Search UX
- **D-11:** Dedicated search page at `/search` with a prominent search input and results below.
- **D-12:** Filter sidebar with: folder selector, document type dropdown, lifecycle state selector. Filters apply as AND conditions.
- **D-13:** Results show: document title, author, snippet with highlighted matches, document type badge, lifecycle state badge, relevance score indicator.
- **D-14:** Snippet generation uses `ts_headline` for keyword highlighting in search results.

### Claude's Discretion
- Search debounce timing (suggest 300ms matching existing pattern)
- Snippet length and number of snippets per result
- Whether to show a search icon in the main nav or rely on the search page
- Migration strategy for indexing existing documents (backfill task)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Patterns
- `src/app/tasks/rendition.py` — Async file processing pattern (MinIO fetch → process → update DB)
- `src/app/services/query_service.py` — Multi-criteria query with pagination and ACL filtering
- `src/app/routers/query.py` — Query endpoint pattern with filter parameters
- `src/app/celery_app.py` — Celery configuration, task routing, beat schedule

### Models
- `src/app/models/document.py` — Document and DocumentVersion models
- `src/app/services/document_service.py` — Document CRUD with ACL enforcement and MinIO integration

### Frontend
- `frontend/src/pages/DocumentsPage.tsx` — Existing document list with debounced filters
- `frontend/src/components/documents/DocumentTable.tsx` — Table component for document listing

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `rendition.py` task: proven pattern for async MinIO file processing with error handling and retries
- `query_service.py`: pagination + conditional filtering pattern, can be extended for search
- `DocumentTable` component: existing table with row selection, can be extended with snippet column
- `DocumentsPage` filter pattern: debounced inputs with react-query, page reset on filter change

### Established Patterns
- Celery tasks use `soft_time_limit=300`, `max_retries=2`, `countdown=30` for retry
- All list endpoints return `EnvelopeResponse` with `PaginationMeta`
- Frontend uses `@tanstack/react-query` with query key factories
- ACL enforcement via `check_permission` for document access

### Integration Points
- Document upload flow in `document_service.py` — trigger extraction task after successful upload
- Router layer in `src/app/routers/documents.py` — add search endpoint
- Frontend routing in `App.tsx` — add `/search` route
- Main navigation — add search entry point

</code_context>

<specifics>
## Specific Ideas

No specific requirements — autonomous mode used recommended defaults based on codebase analysis.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 30-full-text-search-content-extraction*
*Context gathered: 2026-04-14*
