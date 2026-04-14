# Phase 30: Full-Text Search & Content Extraction - Research

**Researched:** 2026-04-14
**Domain:** PostgreSQL full-text search, document text extraction, Celery async tasks
**Confidence:** HIGH

## Summary

This phase adds full-text search across document content and metadata using PostgreSQL's built-in `tsvector`/`tsquery` capabilities, paired with automatic text extraction from uploaded files via Celery background workers. The architecture follows the established rendition task pattern already proven in the codebase.

The core technical approach is: (1) add a `fulltext_content` TEXT column to `DocumentVersion` to store extracted text, (2) add a `search_vector` tsvector column with GIN index to `Document` for fast search, (3) create a Celery extraction task that mirrors `rendition.py`, and (4) build a search API endpoint with `ts_rank` + `ts_headline` for ranked results with highlighted snippets. The frontend gets a dedicated `/search` page with filter sidebar.

**Primary recommendation:** Use PostgreSQL-native `tsvector`/`tsquery` with GIN indexing -- no external search service needed. Use `pdfplumber` for PDF extraction and `python-docx` for Word docs. Follow the existing `rendition.py` Celery task pattern exactly.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-01: Use PostgreSQL full-text search (tsvector/tsquery) -- no Elasticsearch
- D-02: Create a search_vector column (type tsvector) on the Document model with GIN index, populated from title + author + extracted content
- D-03: Search ranking uses ts_rank with normalization, results ordered by relevance score descending
- D-04: Use pdfplumber for PDF text extraction, python-docx for Word (.docx) extraction
- D-05: Plain text files (.txt, .md, .csv) read directly without a library
- D-06: Unsupported file types marked as "not indexed" -- document remains accessible but not searchable by content
- D-07: Follow existing rendition task pattern: Celery async task triggered after document upload
- D-08: Use existing extraction or default Celery queue, add task routing if needed
- D-09: Retry failed extractions up to 2 times (matching rendition pattern), log failures to audit trail
- D-10: Add extraction_status field to Document: pending | completed | failed | not_applicable
- D-11: Dedicated search page at /search with prominent search input and results below
- D-12: Filter sidebar with: folder selector, document type dropdown, lifecycle state selector (AND conditions)
- D-13: Results show: document title, author, snippet with highlighted matches, document type badge, lifecycle state badge, relevance score indicator
- D-14: Snippet generation uses ts_headline for keyword highlighting

### Claude's Discretion
- Search debounce timing (suggest 300ms matching existing pattern)
- Snippet length and number of snippets per result
- Whether to show a search icon in the main nav or rely on the search page
- Migration strategy for indexing existing documents (backfill task)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SRCH-01 | System automatically extracts and indexes text from PDF and Word documents via a background Celery worker; extraction failures are logged and do not block document save | Celery task pattern from rendition.py, pdfplumber + python-docx libraries, extraction_status field, audit trail logging |
| SRCH-02 | User can search documents by content (full-text body) and metadata fields with ranked results | PostgreSQL tsvector/tsquery with ts_rank for ranking, search_vector GIN index on Document model |
| SRCH-03 | User can scope a search to a specific folder, document type, or lifecycle state | AND-condition filters on search query, join with document_folders for folder scoping |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PostgreSQL FTS | 16+ (built-in) | Full-text search engine | tsvector/tsquery with GIN index -- already in the stack, handles expected volume with zero new infrastructure |
| pdfplumber | 0.11.9 | PDF text extraction | Lightweight, text-based PDF extraction. Built on pdfminer with friendlier API. extract_text() handles most text-based PDFs |
| python-docx | 1.2.0 | Word document text extraction | Standard library for .docx files. Already installed in project |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| SQLAlchemy 2.0 | 2.0.48 | ORM with tsvector support | Already in stack. Use `func.to_tsvector`, `func.to_tsquery`, `func.ts_rank`, `func.ts_headline` from `sqlalchemy.func` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pdfplumber | PyPDF2 | PyPDF2 is simpler but worse at complex layouts; pdfplumber handles multi-column, tables better |
| pdfplumber | pymupdf (fitz) | Faster but GPL licensed; pdfplumber is MIT |
| python-docx | docx2python | docx2python extracts text in document order more easily but python-docx is more established and already installed |

