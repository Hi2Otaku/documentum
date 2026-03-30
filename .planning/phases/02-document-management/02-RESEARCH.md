# Phase 2: Document Management - Research

**Researched:** 2026-03-30
**Domain:** Document management with object storage (MinIO) + PostgreSQL metadata + versioning + locking
**Confidence:** HIGH

## Summary

Phase 2 implements a document management system where file content is stored in MinIO and metadata/versioning/locking state lives in PostgreSQL. The core workflow is Documentum-style check-in/check-out: a user uploads a document (creating version 0.1), checks it out (acquiring an exclusive lock), edits locally, and checks it back in (creating a new minor version with SHA-256 dedup). Admins can force-unlock documents. Version history is browsable and any version is downloadable.

The existing codebase already provides the foundation: BaseModel with UUID PKs, audit service, service-layer pattern, envelope responses, JWT auth, async SQLAlchemy with PostgreSQL, and a MinIO container in docker-compose. The `minio` Python SDK 7.2.20 is already installed. The main work is: (1) new Document and DocumentVersion models, (2) a MinIO client singleton, (3) document service with upload/checkout/checkin/unlock/download logic, (4) document router at `/api/v1/documents`, and (5) Alembic migration.

**Primary recommendation:** Follow the established service-layer pattern exactly. Create a `minio_client.py` module in `src/app/core/` that initializes the Minio client from settings. The Document model owns lock state (locked_by, locked_at) and custom_properties (JSON column). DocumentVersion tracks each version's content hash, MinIO object key, and version numbers.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Version numbering: Major versions on approval-triggered check-in (lifecycle), minor on regular check-in. Initial version is 0.1 (draft). Becomes 1.0 on first major promotion. No new version if content unchanged (SHA-256 comparison).
- MinIO storage layout: Single bucket "documents" with UUID keys: `{doc_id}/{version_id}`. Original filename in metadata only.
- Custom metadata: JSONB column `custom_properties` on document table. Schema-free, any JSON key-value pairs.

### Claude's Discretion
- Upload size limits and chunked upload strategy
- File type detection/MIME handling
- Download endpoint design (streaming vs buffered)
- Error handling for MinIO connectivity issues

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DOC-01 | User can upload documents (any file type) to the repository | MinIO `put_object` with `python-multipart` (already installed via FastAPI). UploadFile from FastAPI handles multipart form data. |
| DOC-02 | System tracks document versions with major/minor numbering | DocumentVersion model with `major_version` and `minor_version` integer fields. Logic: increment minor on check-in, major on lifecycle promotion (Phase 7 integration point). |
| DOC-03 | User can check out a document (locks it for editing) | `locked_by` (FK to users) and `locked_at` (datetime) columns on Document model. Service checks lock state before allowing checkout. |
| DOC-04 | User can check in a document (creates new version, releases lock) | Service: verify caller holds lock, compute SHA-256 of uploaded content, compare with previous version hash, create new DocumentVersion if different, upload to MinIO, clear lock. |
| DOC-05 | Admin can force-unlock a checked-out document | Admin-only endpoint that clears `locked_by`/`locked_at` without requiring the lock owner. Uses `get_current_active_admin` dependency. |
| DOC-06 | User can view and download any version of a document | List versions endpoint + download endpoint using MinIO `get_object` with streaming response. |
| DOC-07 | Documents have extensible metadata (title, author, custom properties) | `title`, `author` as regular columns, `custom_properties` as JSON column on Document model. |
| DOC-08 | Documents are stored in MinIO with metadata in PostgreSQL | Architecture: MinIO for file blobs, PostgreSQL for Document + DocumentVersion models. MinIO object key = `{doc_id}/{version_id}`. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| minio | 7.2.20 | S3-compatible object storage client | Already installed. Official MinIO Python SDK. Handles put_object, get_object, bucket creation. |
| fastapi | 0.135.x | HTTP framework | Already in use. UploadFile for multipart uploads, StreamingResponse for downloads. |
| sqlalchemy | 2.0.x | ORM | Already in use. Async models with mapped_column. |
| python-multipart | (bundled) | Multipart form parsing | Already installed via `fastapi[standard]`. Required for `UploadFile`. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-magic | 0.4.27 | MIME type detection from file content | Better than trusting client Content-Type header. Falls back to `mimetypes` stdlib if unavailable. |
| hashlib | (stdlib) | SHA-256 content hashing | Version dedup -- skip creating new version if content unchanged. |
| mimetypes | (stdlib) | MIME type from filename extension | Fallback when python-magic unavailable or for simple cases. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| python-magic | mimetypes (stdlib) | python-magic reads file headers (more accurate) but requires libmagic C library. On Windows this needs `python-magic-bin`. Use `mimetypes` stdlib as primary since it avoids the C dependency and is sufficient for storing content type. |
| Streaming download | Presigned URLs | Presigned URLs offload bandwidth to MinIO directly but expose MinIO endpoint. Streaming through FastAPI keeps MinIO internal. Use streaming for now, presigned URLs can be added later. |

