# Phase 20: Document Renditions - Research

**Researched:** 2026-04-06
**Domain:** Document conversion (PDF rendition, thumbnail generation), Celery task architecture
**Confidence:** HIGH

## Summary

Phase 20 adds automatic PDF rendition and thumbnail generation when documents are uploaded. The existing codebase already has: (1) a `document.uploaded` event emitted via the event bus, (2) Celery task infrastructure with the `asyncio.run()` pattern for async DB access, (3) MinIO for file storage with upload/download helpers, and (4) a frontend document detail panel with version history where rendition status and download links will be displayed.

The architecture requires a new `Rendition` SQLAlchemy model linked to `DocumentVersion`, two new Celery tasks (`generate_pdf_rendition` and `generate_thumbnail`), an event handler on `document.uploaded` that dispatches these tasks, new API endpoints for rendition status/download/retry, and frontend updates to show rendition status badges and PDF download buttons.

**Primary recommendation:** Use LibreOffice headless (subprocess) for office-to-PDF conversion, `pypdfium2` for PDF-to-image rendering (no system dependencies), and Pillow for image thumbnail generation. The event handler triggers Celery tasks; tasks store results back in MinIO under a `renditions/` prefix within the documents bucket.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REND-01 | System auto-generates PDF rendition when a document is uploaded (via LibreOffice headless worker) | Event bus handler on `document.uploaded` dispatches `generate_pdf_rendition` Celery task. LibreOffice subprocess converts office formats; PDFs pass through as-is. |
| REND-02 | System auto-generates thumbnail image for uploaded documents | Same event handler dispatches `generate_thumbnail` Celery task. Uses pypdfium2 for PDF pages, Pillow for images. |
| REND-03 | User can download the PDF rendition of any document version | New API endpoint `GET /documents/{id}/versions/{vid}/renditions/{type}/download` serves rendition from MinIO. Frontend adds download button in version history. |
| REND-04 | Rendition status is visible in the document detail view (pending, ready, failed) | Rendition model tracks status enum. API returns rendition status with version data. Frontend shows status badge + retry button on failure. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pillow | 12.1.1 | Image thumbnail generation | Already installed in project. Handles image resize, format conversion. |
| pypdfium2 | 5.6.0 | PDF page rendering to image | Pure Python + bundled native lib. No system poppler dependency. Renders PDF pages to PIL Images for thumbnailing. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| LibreOffice headless | system | Office-to-PDF conversion | Called as subprocess. Available in Docker; gracefully fails on dev machines without it. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pypdfium2 | pdf2image (poppler) | Requires system poppler install; pypdfium2 bundles its own native lib |
| pypdfium2 | PyMuPDF (fitz) | AGPL licensed; pypdfium2 is Apache/BSD |
| LibreOffice headless | Gotenberg (Docker service) | Extra service to manage; LibreOffice subprocess is simpler |

**Installation:**
```bash
pip install pypdfium2
```

Note: Pillow is already installed (12.1.1). LibreOffice is a system dependency, not a pip package.

## Architecture Patterns

### Recommended Project Structure
```
src/app/
  models/
    rendition.py          # Rendition model
  schemas/
    rendition.py          # Pydantic schemas
  services/
    rendition_service.py  # Business logic
  tasks/
    rendition.py          # Celery tasks (generate_pdf, generate_thumbnail)
  routers/
    documents.py          # Extended with rendition endpoints
frontend/src/
  api/
    documents.ts          # Extended with rendition API calls
  components/documents/
    RenditionStatusBadge.tsx  # Status indicator
    VersionHistoryList.tsx    # Extended with rendition actions
```

### Pattern 1: Rendition Model
**What:** A `Rendition` table linked to `DocumentVersion` with type, status, and MinIO key.
**When to use:** Every document version can have multiple renditions (pdf, thumbnail).
**Example:**
```python
class RenditionType(str, enum.Enum):
    PDF = "pdf"
    THUMBNAIL = "thumbnail"

class RenditionStatus(str, enum.Enum):
    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"

class Rendition(BaseModel):
    __tablename__ = "renditions"
    __table_args__ = (
        UniqueConstraint("document_version_id", "rendition_type", name="uq_rendition_version_type"),
    )

    document_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("document_versions.id"), nullable=False
    )
    rendition_type: Mapped[str] = mapped_column(
        Enum(RenditionType, name="renditiontype"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        Enum(RenditionStatus, name="renditionstatus"), default=RenditionStatus.PENDING, nullable=False
    )
    minio_object_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
```