**Installation:**
```bash
pip install pdfplumber==0.11.9
# python-docx already installed (1.2.0)
```

**Version verification:** pdfplumber 0.11.9 confirmed as latest via PyPI. python-docx 1.2.0 confirmed installed and latest.

## Architecture Patterns

### Recommended Project Structure
```
src/app/
├── tasks/
│   ├── rendition.py        # (existing) PDF/thumbnail generation pattern
│   └── extraction.py       # NEW: text extraction task (mirrors rendition.py)
├── services/
│   ├── document_service.py # MODIFY: trigger extraction after upload/checkin
│   └── search_service.py   # NEW: search query builder with FTS
├── routers/
│   └── search.py           # NEW: /api/v1/search endpoint
├── schemas/
│   └── search.py           # NEW: SearchRequest, SearchResultResponse
├── models/
│   └── document.py         # MODIFY: add search_vector, fulltext_content, extraction_status
frontend/src/
├── pages/
│   └── SearchPage.tsx       # NEW: dedicated search page
├── api/
│   └── search.ts            # NEW: search API client
├── components/
│   └── search/
│       ├── SearchInput.tsx       # NEW: debounced search input
│       ├── SearchResults.tsx     # NEW: result list with snippets
│       └── SearchFilters.tsx     # NEW: filter sidebar
```

### Pattern 1: Celery Extraction Task (mirrors rendition.py)
**What:** Async task triggered after document upload/checkin that extracts text from the file in MinIO, stores it in `fulltext_content`, and updates `search_vector`.
**When to use:** Every document upload and checkin.
**Example:**
```python
# Source: existing rendition.py pattern
@celery_app.task(
    name="app.tasks.extraction.extract_document_text",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    soft_time_limit=300,
)
def extract_document_text(self, document_id: str, document_version_id: str):
    """Extract text content from a document version for full-text search."""
    asyncio.run(_extract_text_async(document_id, document_version_id))
```

### Pattern 2: PostgreSQL tsvector Column with GIN Index
**What:** A stored generated tsvector column on the Document model that combines title, author, and extracted content for fast full-text search.
**When to use:** On the Document model for search queries.
**Example:**
```python
# SQLAlchemy model column
from sqlalchemy import Index, Text
from sqlalchemy.dialects.postgresql import TSVECTOR

class Document(BaseModel):
    # ... existing fields ...
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)
    extraction_status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )

class DocumentVersion(BaseModel):
    # ... existing fields ...
    fulltext_content: Mapped[str | None] = mapped_column(Text, nullable=True)

# GIN index in migration
Index('ix_documents_search_vector', Document.search_vector, postgresql_using='gin')
```

### Pattern 3: Search Query with ts_rank and ts_headline
**What:** SQLAlchemy query using PostgreSQL FTS functions for ranked results with highlighted snippets.
**When to use:** In the search service for handling search requests.
**Example:**
```python
from sqlalchemy import func, select, cast, String

async def search_documents(
    db: AsyncSession,
    query_text: str,
    folder_id: uuid.UUID | None = None,
    document_type_id: uuid.UUID | None = None,
    lifecycle_state: str | None = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[dict], int]:
    ts_query = func.websearch_to_tsquery('english', query_text)

    rank = func.ts_rank(Document.search_vector, ts_query).label('rank')
    headline = func.ts_headline(
        'english',
        func.coalesce(
            # Use latest version fulltext for headline
            select(DocumentVersion.fulltext_content)
            .where(DocumentVersion.document_id == Document.id)
            .order_by(DocumentVersion.major_version.desc(), DocumentVersion.minor_version.desc())
            .limit(1)
            .correlate(Document)
            .scalar_subquery(),
            Document.title
        ),
        ts_query,
        'StartSel=<mark>, StopSel=</mark>, MaxWords=35, MinWords=15, MaxFragments=3'
    ).label('headline')

    base_query = (
        select(Document, rank, headline)
        .where(
            Document.search_vector.op('@@')(ts_query),
            Document.is_deleted == False,
        )
    )

    # Apply filters
    if folder_id:
        base_query = base_query.where(
            Document.id.in_(
                select(document_folders.c.document_id)
                .where(document_folders.c.folder_id == folder_id)
            )
        )
    if document_type_id:
        base_query = base_query.where(Document.document_type_id == document_type_id)
    if lifecycle_state:
        base_query = base_query.where(Document.lifecycle_state == lifecycle_state)

    # Count
    count_query = select(func.count()).select_from(base_query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Fetch ranked results
    results = await db.execute(
        base_query.order_by(rank.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(results.all()), total
```