**Installation:**
```bash
pip install minio
```
Note: `minio` is already installed (7.2.20) but NOT in pyproject.toml dependencies. Must be added.

## Architecture Patterns

### Recommended Project Structure
```
src/app/
├── core/
│   ├── minio_client.py     # MinIO client singleton + bucket init
│   └── config.py           # Add MINIO_* settings
├── models/
│   ├── document.py          # Document + DocumentVersion models
│   └── enums.py             # Add DocumentLockState if needed
├── schemas/
│   └── document.py          # Pydantic schemas for request/response
├── services/
│   └── document_service.py  # All document business logic
├── routers/
│   └── documents.py         # HTTP endpoints
```

### Pattern 1: MinIO Client as Dependency
**What:** Initialize MinIO client in a module, expose it as a FastAPI dependency or module-level singleton.
**When to use:** Every document upload/download operation.
**Example:**
```python
# src/app/core/minio_client.py
from minio import Minio
from app.core.config import settings

minio_client = Minio(
    endpoint=settings.minio_endpoint,   # "minio:9000" or "localhost:9000"
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    secure=settings.minio_secure,       # False for local dev
)

async def ensure_bucket():
    """Create the documents bucket if it doesn't exist. Call at startup."""
    if not minio_client.bucket_exists("documents"):
        minio_client.make_bucket("documents")
```

### Pattern 2: Document Upload Flow
**What:** Multipart upload through FastAPI, stream to MinIO, save metadata to PostgreSQL.
**When to use:** DOC-01 upload and DOC-04 check-in.
**Example:**
```python
# In document_service.py
import hashlib
import uuid
from io import BytesIO
from fastapi import UploadFile

async def upload_document(
    db: AsyncSession,
    file: UploadFile,
    title: str,
    author: str | None,
    custom_properties: dict | None,
    user_id: str,
) -> Document:
    doc_id = uuid.uuid4()
    version_id = uuid.uuid4()

    # Read file content for hashing and MinIO upload
    content = await file.read()
    content_hash = hashlib.sha256(content).hexdigest()
    content_size = len(content)

    # Upload to MinIO: key = {doc_id}/{version_id}
    object_name = f"{doc_id}/{version_id}"
    minio_client.put_object(
        bucket_name="documents",
        object_name=object_name,
        data=BytesIO(content),
        length=content_size,
        content_type=file.content_type or "application/octet-stream",
    )

    # Create Document record
    document = Document(
        id=doc_id,
        title=title,
        author=author,
        filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
        custom_properties=custom_properties or {},
        created_by=user_id,
    )
    db.add(document)
    await db.flush()

    # Create initial DocumentVersion (0.1)
    version = DocumentVersion(
        id=version_id,
        document_id=doc_id,
        major_version=0,
        minor_version=1,
        content_hash=content_hash,
        content_size=content_size,
        minio_object_key=object_name,
        filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
        created_by=user_id,
    )
    db.add(version)
    await db.flush()

    # Audit
    await create_audit_record(
        db,
        entity_type="document",
        entity_id=str(doc_id),
        action="upload",
        user_id=user_id,
        after_state={"title": title, "version": "0.1"},
    )
    return document
```