### Pattern 2: Event-Driven Rendition Triggering
**What:** Register an event handler on `document.uploaded` that creates Rendition records (PENDING) and dispatches Celery tasks.
**When to use:** Follows the existing event_handlers.py pattern exactly.
**Example:**
```python
@event_bus.on("document.uploaded")
async def _trigger_renditions_on_upload(db: AsyncSession, event: DomainEvent) -> None:
    payload = event.payload or {}
    # Find the version that was just created
    version = await _get_latest_version(db, event.entity_id)
    if version is None:
        return

    # Create PENDING rendition records
    pdf_rendition = Rendition(
        document_version_id=version.id,
        rendition_type=RenditionType.PDF,
        status=RenditionStatus.PENDING,
    )
    thumb_rendition = Rendition(
        document_version_id=version.id,
        rendition_type=RenditionType.THUMBNAIL,
        status=RenditionStatus.PENDING,
    )
    db.add_all([pdf_rendition, thumb_rendition])
    await db.flush()

    # Dispatch Celery tasks
    from app.tasks.rendition import generate_pdf_rendition, generate_thumbnail
    generate_pdf_rendition.delay(str(version.id), str(pdf_rendition.id))
    generate_thumbnail.delay(str(version.id), str(thumb_rendition.id))
```

### Pattern 3: Celery Task with asyncio.run() Bridge
**What:** Celery tasks use `asyncio.run()` with `create_task_session_factory()` to access async DB and MinIO, matching the existing notification task pattern.
**When to use:** All Celery tasks in this project follow this pattern.
**Example:**
```python
@celery_app.task(name="app.tasks.rendition.generate_pdf_rendition", bind=True, max_retries=2)
def generate_pdf_rendition(self, version_id: str, rendition_id: str):
    asyncio.run(_generate_pdf_async(self, version_id, rendition_id))

async def _generate_pdf_async(task, version_id: str, rendition_id: str):
    session_factory = create_task_session_factory()
    async with session_factory() as session:
        # 1. Load version + rendition
        # 2. Download source from MinIO
        # 3. Convert to PDF (LibreOffice subprocess or passthrough if already PDF)
        # 4. Upload PDF to MinIO
        # 5. Update rendition record: status=READY, minio_object_key, content_size
        # On error: update rendition status=FAILED, error_message
```

### Pattern 4: LibreOffice Subprocess Conversion
**What:** Shell out to `soffice --headless --convert-to pdf` in a temp directory.
**When to use:** For office formats (docx, xlsx, pptx, odt, etc.) that need PDF conversion.
**Example:**
```python
import subprocess
import tempfile
from pathlib import Path

CONVERTIBLE_TYPES = {
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.oasis.opendocument.text",
    "application/vnd.oasis.opendocument.spreadsheet",
    "text/plain",
    "text/csv",
    "text/html",
}

def convert_to_pdf(source_bytes: bytes, filename: str) -> bytes:
    """Convert a document to PDF using LibreOffice headless. Raises if unavailable."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src_path = Path(tmpdir) / filename
        src_path.write_bytes(source_bytes)

        result = subprocess.run(
            ["soffice", "--headless", "--convert-to", "pdf", "--outdir", tmpdir, str(src_path)],
            capture_output=True, timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(f"LibreOffice conversion failed: {result.stderr.decode()}")

        pdf_path = src_path.with_suffix(".pdf")
        if not pdf_path.exists():
            raise RuntimeError("LibreOffice did not produce a PDF output file")
        return pdf_path.read_bytes()
```

### Pattern 5: Thumbnail Generation
**What:** Generate a small JPEG/PNG thumbnail from the first page of a PDF or from an image file.
**When to use:** For REND-02 (thumbnail visible in document list).
**Example:**
```python
import pypdfium2 as pdfium
from PIL import Image
import io

IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/tiff", "image/bmp"}
THUMB_SIZE = (200, 200)

def generate_thumbnail_from_pdf(pdf_bytes: bytes) -> bytes:
    """Render first page of PDF to a thumbnail image."""
    pdf = pdfium.PdfDocument(pdf_bytes)
    page = pdf[0]
    bitmap = page.render(scale=1)  # 72 DPI
    pil_image = bitmap.to_pil()
    pil_image.thumbnail(THUMB_SIZE, Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    pil_image.save(buf, format="PNG")
    return buf.getvalue()

def generate_thumbnail_from_image(image_bytes: bytes) -> bytes:
    """Resize an image to a thumbnail."""
    img = Image.open(io.BytesIO(image_bytes))
    img.thumbnail(THUMB_SIZE, Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
```

### Pattern 6: MinIO Key Naming Convention
**What:** Store renditions in MinIO with a predictable key pattern.
**When to use:** All rendition uploads.
```
Key format: {document_id}/{version_id}/renditions/{type}.{ext}
Example:    abc123/def456/renditions/pdf.pdf
Example:    abc123/def456/renditions/thumbnail.png
```
This keeps renditions co-located with their source version objects.

