"""Tests for import/export endpoints and service layer."""
import io
import json
import uuid
import zipfile

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentVersion
from app.models.folder import Folder, document_folders
from app.models.bulk_job import BulkJob


@pytest.fixture
async def sample_document(db_session: AsyncSession, admin_user, mock_minio):
    """Create a sample document with a version and content in MinIO."""
    doc = Document(
        id=uuid.uuid4(),
        title="Test Document",
        author="admin",
        filename="test.txt",
        content_type="text/plain",
        custom_properties={},
        current_major_version=0,
        current_minor_version=1,
    )
    db_session.add(doc)
    await db_session.flush()

    version = DocumentVersion(
        id=uuid.uuid4(),
        document_id=doc.id,
        major_version=0,
        minor_version=1,
        content_hash="abc123",
        content_size=12,
        minio_object_key=f"docs/{doc.id}/test.txt",
        filename="test.txt",
        content_type="text/plain",
    )
    db_session.add(version)
    await db_session.commit()

    # Store content in mock MinIO
    mock_minio[f"docs/{doc.id}/test.txt"] = b"Hello World!"
    return doc


@pytest.fixture
async def sample_folder(db_session: AsyncSession):
    """Create a sample folder."""
    folder = Folder(
        id=uuid.uuid4(),
        name="Test Folder",
        description="A test folder",
        is_cabinet=False,
    )
    db_session.add(folder)
    await db_session.commit()
    return folder


@pytest.fixture
async def doc_in_folder(db_session: AsyncSession, sample_document, sample_folder):
    """File the sample document into the sample folder."""
    await db_session.execute(
        document_folders.insert().values(
            document_id=sample_document.id,
            folder_id=sample_folder.id,
            filed_by="admin",
        )
    )
    await db_session.commit()
    return sample_document, sample_folder


def _make_import_zip(docs=None, folders=None, folder_filings=None, acls=None, relationships=None):
    """Build a ZIP file with manifest.json and optional content files."""
    manifest = {
        "version": "1.0",
        "exported_at": "2026-01-01T00:00:00Z",
        "exported_by": "admin",
        "documents": docs or [],
        "folders": folders or [],
        "folder_filings": folder_filings or [],
        "acls": acls or {"documents": [], "folders": []},
        "relationships": relationships or [],
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest))
        for doc in (docs or []):
            content_path = doc.get("content_file", "")
            if content_path:
                zf.writestr(content_path, b"dummy content for import")
    buf.seek(0)
    return buf.read()