### Pattern 4: Updating search_vector After Extraction
**What:** After extracting text, update the Document's search_vector by combining title, author, and extracted content with weighted ranks.
**When to use:** In the extraction task, after storing fulltext_content.
**Example:**
```python
# In the extraction task, after saving fulltext_content:
await session.execute(
    update(Document)
    .where(Document.id == doc_id)
    .values(
        search_vector=func.to_tsvector('english',
            func.coalesce(Document.title, '') + ' ' +
            func.coalesce(Document.author, '') + ' ' +
            func.coalesce(content_text, '')
        ),
        extraction_status='completed'
    )
)
```

**Note on weighted vectors:** PostgreSQL supports weight labels A/B/C/D for tsvector. A more refined approach uses `setweight()`:
```python
search_vector = (
    func.setweight(func.to_tsvector('english', func.coalesce(Document.title, '')), 'A') +
    func.setweight(func.to_tsvector('english', func.coalesce(Document.author, '')), 'B') +
    func.setweight(func.to_tsvector('english', func.coalesce(content_text, '')), 'C')
)
```
This ensures title matches rank higher than content matches.

### Anti-Patterns to Avoid
- **Storing extracted text only in tsvector:** The tsvector is a lossy representation (stems, no positions). Always store the original text in `fulltext_content` for `ts_headline` snippet generation.
- **Using LIKE/ILIKE for search:** Orders of magnitude slower than tsvector/GIN for text search.
- **Triggering extraction synchronously:** Never extract text in the upload request -- always use Celery. Large PDFs can take 10+ seconds.
- **Using a PostgreSQL trigger to auto-update search_vector:** In async SQLAlchemy, triggers can cause unexpected behavior. Update search_vector explicitly in application code.
- **Extracting from scanned/image PDFs without OCR:** pdfplumber only handles text-based PDFs. Scanned PDFs will return empty strings -- handle gracefully by marking extraction as completed with empty content rather than failed.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PDF text extraction | Custom PDF parser | pdfplumber 0.11.9 | PDF format is complex; pdfplumber handles encoding, multi-column, ligatures |
| Word text extraction | Custom XML parser for .docx | python-docx 1.2.0 | .docx is a ZIP of XML files; python-docx handles the OPC packaging |
| Full-text search ranking | Custom TF-IDF scoring | PostgreSQL ts_rank | Battle-tested, handles stemming, stopwords, normalization |
| Search snippet generation | Custom substring extraction | PostgreSQL ts_headline | Handles word boundaries, fragment selection, HTML highlighting |
| Search query parsing | Custom query parser | websearch_to_tsquery | Handles quoted phrases, OR, NOT, partial words |

**Key insight:** PostgreSQL's full-text search is a complete search engine -- ranking, snippets, stemming, stopwords, and query parsing are all built in. The only code needed is the glue between SQLAlchemy and these PostgreSQL functions.

## Common Pitfalls