### Anti-Patterns to Avoid
- **Storing renditions as BLOBs in PostgreSQL:** Use MinIO consistently. The project already stores all file content in MinIO.
- **Synchronous conversion in the API request:** Never block the upload request with LibreOffice conversion. Always use Celery.
- **Polling for rendition status:** The frontend should use react-query refetch interval on PENDING status, not manual polling loops.
- **Generating renditions for renditions:** Only generate from source document versions, never from other renditions.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PDF rendering to image | Custom PDF parser | pypdfium2 | PDF rendering is enormously complex; pypdfium2 wraps Chromium's PDFium |
| Office-to-PDF conversion | Custom format parsers | LibreOffice headless | Office formats have thousands of edge cases |
| Image resizing | Manual pixel manipulation | Pillow (PIL) | Battle-tested, handles color spaces, EXIF rotation, format conversion |
| Temp file cleanup | Manual try/finally | tempfile.TemporaryDirectory() | Context manager guarantees cleanup even on exceptions |

## Common Pitfalls

### Pitfall 1: LibreOffice Global Lock
**What goes wrong:** LibreOffice headless cannot run multiple instances concurrently in the same user profile directory. Two simultaneous conversions will fail.
**Why it happens:** LibreOffice uses a lock file in `~/.config/libreoffice/`.
**How to avoid:** Use `-env:UserInstallation=file:///tmp/libreoffice_profile_{uuid}` to give each invocation its own profile directory. In Docker, use Celery concurrency=1 for the rendition worker, or use unique profile dirs.
**Warning signs:** "LibreOffice is already running" errors in Celery logs.

### Pitfall 2: LibreOffice Not Available in Development
**What goes wrong:** Tasks fail on Windows/Mac dev machines where LibreOffice is not installed.
**Why it happens:** LibreOffice is a system dependency, not a pip package.
**How to avoid:** Wrap subprocess call in try/except (FileNotFoundError for missing binary). Set rendition status to FAILED with clear error message "LibreOffice not available". The architecture is ready for Docker where LibreOffice IS installed.
**Warning signs:** FileNotFoundError or "soffice not found" in task logs.

### Pitfall 3: Celery Task Session Factory
**What goes wrong:** Reusing the module-level SQLAlchemy engine in Celery tasks causes "event loop is closed" errors.
**Why it happens:** Each `asyncio.run()` creates a new event loop; the module-level engine's connection pool is bound to the original loop.
**How to avoid:** Always use `create_task_session_factory()` inside the async function (matching the existing notification task pattern).
**Warning signs:** RuntimeError about closed event loops.

### Pitfall 4: Large File Memory Pressure
**What goes wrong:** Reading entire large documents into memory for conversion causes OOM in Celery workers.
**Why it happens:** The source file must be fully loaded for conversion.
**How to avoid:** Set a maximum file size for rendition generation (e.g., 50MB). Skip rendition for files above the limit with a clear status message.
**Warning signs:** Worker processes being killed by OOM killer.

### Pitfall 5: Forgetting to Trigger on Checkin
**What goes wrong:** Only new uploads get renditions; checkins (new versions) do not.
**Why it happens:** The event handler only listens for `document.uploaded`, but checkins create new versions too.
**How to avoid:** Either emit `document.uploaded` on checkin as well, or add a separate handler. Looking at the code, `checkin_document` does NOT emit a domain event, so the rendition service should also be triggered from the checkin flow directly (or add event emission to checkin).
**Warning signs:** Versions after v0.1 have no renditions.

### Pitfall 6: pypdfium2 on Windows
**What goes wrong:** pypdfium2 ships pre-built binaries for all major platforms (Windows, Linux, macOS), but some older versions had Windows compatibility issues.
**Why it happens:** Native library packaging variations.
**How to avoid:** Use v5.x which has stable Windows support. Test locally.
**Warning signs:** ImportError or DLL load failures.

## Code Examples

### Rendition API Endpoints
```python
# GET /documents/{doc_id}/versions/{ver_id}/renditions
# Returns list of renditions for a version with status

# GET /documents/{doc_id}/versions/{ver_id}/renditions/{rendition_id}/download
# Downloads the rendition file from MinIO

# POST /documents/{doc_id}/versions/{ver_id}/renditions/{rendition_id}/retry
# Re-queues a FAILED rendition for retry
```

### Frontend Rendition Status Badge
```typescript
// RenditionStatusBadge.tsx
function RenditionStatusBadge({ status }: { status: string }) {
  switch (status) {
    case "ready": return <Badge variant="default">PDF Ready</Badge>;
    case "pending": return <Badge variant="secondary">Generating...</Badge>;
    case "failed": return <Badge variant="destructive">Failed</Badge>;
  }
}
```