### Pattern 3: Check-Out / Check-In Locking
**What:** Optimistic locking on Document row. Check-out sets `locked_by`, check-in clears it and creates new version.
**When to use:** DOC-03, DOC-04, DOC-05.
**Example:**
```python
async def checkout_document(
    db: AsyncSession, document_id: uuid.UUID, user_id: str
) -> Document:
    doc = await _get_document_or_404(db, document_id)
    if doc.locked_by is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Document is locked by user {doc.locked_by}",
        )
    doc.locked_by = uuid.UUID(user_id)
    doc.locked_at = datetime.now(timezone.utc)
    await db.flush()

    await create_audit_record(
        db, entity_type="document", entity_id=str(document_id),
        action="checkout", user_id=user_id,
    )
    return doc
```

### Pattern 4: Streaming Download
**What:** Stream MinIO object through FastAPI using StreamingResponse.
**When to use:** DOC-06 download endpoint.
**Example:**
```python
from fastapi.responses import StreamingResponse

@router.get("/{document_id}/versions/{version_id}/download")
async def download_version(
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    version = await document_service.get_version(db, document_id, version_id)
    response = minio_client.get_object("documents", version.minio_object_key)

    return StreamingResponse(
        response.stream(32 * 1024),
        media_type=version.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{version.filename}"',
            "Content-Length": str(version.content_size),
        },
    )
```

### Anti-Patterns to Avoid
- **Storing files in PostgreSQL BLOB:** Bloats database, slows backups, no presigned URL support. Always use MinIO.
- **Trusting client filename for storage key:** Use UUIDs for MinIO keys. Original filename in metadata only. Prevents path traversal and collisions.
- **Reading entire large file into memory for hashing:** For this phase, reading into memory is acceptable (decide upload size limit, e.g., 100MB). Chunked hashing can be added later.
- **Not closing MinIO response objects:** `get_object` returns an urllib3 response that MUST be closed/released. Use try/finally or context manager pattern.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Object storage | Custom file system manager | MinIO `put_object`/`get_object` | Handles multipart uploads, checksums, concurrent access |
| Content hashing | Custom hash comparison | `hashlib.sha256` | Standard library, no bugs |
| MIME detection | Content-Type parsing | `mimetypes.guess_type()` from stdlib | Handles edge cases, extensible |
| Multipart form parsing | Custom stream parser | FastAPI `UploadFile` | Already handled by python-multipart |
| Streaming response | Custom chunked response | FastAPI `StreamingResponse` | Handles HTTP headers, chunked transfer encoding |

**Key insight:** MinIO SDK handles all the hard parts of object storage (multipart, checksums, retries). The service layer only needs to orchestrate the flow between MinIO and PostgreSQL.

## Common Pitfalls

### Pitfall 1: MinIO Client is Synchronous
**What goes wrong:** The `minio` Python SDK is synchronous (uses urllib3). Calling `put_object`/`get_object` in an async endpoint blocks the event loop.
**Why it happens:** MinIO Python SDK has no async version.
**How to avoid:** Run MinIO calls in a thread pool using `asyncio.to_thread()` or `loop.run_in_executor()`. Alternatively, since FastAPI handles this for `def` (non-async) route handlers by running them in a threadpool, you could use sync service functions -- but this breaks the async pattern established in Phase 1. Use `asyncio.to_thread()` to keep consistency.
**Warning signs:** Slow response times under concurrent requests, event loop blocking warnings.

### Pitfall 2: Not Handling Partial Failures (MinIO up, DB down or vice versa)
**What goes wrong:** File uploaded to MinIO but database insert fails, leaving orphaned objects. Or database updated but MinIO upload fails.
**Why it happens:** MinIO and PostgreSQL are separate systems -- no distributed transaction.
**How to avoid:** Upload to MinIO first, then write to database. If DB fails, clean up the MinIO object. Wrap in try/except. The cost of an orphan MinIO object is lower than a DB record pointing to nothing.
**Warning signs:** Orphaned objects in MinIO bucket, 500 errors on upload.

### Pitfall 3: Version Number Race Conditions
**What goes wrong:** Two concurrent check-ins create the same version number.
**Why it happens:** Reading max version and incrementing is not atomic.
**How to avoid:** Use `SELECT ... FOR UPDATE` on the document row during check-in, or use a unique constraint on `(document_id, major_version, minor_version)`. The check-out lock should already prevent concurrent check-ins for the same document, but the unique constraint is defense-in-depth.
**Warning signs:** Duplicate version numbers in the database.