### Pitfall 1: Empty tsvector for Documents Without Extracted Content
**What goes wrong:** Documents uploaded before extraction completes (or that fail extraction) have NULL search_vector, making them invisible to search.
**Why it happens:** Search query uses `@@` operator which returns false for NULL vectors.
**How to avoid:** Initialize search_vector from title+author at upload time (before extraction). Extraction task updates it by adding content. This ensures documents are always findable by metadata.
**Warning signs:** New uploads briefly not appearing in search results.

### Pitfall 2: pdfplumber Memory Usage on Large PDFs
**What goes wrong:** Very large PDFs (100+ pages) can consume significant memory during extraction.
**Why it happens:** pdfplumber loads page objects into memory for text extraction.
**How to avoid:** Set `soft_time_limit=300` on the Celery task (already in rendition pattern). Consider truncating extracted text to a reasonable limit (e.g., first 1MB of text) for very large documents.
**Warning signs:** Celery worker OOM kills on large document uploads.

### Pitfall 3: ts_headline Performance on Large Content
**What goes wrong:** `ts_headline` needs the original text to generate snippets, and it can be slow on very large text fields.
**Why it happens:** ts_headline scans the full text to find matching fragments.
**How to avoid:** Use `MaxFragments=3, MaxWords=35` options to limit snippet generation work. Store `fulltext_content` on DocumentVersion (not inlined in the search query from MinIO).
**Warning signs:** Search response times increasing with document content size.

### Pitfall 4: SQLAlchemy TSVECTOR Type Import
**What goes wrong:** Using wrong import path for TSVECTOR type.
**Why it happens:** TSVECTOR is PostgreSQL-specific, not in the base SQLAlchemy types.
**How to avoid:** Import from `sqlalchemy.dialects.postgresql import TSVECTOR`. For the Alembic migration, use `sa.Column('search_vector', postgresql.TSVECTOR())`.
**Warning signs:** Import errors or type mismatch on migration.

### Pitfall 5: GIN Index Not Created in Migration
**What goes wrong:** Search works but is extremely slow without the GIN index.
**Why it happens:** Alembic auto-generation may not detect GIN indexes properly.
**How to avoid:** Manually add the GIN index in the migration: `op.create_index('ix_documents_search_vector', 'documents', ['search_vector'], postgresql_using='gin')`.
**Warning signs:** Full table scans on search queries visible in `EXPLAIN ANALYZE`.

### Pitfall 6: websearch_to_tsquery vs plainto_tsquery
**What goes wrong:** Using `plainto_tsquery` which doesn't support quoted phrases or boolean operators.
**Why it happens:** `plainto_tsquery` is the default in SQLAlchemy's `match()` operator.
**How to avoid:** Use `func.websearch_to_tsquery('english', query)` explicitly. It supports Google-like syntax: quoted phrases, `-exclusion`, `OR`.
**Warning signs:** Users expecting phrase search getting unexpected results.

## Code Examples

### Text Extraction from PDF (pdfplumber)
```python
# Source: pdfplumber GitHub README + official docs
import pdfplumber

def extract_pdf_text(content: bytes) -> str:
    """Extract text from PDF bytes using pdfplumber."""
    import io
    text_parts = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)
```

### Text Extraction from Word (.docx)
```python
# Source: python-docx documentation
from docx import Document as DocxDocument

def extract_docx_text(content: bytes) -> str:
    """Extract text from .docx bytes using python-docx."""
    import io
    doc = DocxDocument(io.BytesIO(content))
    text_parts = []
    for paragraph in doc.paragraphs:
        if paragraph.text.strip():
            text_parts.append(paragraph.text)
    # Also extract text from tables
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text.strip():
                    text_parts.append(cell.text)
    return "\n".join(text_parts)
```

### Plain Text Extraction
```python
def extract_plain_text(content: bytes) -> str:
    """Extract text from plain text files."""
    for encoding in ['utf-8', 'latin-1', 'cp1252']:
        try:
            return content.decode(encoding)
        except (UnicodeDecodeError, ValueError):
            continue
    return content.decode('utf-8', errors='replace')
```