### Frontend Polling for Pending Status
```typescript
const { data: renditions } = useQuery({
  queryKey: ["renditions", versionId],
  queryFn: () => fetchRenditions(documentId, versionId),
  refetchInterval: (query) => {
    // Poll every 3s while any rendition is pending
    const hasPending = query.state.data?.some(r => r.status === "pending");
    return hasPending ? 3000 : false;
  },
});
```

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Pillow | Thumbnail generation | Yes | 12.1.1 | -- |
| pypdfium2 | PDF-to-image rendering | No (pip install needed) | 5.6.0 target | -- |
| LibreOffice headless | Office-to-PDF conversion | No (not on dev machine) | -- | Task fails gracefully with status=FAILED |
| Redis | Celery broker | Yes (Docker) | 7.x | -- |
| MinIO | File storage | Yes (Docker) | latest | -- |

**Missing dependencies with no fallback:**
- pypdfium2 must be added to pyproject.toml dependencies

**Missing dependencies with fallback:**
- LibreOffice: Not available on Windows dev machine. Tasks gracefully fail. Full functionality available in Docker deployment.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_renditions.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REND-01 | PDF rendition auto-generated on upload | unit | `pytest tests/test_renditions.py::test_upload_triggers_pdf_rendition -x` | Wave 0 |
| REND-02 | Thumbnail auto-generated on upload | unit | `pytest tests/test_renditions.py::test_upload_triggers_thumbnail -x` | Wave 0 |
| REND-03 | Download PDF rendition of any version | integration | `pytest tests/test_renditions.py::test_download_pdf_rendition -x` | Wave 0 |
| REND-04 | Rendition status visible + retry on failure | integration | `pytest tests/test_renditions.py::test_rendition_status_and_retry -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_renditions.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_renditions.py` -- covers REND-01 through REND-04
- [ ] Mock strategies for LibreOffice subprocess and pypdfium2 rendering

## Key Implementation Notes

### Checkin Event Gap
The current `checkin_document()` in document_service.py does NOT emit a `document.uploaded` event. New versions created via checkin will not trigger rendition generation unless:
1. We add event emission to `checkin_document()`, OR
2. We call rendition dispatch directly from `checkin_document()` after creating the version

**Recommendation:** Add `document.version_created` event emission to `checkin_document()` and listen for both `document.uploaded` and `document.version_created` in the rendition handler. Alternatively, trigger renditions from both upload and checkin service methods directly.

### MinIO Bucket Strategy
Use the same `documents` bucket but with a key prefix that distinguishes renditions:
- Source: `{doc_id}/{version_id}` (existing pattern)
- Rendition: `{doc_id}/{version_id}/renditions/{type}.{ext}` (new pattern)

### Docker Compose Addition
A dedicated rendition worker should be added to docker-compose.yml:
```yaml
celery-rendition-worker:
  build: .
  environment:
    - DATABASE_URL=...
    - REDIS_URL=...
    - MINIO_ENDPOINT=minio:9000
  depends_on:
    - db
    - redis
    - minio
  command: celery -A app.celery_app worker --loglevel=info -Q renditions --concurrency=1
```
Using `--concurrency=1` avoids LibreOffice global lock issues. A dedicated queue `renditions` isolates heavy conversion work from the main worker.

### Content Type Decision Matrix
| Source Content Type | PDF Rendition Strategy | Thumbnail Strategy |
|--------------------|-----------------------|-------------------|
| application/pdf | Pass-through (copy source) | pypdfium2 first page render |
| image/* | Skip PDF rendition | Pillow resize |
| Office formats (docx, xlsx, etc.) | LibreOffice headless conversion | Convert to PDF first, then pypdfium2 |
| text/plain, text/csv | LibreOffice headless conversion | Convert to PDF first, then pypdfium2 |
| Other/unknown | Skip with status FAILED ("unsupported") | Skip with status FAILED ("unsupported") |

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `src/app/services/document_service.py`, `src/app/services/event_bus.py`, `src/app/services/event_handlers.py`, `src/app/tasks/notification.py` -- established patterns
- Codebase analysis: `src/app/core/minio_client.py` -- MinIO integration pattern
- Codebase analysis: `src/app/celery_app.py` -- Celery configuration
- Pillow 12.1.1 -- verified installed via `pip show`
- pypdfium2 5.6.0 -- verified available on PyPI

### Secondary (MEDIUM confidence)
- LibreOffice headless CLI interface -- well-documented, stable across versions
- pypdfium2 Windows compatibility -- v5.x ships pre-built wheels for Windows

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries verified, patterns match existing codebase
- Architecture: HIGH - Directly extends existing event bus + Celery task + MinIO patterns
- Pitfalls: HIGH - LibreOffice concurrency and checkin gap identified from code analysis

**Research date:** 2026-04-06
**Valid until:** 2026-05-06 (stable domain, 30-day validity)