### Pitfall 4: Forgetting to Release MinIO Response
**What goes wrong:** Connection pool exhaustion, resource leaks.
**Why it happens:** `minio_client.get_object()` returns an urllib3 HTTPResponse that holds a connection.
**How to avoid:** Always call `response.close()` and `response.release_conn()` in a finally block, or use StreamingResponse which handles the iteration and release.
**Warning signs:** "Connection pool is full" errors after many downloads.

### Pitfall 5: JSON vs JSONB for SQLite Test Compatibility
**What goes wrong:** Using `JSONB` type fails on SQLite test database.
**Why it happens:** Phase 1 decision: models are dialect-agnostic, using `JSON` instead of `JSONB`.
**How to avoid:** Use `sqlalchemy.JSON` for the `custom_properties` column, not `sqlalchemy.dialects.postgresql.JSONB`. PostgreSQL will still store it as JSONB internally when using JSON column type.
**Warning signs:** Test failures on SQLite with "no such type: JSONB".

### Pitfall 6: Missing MinIO Bucket on First Request
**What goes wrong:** Upload fails with "NoSuchBucket" error.
**Why it happens:** The "documents" bucket doesn't exist yet.
**How to avoid:** Add bucket creation to the app lifespan startup. Check `bucket_exists()` and `make_bucket()` if needed.
**Warning signs:** 500 error on first upload attempt.

## Code Examples

### Document Model
```python
# src/app/models/document.py
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Document(BaseModel):
    __tablename__ = "documents"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(
        String(255), default="application/octet-stream", nullable=False
    )
    custom_properties: Mapped[dict] = mapped_column(
        JSON, default=dict, nullable=False
    )

    # Lock state
    locked_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("users.id"), nullable=True
    )
    locked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Current version tracking (denormalized for quick access)
    current_major_version: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    current_minor_version: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False
    )

    versions: Mapped[list["DocumentVersion"]] = relationship(
        back_populates="document", order_by="DocumentVersion.created_at"
    )


class DocumentVersion(BaseModel):
    __tablename__ = "document_versions"

    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("documents.id"), nullable=False
    )
    major_version: Mapped[int] = mapped_column(Integer, nullable=False)
    minor_version: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256
    content_size: Mapped[int] = mapped_column(Integer, nullable=False)     # bytes
    minio_object_key: Mapped[str] = mapped_column(String(500), nullable=False)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(
        String(255), default="application/octet-stream", nullable=False
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    document: Mapped["Document"] = relationship(back_populates="versions")

    __table_args__ = (
        # Prevent duplicate version numbers per document
        # Uses Index since UniqueConstraint syntax is identical
        {"comment": "unique_version_per_doc constraint via migration"},
    )
```

### MinIO Client Module
```python
# src/app/core/minio_client.py
import asyncio
import logging
from io import BytesIO

from minio import Minio
from minio.error import S3Error

from app.core.config import settings

logger = logging.getLogger(__name__)

minio_client = Minio(
    endpoint=settings.minio_endpoint,
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    secure=settings.minio_secure,
)

DOCUMENTS_BUCKET = "documents"


async def ensure_documents_bucket():
    """Create the documents bucket if it doesn't exist."""
    def _ensure():
        if not minio_client.bucket_exists(DOCUMENTS_BUCKET):
            minio_client.make_bucket(DOCUMENTS_BUCKET)
            logger.info("Created MinIO bucket: %s", DOCUMENTS_BUCKET)
    await asyncio.to_thread(_ensure)


async def upload_object(
    object_name: str, data: bytes, content_type: str = "application/octet-stream"
) -> str:
    """Upload bytes to MinIO. Returns the object name (key)."""
    def _upload():
        minio_client.put_object(
            bucket_name=DOCUMENTS_BUCKET,
            object_name=object_name,
            data=BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        return object_name
    return await asyncio.to_thread(_upload)


async def download_object(object_name: str) -> bytes:
    """Download object from MinIO. Returns bytes."""
    def _download():
        response = minio_client.get_object(DOCUMENTS_BUCKET, object_name)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()
    return await asyncio.to_thread(_download)


async def delete_object(object_name: str) -> None:
    """Delete object from MinIO."""
    def _delete():
        minio_client.remove_object(DOCUMENTS_BUCKET, object_name)
    await asyncio.to_thread(_delete)
```