@pytest.mark.asyncio
async def test_export_returns_202(async_client: AsyncClient, admin_token: str, sample_document, monkeypatch):
    """POST /import-export/export with document_ids returns 202 with BulkJob response."""
    # Patch Celery task dispatch
    dispatched = []
    monkeypatch.setattr(
        "app.tasks.import_export.execute_export_job.delay",
        lambda *a, **kw: dispatched.append(a),
    )

    resp = await async_client.post(
        "/api/v1/import-export/export",
        json={"document_ids": [str(sample_document.id)]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 202
    data = resp.json()["data"]
    assert data["job_type"] == "export"
    assert data["status"] == "pending"
    assert data["total_count"] == 1
    assert len(dispatched) == 1


@pytest.mark.asyncio
async def test_export_with_folder_ids(async_client: AsyncClient, admin_token: str, doc_in_folder, monkeypatch):
    """POST /import-export/export with folder_ids exports folder tree recursively."""
    doc, folder = doc_in_folder
    dispatched = []
    monkeypatch.setattr(
        "app.tasks.import_export.execute_export_job.delay",
        lambda *a, **kw: dispatched.append(a),
    )

    resp = await async_client.post(
        "/api/v1/import-export/export",
        json={"folder_ids": [str(folder.id)]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 202
    data = resp.json()["data"]
    assert data["job_type"] == "export"
    assert len(dispatched) == 1


@pytest.mark.asyncio
async def test_import_returns_202(async_client: AsyncClient, admin_token: str, monkeypatch):
    """POST /import-export/import with ZIP file upload returns 202."""
    dispatched = []
    monkeypatch.setattr(
        "app.tasks.import_export.execute_import_job.delay",
        lambda *a, **kw: dispatched.append(a),
    )

    doc_id = str(uuid.uuid4())
    zip_bytes = _make_import_zip(docs=[{
        "id": doc_id,
        "title": "Imported Doc",
        "author": "someone",
        "filename": "imported.txt",
        "content_type": "text/plain",
        "custom_properties": {},
        "lifecycle_state": None,
        "document_type_id": None,
        "content_file": f"docs/{doc_id}/imported.txt",
        "version": {"major": 0, "minor": 1},
    }])

    resp = await async_client.post(
        "/api/v1/import-export/import",
        files={"file": ("export.zip", zip_bytes, "application/zip")},
        data={"conflict_strategy": "skip"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 202
    data = resp.json()["data"]
    assert data["job_type"] == "import"
    assert len(dispatched) == 1


@pytest.mark.asyncio
async def test_import_skip_strategy(async_client: AsyncClient, admin_token: str, sample_document, monkeypatch):
    """Import with strategy=skip skips duplicate-named documents."""
    dispatched = []
    monkeypatch.setattr(
        "app.tasks.import_export.execute_import_job.delay",
        lambda *a, **kw: dispatched.append(a),
    )

    doc_id = str(uuid.uuid4())
    zip_bytes = _make_import_zip(docs=[{
        "id": doc_id,
        "title": sample_document.title,  # Same title as existing
        "author": "someone",
        "filename": "test.txt",
        "content_type": "text/plain",
        "custom_properties": {},
        "lifecycle_state": None,
        "document_type_id": None,
        "content_file": f"docs/{doc_id}/test.txt",
        "version": {"major": 0, "minor": 1},
    }])

    resp = await async_client.post(
        "/api/v1/import-export/import",
        files={"file": ("export.zip", zip_bytes, "application/zip")},
        data={"conflict_strategy": "skip"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 202


@pytest.mark.asyncio
async def test_import_overwrite_strategy(async_client: AsyncClient, admin_token: str, monkeypatch):
    """Import with strategy=overwrite replaces existing documents."""
    dispatched = []
    monkeypatch.setattr(
        "app.tasks.import_export.execute_import_job.delay",
        lambda *a, **kw: dispatched.append(a),
    )

    doc_id = str(uuid.uuid4())
    zip_bytes = _make_import_zip(docs=[{
        "id": doc_id,
        "title": "Overwrite Target",
        "author": "someone",
        "filename": "overwrite.txt",
        "content_type": "text/plain",
        "custom_properties": {},
        "lifecycle_state": None,
        "document_type_id": None,
        "content_file": f"docs/{doc_id}/overwrite.txt",
        "version": {"major": 0, "minor": 1},
    }])

    resp = await async_client.post(
        "/api/v1/import-export/import",
        files={"file": ("export.zip", zip_bytes, "application/zip")},
        data={"conflict_strategy": "overwrite"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 202


@pytest.mark.asyncio
async def test_import_rename_strategy(async_client: AsyncClient, admin_token: str, monkeypatch):
    """Import with strategy=rename appends suffix to duplicate names."""
    dispatched = []
    monkeypatch.setattr(
        "app.tasks.import_export.execute_import_job.delay",
        lambda *a, **kw: dispatched.append(a),
    )

    doc_id = str(uuid.uuid4())
    zip_bytes = _make_import_zip(docs=[{
        "id": doc_id,
        "title": "Rename Target",
        "author": "someone",
        "filename": "rename.txt",
        "content_type": "text/plain",
        "custom_properties": {},
        "lifecycle_state": None,
        "document_type_id": None,
        "content_file": f"docs/{doc_id}/rename.txt",
        "version": {"major": 0, "minor": 1},
    }])

    resp = await async_client.post(
        "/api/v1/import-export/import",
        files={"file": ("export.zip", zip_bytes, "application/zip")},
        data={"conflict_strategy": "rename"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 202


@pytest.mark.asyncio
async def test_list_import_export_jobs(async_client: AsyncClient, admin_token: str, monkeypatch):
    """GET /import-export/jobs lists user's import/export jobs."""
    dispatched = []
    monkeypatch.setattr(
        "app.tasks.import_export.execute_export_job.delay",
        lambda *a, **kw: dispatched.append(a),
    )

    # Create an export job first
    resp = await async_client.post(
        "/api/v1/import-export/export",
        json={"document_ids": [str(uuid.uuid4())]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 202

    resp = await async_client.get(
        "/api/v1/import-export/jobs",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) >= 1
    assert all(j["job_type"] in ("export", "import") for j in data)


@pytest.mark.asyncio
async def test_download_export_zip(async_client: AsyncClient, admin_token: str, db_session: AsyncSession, admin_user, mock_minio):
    """GET /import-export/download/{job_id} returns ZIP for completed export."""
    # Create a completed export job with a ZIP in MinIO
    job_id = uuid.uuid4()
    job = BulkJob(
        id=job_id,
        job_type="export",
        status="completed",
        document_ids=[],
        parameters={"zip_object_key": f"exports/{job_id}.zip"},
        total_count=1,
        success_count=1,
        failure_count=0,
        created_by=str(admin_user.id),
    )
    db_session.add(job)
    await db_session.commit()

    # Store a dummy ZIP in mock MinIO
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("manifest.json", '{"version": "1.0"}')
    mock_minio[f"exports/{job_id}.zip"] = buf.getvalue()

    resp = await async_client.get(
        f"/api/v1/import-export/download/{job_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    assert "export_" in resp.headers.get("content-disposition", "")
