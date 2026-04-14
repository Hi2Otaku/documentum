---
phase: 30-full-text-search-content-extraction
plan: 01
subsystem: search
tags: [postgresql, tsvector, fts, pdfplumber, python-docx, celery]

requires:
  - phase: 28-cabinet-folder-hierarchy
    provides: folder model and document_folders association table for folder-scoped search
provides:
  - Document.search_vector TSVECTOR column with GIN index
  - Document.extraction_status tracking field
  - DocumentVersion.fulltext_content text storage
  - Celery extract_document_text task (PDF, DOCX, plain text)
  - search_documents service with ts_rank and ts_headline
  - SearchResultResponse Pydantic schema
  - backfill_search_index task for existing documents
affects: [30-02, 30-03]

tech-stack:
  added: [pdfplumber 0.11.9, python-docx >=1.1]
  patterns: [weighted tsvector A/B/C for title/author/content, websearch_to_tsquery for user queries]

key-files:
  created:
    - src/app/tasks/extraction.py
    - src/app/services/search_service.py
    - src/app/schemas/search.py
    - alembic/versions/phase30_001_search_columns.py
  modified:
    - src/app/models/document.py
    - src/app/celery_app.py
    - pyproject.toml

key-decisions:
  - "Raw DDL migration (per Phase 29 pattern) to avoid SQLAlchemy enum conflicts"
  - "Weighted tsvector: title=A, author=B, content=C for relevance ranking"
  - "websearch_to_tsquery for natural user query syntax (AND/OR/NOT support)"
  - "Correlated subquery for ts_headline on latest version fulltext_content"

patterns-established:
  - "Extraction task pattern: download from MinIO, extract text, update search_vector in single transaction"
  - "Search service returns dicts (not ORM objects) for flexibility in response serialization"

requirements-completed: [SRCH-01, SRCH-02]

duration: 4min
completed: 2026-04-14
---

# Phase 30 Plan 01: Search Backend Foundation Summary

**PostgreSQL tsvector search with weighted A/B/C ranking, Celery text extraction for PDF/DOCX/text, and ts_headline snippet generation**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-14T03:11:36Z
- **Completed:** 2026-04-14T03:15:08Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Document and DocumentVersion models extended with search_vector (TSVECTOR + GIN index), extraction_status, and fulltext_content columns
- Celery extraction task processes PDF (pdfplumber), DOCX (python-docx), and plain text with encoding detection
- Search service provides ranked results with ts_headline snippets and full ACL enforcement matching document_service.py pattern

## Task Commits

Each task was committed atomically:

1. **Task 1: Model columns, migration, schemas, and pdfplumber dependency** - `581a2f1` (feat)
2. **Task 2: Celery extraction task and search service** - `789d402` (feat)

## Files Created/Modified
- `src/app/models/document.py` - Added search_vector, extraction_status, fulltext_content columns
- `src/app/tasks/extraction.py` - Celery task for PDF/DOCX/text extraction with weighted tsvector updates
- `src/app/services/search_service.py` - Full-text search with ts_rank ranking, ts_headline, ACL filtering
- `src/app/schemas/search.py` - SearchResultResponse Pydantic schema
- `alembic/versions/phase30_001_search_columns.py` - Migration adding columns and GIN index
- `src/app/celery_app.py` - Registered extraction tasks with queue routing
- `pyproject.toml` - Added pdfplumber and python-docx dependencies

## Decisions Made
- Used raw DDL in migration (consistent with Phase 29 pattern) to avoid enum conflicts with Alembic autogenerate
- Weighted tsvector with title=A, author=B, content=C ensures title matches rank highest
- Used websearch_to_tsquery for natural user query syntax (supports AND/OR/NOT without special syntax)
- Correlated subquery fetches latest version's fulltext_content for ts_headline, falling back to title

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] python-docx dependency added to pyproject.toml instead of requirements.txt**
- **Found during:** Task 1
- **Issue:** Plan referenced requirements.txt which does not exist; project uses pyproject.toml
- **Fix:** Added pdfplumber and python-docx to pyproject.toml dependencies array
- **Files modified:** pyproject.toml
- **Verification:** Dependencies listed correctly in pyproject.toml
- **Committed in:** 581a2f1 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary adaptation to actual project structure. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Search backend foundation complete: models, migration, extraction task, search service
- Ready for Plan 02 (search API endpoints) and Plan 03 (frontend search UI)
- Backfill task available for indexing existing documents after migration

---
*Phase: 30-full-text-search-content-extraction*
*Completed: 2026-04-14*