### Settings Additions
```python
# Add to src/app/core/config.py Settings class
minio_endpoint: str = "localhost:9000"
minio_access_key: str = "minioadmin"
minio_secret_key: str = "minioadmin"
minio_secure: bool = False
```

### Check-In with SHA-256 Dedup
```python
async def checkin_document(
    db: AsyncSession,
    document_id: uuid.UUID,
    file: UploadFile,
    user_id: str,
    comment: str | None = None,
) -> DocumentVersion | None:
    doc = await _get_document_or_404(db, document_id)

    # Verify caller holds the lock
    if doc.locked_by is None or str(doc.locked_by) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not hold the lock on this document",
        )

    content = await file.read()
    content_hash = hashlib.sha256(content).hexdigest()

    # Check if content is unchanged
    latest_version = await _get_latest_version(db, document_id)
    if latest_version and latest_version.content_hash == content_hash:
        # Release lock without creating new version
        doc.locked_by = None
        doc.locked_at = None
        await db.flush()
        return None  # Signal: no new version created

    # Create new minor version
    new_minor = (latest_version.minor_version + 1) if latest_version else 1
    new_major = latest_version.major_version if latest_version else 0

    version_id = uuid.uuid4()
    object_name = f"{document_id}/{version_id}"

    await upload_object(object_name, content, file.content_type or "application/octet-stream")

    version = DocumentVersion(
        id=version_id,
        document_id=document_id,
        major_version=new_major,
        minor_version=new_minor,
        content_hash=content_hash,
        content_size=len(content),
        minio_object_key=object_name,
        filename=file.filename or doc.filename,
        content_type=file.content_type or doc.content_type,
        comment=comment,
        created_by=user_id,
    )
    db.add(version)

    # Update document current version + release lock
    doc.current_major_version = new_major
    doc.current_minor_version = new_minor
    doc.locked_by = None
    doc.locked_at = None
    await db.flush()

    await create_audit_record(
        db, entity_type="document", entity_id=str(document_id),
        action="checkin", user_id=user_id,
        after_state={"version": f"{new_major}.{new_minor}"},
    )
    return version
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| passlib for hashing | hashlib (stdlib) for content hashing | N/A | Content hash is SHA-256 via stdlib, no extra dependency |
| JSONB column type | JSON column type (dialect-agnostic) | Phase 1 decision | Works on both PostgreSQL and SQLite for testing |
| Sync MinIO calls in async code | `asyncio.to_thread()` wrapping | Python 3.9+ | Prevents event loop blocking |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_documents.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DOC-01 | Upload document via multipart form | integration | `pytest tests/test_documents.py::test_upload_document -x` | Wave 0 |
| DOC-02 | Version numbers increment correctly (0.1, 0.2, etc.) | integration | `pytest tests/test_documents.py::test_version_numbering -x` | Wave 0 |
| DOC-03 | Checkout locks document, rejects second checkout | integration | `pytest tests/test_documents.py::test_checkout_locking -x` | Wave 0 |
| DOC-04 | Check-in creates new version, releases lock, dedup on unchanged | integration | `pytest tests/test_documents.py::test_checkin_creates_version -x` | Wave 0 |
| DOC-05 | Admin force-unlock clears lock | integration | `pytest tests/test_documents.py::test_admin_force_unlock -x` | Wave 0 |
| DOC-06 | List versions + download specific version | integration | `pytest tests/test_documents.py::test_download_version -x` | Wave 0 |
| DOC-07 | Custom metadata set and queried | integration | `pytest tests/test_documents.py::test_custom_metadata -x` | Wave 0 |
| DOC-08 | MinIO storage verified (mock in tests) | unit | `pytest tests/test_documents.py::test_minio_integration -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_documents.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before verification

### Wave 0 Gaps
- [ ] `tests/test_documents.py` -- covers DOC-01 through DOC-08
- [ ] MinIO mock fixture in `tests/conftest.py` -- mock `minio_client` for unit tests (no real MinIO in CI)