### Search API Endpoint Pattern
```python
# Following existing router patterns (query.py, documents.py)
@router.get("/", response_model=EnvelopeResponse[list[SearchResultResponse]])
async def search_documents(
    q: str = Query(..., min_length=1, max_length=500),
    folder_id: uuid.UUID | None = Query(None),
    document_type_id: uuid.UUID | None = Query(None),
    lifecycle_state: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    results, total = await search_service.search_documents(
        db, q, folder_id, document_type_id, lifecycle_state,
        skip=(page - 1) * page_size, limit=page_size,
        user_id=str(current_user.id),
        is_superuser=current_user.is_superuser,
    )
    # ... build response with PaginationMeta
```

### Backfill Task for Existing Documents
```python
@celery_app.task(name="app.tasks.extraction.backfill_search_index")
def backfill_search_index():
    """One-time task to extract text and build search vectors for all existing documents."""
    asyncio.run(_backfill_async())

async def _backfill_async():
    session_factory = create_task_session_factory()
    async with session_factory() as session:
        # Find documents without search_vector
        result = await session.execute(
            select(Document.id)
            .where(Document.search_vector == None)  # noqa: E711
            .where(Document.is_deleted == False)     # noqa: E712
        )
        doc_ids = [str(row[0]) for row in result.fetchall()]

    # Dispatch individual extraction tasks
    for doc_id in doc_ids:
        # Get latest version for each doc
        extract_document_text.delay(doc_id, latest_version_id)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| plainto_tsquery | websearch_to_tsquery | PostgreSQL 11+ (2018) | Supports Google-like syntax (quotes, OR, -exclude) |
| Separate search service (Elasticsearch) | PostgreSQL built-in FTS | Always available, but better tooling since PG 12+ | Zero infrastructure overhead for moderate-scale search |
| PyPDF2 for extraction | pdfplumber | ~2020 | Better handling of complex layouts, tables, multi-column |

**Deprecated/outdated:**
- PyPDF2: Renamed to pypdf. pdfplumber is recommended over it for text extraction.
- `to_tsquery`: Requires manual formatting with `&` and `|`. Use `websearch_to_tsquery` for user-facing search.

## Open Questions

1. **ACL enforcement on search results**
   - What we know: `list_documents` has complex ACL filtering with direct ACL, folder ACL, and workflow participant checks.
   - What's unclear: Should search results enforce the same ACL logic? This would significantly complicate the search query.
   - Recommendation: Apply the same ACL subquery conditions to search results. The existing `list_documents` ACL logic can be extracted into a reusable subquery builder. Performance impact is mitigated by the GIN index reducing the candidate set before ACL filtering.

2. **Content size limit for fulltext_content**
   - What we know: Some documents could have hundreds of pages of text.
   - What's unclear: Should there be a truncation limit?
   - Recommendation: Truncate at 1MB of extracted text. This covers ~250K words which is sufficient for search purposes. Log a warning when truncation occurs.

3. **Search vector initialization on upload**
   - What we know: There is a timing gap between upload and extraction completion.
   - What's unclear: Whether to initialize search_vector at upload with just title+author.
   - Recommendation: Yes -- set search_vector from title+author in the upload/checkin service (synchronously). The extraction task then updates it with the full content. This ensures documents are immediately searchable by metadata.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PostgreSQL FTS | Search engine | Yes (via Docker) | 16+ | -- |
| pdfplumber | PDF extraction | No (not installed) | -- | pip install pdfplumber==0.11.9 |
| python-docx | DOCX extraction | Yes | 1.2.0 | -- |
| Celery | Background tasks | Yes | 5.6.x | -- |
| Redis | Celery broker | Yes (via Docker) | 7.x | -- |

**Missing dependencies with no fallback:**
- None (pdfplumber is a simple pip install)

**Missing dependencies with fallback:**
- pdfplumber needs to be installed: `pip install pdfplumber==0.11.9` and added to pyproject.toml

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.24.x |
| Config file | pyproject.toml [tool.pytest.ini_options] |
| Quick run command | `pytest tests/test_search.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SRCH-01 | Text extraction from PDF/DOCX via Celery task, failures logged | unit + integration | `pytest tests/test_search.py::test_extract_pdf_text -x` | No -- Wave 0 |
| SRCH-01 | Extraction status tracking (pending/completed/failed/not_applicable) | unit | `pytest tests/test_search.py::test_extraction_status -x` | No -- Wave 0 |
| SRCH-02 | Full-text search with ranked results | integration | `pytest tests/test_search.py::test_search_ranked_results -x` | No -- Wave 0 |
| SRCH-02 | ts_headline snippet generation | integration | `pytest tests/test_search.py::test_search_snippets -x` | No -- Wave 0 |
| SRCH-03 | Search scoped by folder | integration | `pytest tests/test_search.py::test_search_folder_filter -x` | No -- Wave 0 |
| SRCH-03 | Search scoped by document type | integration | `pytest tests/test_search.py::test_search_type_filter -x` | No -- Wave 0 |
| SRCH-03 | Search scoped by lifecycle state | integration | `pytest tests/test_search.py::test_search_lifecycle_filter -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_search.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_search.py` -- covers SRCH-01, SRCH-02, SRCH-03
- [ ] Test fixtures for documents with pre-populated search_vector and fulltext_content

**Note:** Tests use aiosqlite which does NOT support tsvector/tsquery. Search service tests that use FTS functions will need PostgreSQL-specific handling -- either skip FTS-specific tests on SQLite with `pytest.mark.skipif` or mock the FTS functions. The extraction logic (pdfplumber, python-docx) can be unit tested independently of the database.

## Project Constraints (from CLAUDE.md)

- **Tech stack:** FastAPI + SQLAlchemy 2.0 async + PostgreSQL + Celery + Redis + React + TypeScript + Vite
- **Frontend:** shadcn/ui components + Tailwind CSS + TanStack Query + React Router 7.x
- **Response format:** All API endpoints use `EnvelopeResponse` with `PaginationMeta`
- **ACL enforcement:** Document access requires permission checks
- **Background tasks:** Celery with Redis broker, use `create_task_session_factory()` for DB access in tasks
- **Async pattern:** Celery tasks use `asyncio.run()` wrapping async implementation functions
- **Linting:** Ruff for Python, TypeScript strict mode
- **GSD Workflow:** Must use GSD commands for code changes

## Sources

### Primary (HIGH confidence)
- [PostgreSQL 18 Full-Text Search Documentation](https://www.postgresql.org/docs/current/textsearch-controls.html) -- ts_rank, ts_headline, websearch_to_tsquery
- [SQLAlchemy 2.0 PostgreSQL Dialect](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html) -- TSVECTOR type, FTS operators
- [pdfplumber GitHub](https://github.com/jsvine/pdfplumber) -- API reference, extract_text()
- [python-docx documentation](https://python-docx.readthedocs.io/) -- Document, paragraphs, tables
- Existing codebase: `src/app/tasks/rendition.py`, `src/app/services/document_service.py`, `src/app/models/document.py`

### Secondary (MEDIUM confidence)
- [PostgreSQL FTS with SQLAlchemy blog](https://amitosh.medium.com/full-text-search-fts-with-postgresql-and-sqlalchemy-edc436330a0c) -- verified patterns against official docs
- [pdfplumber extraction accuracy comparison](https://onlyoneaman.medium.com/i-tested-7-python-pdf-extractors-so-you-dont-have-to-2025-edition-c88013922257) -- 2025 evaluation

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries verified via PyPI, PostgreSQL FTS is well-documented
- Architecture: HIGH -- follows proven rendition.py pattern from existing codebase
- Pitfalls: HIGH -- well-known PostgreSQL FTS gotchas documented in official docs

**Research date:** 2026-04-14
**Valid until:** 2026-05-14 (stable technologies, 30-day validity)