### Test Strategy: Mocking MinIO
Since tests run on SQLite in-memory (no Docker), MinIO must be mocked. Use `unittest.mock.patch` or a conftest fixture:
```python
@pytest.fixture
def mock_minio(monkeypatch):
    """Replace MinIO operations with in-memory dict storage."""
    storage = {}

    async def mock_upload(object_name, data, content_type="application/octet-stream"):
        storage[object_name] = data
        return object_name

    async def mock_download(object_name):
        if object_name not in storage:
            raise Exception("NoSuchKey")
        return storage[object_name]

    async def mock_delete(object_name):
        storage.pop(object_name, None)

    monkeypatch.setattr("app.core.minio_client.upload_object", mock_upload)
    monkeypatch.setattr("app.core.minio_client.download_object", mock_download)
    monkeypatch.setattr("app.core.minio_client.delete_object", mock_delete)
    return storage
```

## API Endpoint Design

| Method | Path | Purpose | Auth |
|--------|------|---------|------|
| POST | `/api/v1/documents` | Upload new document | User |
| GET | `/api/v1/documents` | List documents (paginated) | User |
| GET | `/api/v1/documents/{id}` | Get document metadata | User |
| PUT | `/api/v1/documents/{id}` | Update document metadata (title, custom_properties) | User |
| DELETE | `/api/v1/documents/{id}` | Soft delete document | Admin |
| POST | `/api/v1/documents/{id}/checkout` | Check out (lock) | User |
| POST | `/api/v1/documents/{id}/checkin` | Check in (new version + unlock) | User (lock holder) |
| POST | `/api/v1/documents/{id}/unlock` | Force unlock | Admin |
| GET | `/api/v1/documents/{id}/versions` | List version history | User |
| GET | `/api/v1/documents/{id}/versions/{vid}/download` | Download specific version | User |

## Open Questions

1. **Upload size limit**
   - What we know: FastAPI/Starlette default is no limit. MinIO handles multipart automatically for large objects.
   - What's unclear: What size limit is appropriate for this system.
   - Recommendation: Set 100MB default via config. Read file content into memory for hashing (acceptable at 100MB). For larger files, implement chunked hashing later.

2. **Major version promotion trigger**
   - What we know: Major versions happen on lifecycle approval (Phase 7).
   - What's unclear: The exact integration point -- will Phase 7 call a `promote_version()` function?
   - Recommendation: Build a `promote_to_major_version()` service function now that Phase 7 can call. It creates a new major version (e.g., 0.3 becomes 1.0) by incrementing major and resetting minor to 0.

3. **Download: streaming from MinIO vs buffered**
   - What we know: MinIO `get_object` returns an urllib3 response with `.stream()` method.
   - Recommendation: Use `StreamingResponse` with MinIO's `.stream(chunk_size)` for efficient memory usage. Wrap the sync stream call in `asyncio.to_thread()`.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| MinIO (Docker) | File storage | Defined in docker-compose.yml | latest | -- |
| minio (Python SDK) | MinIO client | Installed | 7.2.20 | -- |
| PostgreSQL (Docker) | Metadata storage | Defined in docker-compose.yml | 16-alpine | -- |
| python-multipart | File upload parsing | Installed via fastapi[standard] | -- | -- |

**Missing dependencies with no fallback:**
- `minio` must be added to pyproject.toml `dependencies` list (installed but not declared)
- MinIO environment variables (`MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`) must be added to docker-compose.yml `api` service

**Missing dependencies with fallback:**
- None

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `src/app/models/`, `src/app/services/`, `src/app/routers/`, `src/app/core/` -- established patterns
- [MinIO Python SDK GitHub](https://github.com/minio/minio-py) -- put_object, get_object API examples
- [MinIO Python Client API Reference](https://docs.min.io/enterprise/aistor-object-store/developers/sdk/python/api/) -- official API docs
- PyPI `minio` package -- verified version 7.2.20 installed

### Secondary (MEDIUM confidence)
- [MinIO put_object examples](https://github.com/minio/minio-py/blob/master/examples/put_object.py) -- verified via WebFetch
- FastAPI UploadFile and StreamingResponse -- from training data, well-established API

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already installed/in use, versions verified
- Architecture: HIGH -- follows established Phase 1 patterns exactly
- Pitfalls: HIGH -- common issues well-documented in MinIO SDK docs and async Python community
- MinIO async wrapping: MEDIUM -- `asyncio.to_thread()` is the standard approach but adds slight complexity

**Research date:** 2026-03-30
**Valid until:** 2026-04-30 (stable domain, no fast-moving dependencies)
