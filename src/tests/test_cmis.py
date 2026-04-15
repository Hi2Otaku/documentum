"""Tests for CMIS 1.1 Browser Binding service layer and endpoints."""

import io
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services import cmis_service


@pytest.fixture(autouse=True)
def mock_celery_tasks(monkeypatch):
    """Prevent ALL Celery tasks from trying to connect to Redis during tests."""
    from unittest.mock import MagicMock

    # Patch the Celery app's send_task to prevent any Redis connection
    monkeypatch.setattr(
        "app.celery_app.celery_app.send_task",
        MagicMock(return_value=MagicMock(id="mock-task-id")),
    )

    # Also patch Task.delay and Task.apply_async at the base class level
    from celery.app.task import Task
    monkeypatch.setattr(Task, "delay", MagicMock(return_value=MagicMock(id="mock-task-id")))
    monkeypatch.setattr(Task, "apply_async", MagicMock(return_value=MagicMock(id="mock-task-id")))


# ── Unit tests for cmis_service ──────────────────────────────────────────────


class TestGetRepositoryInfo:
    def test_returns_required_fields(self):
        root_id = str(uuid.uuid4())
        info = cmis_service.get_repository_info(root_id)
        assert info["repositoryId"] == "documentum-clone"
        assert info["repositoryName"] == "Documentum Clone Repository"
        assert info["cmisVersionSupported"] == "1.1"
        assert "capabilities" in info
        assert info["rootFolderId"] == root_id

    def test_capabilities(self):
        info = cmis_service.get_repository_info(str(uuid.uuid4()))
        caps = info["capabilities"]
        assert caps["capabilityACL"] == "manage"
        assert caps["capabilityQuery"] == "metadataonly"
        assert caps["capabilityContentStreamUpdatability"] == "anytime"
        assert caps["capabilityGetDescendants"] is True
        assert caps["capabilityGetFolderTree"] is True
        assert caps["capabilityMultifiling"] is True
        assert caps["capabilityUnfiling"] is True


class TestGetTypeDefinition:
    def test_document_type(self):
        typedef = cmis_service.get_type_definition("cmis:document")
        assert typedef["id"] == "cmis:document"
        assert typedef["baseId"] == "cmis:document"
        props = typedef["propertyDefinitions"]
        assert "cmis:objectId" in props
        assert "cmis:name" in props
        assert "cmis:baseTypeId" in props
        assert "cmis:objectTypeId" in props
        assert "cmis:createdBy" in props
        assert "cmis:creationDate" in props
        assert "cmis:lastModificationDate" in props
        assert "cmis:contentStreamFileName" in props
        assert "cmis:contentStreamMimeType" in props
        assert "cmis:contentStreamLength" in props
        assert "cmis:isVersionSeriesCheckedOut" in props

    def test_folder_type(self):
        typedef = cmis_service.get_type_definition("cmis:folder")
        assert typedef["id"] == "cmis:folder"
        assert typedef["baseId"] == "cmis:folder"
        props = typedef["propertyDefinitions"]
        assert "cmis:objectId" in props
        assert "cmis:name" in props
        assert "cmis:baseTypeId" in props
        assert "cmis:parentId" in props

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError):
            cmis_service.get_type_definition("cmis:unknown")


class TestToCmisDocument:
    def _make_doc(self, **overrides):
        defaults = {
            "id": uuid.uuid4(),
            "title": "Report.pdf",
            "filename": "report.pdf",
            "content_type": "application/pdf",
            "created_by": "user1",
            "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "updated_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
            "locked_by": None,
            "current_major_version": 1,
            "current_minor_version": 0,
            "lifecycle_state": "draft",
            "custom_properties": {},
        }
        defaults.update(overrides)
        doc = MagicMock()
        for k, v in defaults.items():
            setattr(doc, k, v)
        return doc

    def test_basic_mapping(self):
        doc = self._make_doc()
        props = cmis_service.to_cmis_document(doc)
        assert props["cmis:objectId"] == str(doc.id)
        assert props["cmis:name"] == "Report.pdf"
        assert props["cmis:contentStreamFileName"] == "report.pdf"
        assert props["cmis:contentStreamMimeType"] == "application/pdf"
        assert props["cmis:createdBy"] == "user1"
        assert props["cmis:baseTypeId"] == "cmis:document"
        assert props["cmis:objectTypeId"] == "cmis:document"
        assert props["cmis:isVersionSeriesCheckedOut"] is False
        assert props["cmis:versionLabel"] == "1.0"

    def test_checked_out_document(self):
        lock_id = uuid.uuid4()
        doc = self._make_doc(locked_by=lock_id)
        props = cmis_service.to_cmis_document(doc)
        assert props["cmis:isVersionSeriesCheckedOut"] is True
        assert props["cmis:versionSeriesCheckedOutBy"] == str(lock_id)

    def test_with_version_adds_content_length(self):
        doc = self._make_doc()
        version = MagicMock()
        version.content_size = 12345
        props = cmis_service.to_cmis_document(doc, version=version)
        assert props["cmis:contentStreamLength"] == 12345


class TestToCmisFolder:
    def _make_folder(self, **overrides):
        defaults = {
            "id": uuid.uuid4(),
            "name": "Reports",
            "parent_id": uuid.uuid4(),
            "is_cabinet": False,
            "created_by": "admin",
            "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "updated_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
        }
        defaults.update(overrides)
        folder = MagicMock()
        for k, v in defaults.items():
            setattr(folder, k, v)
        return folder

    def test_basic_mapping(self):
        folder = self._make_folder()
        props = cmis_service.to_cmis_folder(folder)
        assert props["cmis:objectId"] == str(folder.id)
        assert props["cmis:name"] == "Reports"
        assert props["cmis:baseTypeId"] == "cmis:folder"
        assert props["cmis:objectTypeId"] == "cmis:folder"
        assert props["cmis:parentId"] == str(folder.parent_id)

    def test_cabinet_has_no_parent(self):
        folder = self._make_folder(parent_id=None, is_cabinet=True)
        props = cmis_service.to_cmis_folder(folder)
        assert props["cmis:parentId"] is None


class TestFromCmisProperties:
    def test_name_to_title(self):
        result = cmis_service.from_cmis_properties({"cmis:name": "test.pdf"})
        assert result["title"] == "test.pdf"

    def test_multiple_properties(self):
        result = cmis_service.from_cmis_properties({
            "cmis:name": "doc.pdf",
            "cmis:contentStreamFileName": "doc.pdf",
        })
        assert result["title"] == "doc.pdf"
        assert result["filename"] == "doc.pdf"

    def test_unknown_properties_ignored(self):
        result = cmis_service.from_cmis_properties({
            "cmis:name": "test.pdf",
            "custom:field": "value",
        })
        assert "custom:field" not in result
        assert result["title"] == "test.pdf"


# ── Integration tests for CMIS Browser Binding endpoints ─────────────────────


@pytest.mark.asyncio
class TestCmisRepositoryEndpoint:
    async def test_get_repository_info(self, async_client: AsyncClient, admin_token: str):
        resp = await async_client.get(
            "/api/v1/cmis/browser",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["cmisVersionSupported"] == "1.1"
        assert data["repositoryId"] == "documentum-clone"
        assert "rootFolderId" in data

    async def test_repository_info_requires_auth(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/cmis/browser")
        assert resp.status_code == 401


@pytest.mark.asyncio
class TestCmisDocumentCrud:
    async def _create_cabinet(self, async_client: AsyncClient, admin_token: str) -> str:
        """Create a cabinet and return its ID."""
        resp = await async_client.post(
            "/api/v1/folders/",
            json={"name": "CMIS Test Cabinet", "description": "Test"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201
        return resp.json()["data"]["id"]

    async def _upload_doc_via_cmis(
        self, async_client: AsyncClient, admin_token: str, cabinet_id: str
    ) -> dict:
        """Upload a document via CMIS createDocument and return the response."""
        resp = await async_client.post(
            f"/api/v1/cmis/browser/root/{cabinet_id}",
            data={
                "cmisaction": "createDocument",
                "propertyId[0]": "cmis:name",
                "propertyValue[0]": "test-cmis.txt",
            },
            files={"file": ("test-cmis.txt", b"CMIS test content", "text/plain")},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        return resp.json()

    async def test_create_document(self, async_client: AsyncClient, admin_token: str):
        cabinet_id = await self._create_cabinet(async_client, admin_token)
        data = await self._upload_doc_via_cmis(async_client, admin_token, cabinet_id)
        props = data["succinctProperties"]
        assert props["cmis:name"] == "test-cmis.txt"
        assert props["cmis:baseTypeId"] == "cmis:document"
        assert "cmis:objectId" in props

    async def test_get_object(self, async_client: AsyncClient, admin_token: str):
        cabinet_id = await self._create_cabinet(async_client, admin_token)
        created = await self._upload_doc_via_cmis(async_client, admin_token, cabinet_id)
        doc_id = created["succinctProperties"]["cmis:objectId"]

        resp = await async_client.get(
            f"/api/v1/cmis/browser/root/{doc_id}",
            params={"cmisselector": "object"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        props = resp.json()["succinctProperties"]
        assert props["cmis:objectId"] == doc_id
        assert props["cmis:name"] == "test-cmis.txt"

    async def test_delete_document(self, async_client: AsyncClient, admin_token: str):
        cabinet_id = await self._create_cabinet(async_client, admin_token)
        created = await self._upload_doc_via_cmis(async_client, admin_token, cabinet_id)
        doc_id = created["succinctProperties"]["cmis:objectId"]

        resp = await async_client.post(
            f"/api/v1/cmis/browser/root/{doc_id}",
            data={"cmisaction": "delete"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200

        # Object should now be not found
        resp = await async_client.get(
            f"/api/v1/cmis/browser/root/{doc_id}",
            params={"cmisselector": "object"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404

    async def test_get_object_requires_auth(self, async_client: AsyncClient):
        fake_id = str(uuid.uuid4())
        resp = await async_client.get(f"/api/v1/cmis/browser/root/{fake_id}")
        assert resp.status_code == 401


@pytest.mark.asyncio
class TestCmisFolderNavigation:
    async def _create_cabinet(self, async_client: AsyncClient, admin_token: str) -> str:
        resp = await async_client.post(
            "/api/v1/folders/",
            json={"name": "Nav Test Cabinet", "description": "Test"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201
        return resp.json()["data"]["id"]

    async def test_get_children(self, async_client: AsyncClient, admin_token: str):
        cabinet_id = await self._create_cabinet(async_client, admin_token)

        # Create a subfolder via CMIS
        resp = await async_client.post(
            f"/api/v1/cmis/browser/root/{cabinet_id}",
            data={
                "cmisaction": "createFolder",
                "propertyId[0]": "cmis:name",
                "propertyValue[0]": "SubFolder1",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200

        # Upload a document
        await async_client.post(
            f"/api/v1/cmis/browser/root/{cabinet_id}",
            data={
                "cmisaction": "createDocument",
                "propertyId[0]": "cmis:name",
                "propertyValue[0]": "child-doc.txt",
            },
            files={"file": ("child-doc.txt", b"content", "text/plain")},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Get children
        resp = await async_client.get(
            f"/api/v1/cmis/browser/root/{cabinet_id}",
            params={"cmisselector": "children"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["numItems"] >= 2
        types = {obj["succinctProperties"]["cmis:baseTypeId"] for obj in data["objects"]}
        assert "cmis:folder" in types
        assert "cmis:document" in types

    async def test_get_descendants(self, async_client: AsyncClient, admin_token: str):
        cabinet_id = await self._create_cabinet(async_client, admin_token)

        # Create a nested structure
        resp = await async_client.post(
            f"/api/v1/cmis/browser/root/{cabinet_id}",
            data={
                "cmisaction": "createFolder",
                "propertyId[0]": "cmis:name",
                "propertyValue[0]": "Level1",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200

        resp = await async_client.get(
            f"/api/v1/cmis/browser/root/{cabinet_id}",
            params={"cmisselector": "descendants"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert "object" in data[0]
        assert "children" in data[0]


@pytest.mark.asyncio
class TestCmisMoveObject:
    async def test_move_document_between_folders(
        self, async_client: AsyncClient, admin_token: str
    ):
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Create two cabinets
        resp = await async_client.post(
            "/api/v1/folders/",
            json={"name": "Source Cabinet", "description": "Source"},
            headers=headers,
        )
        source_id = resp.json()["data"]["id"]

        resp = await async_client.post(
            "/api/v1/folders/",
            json={"name": "Target Cabinet", "description": "Target"},
            headers=headers,
        )
        target_id = resp.json()["data"]["id"]

        # Create document in source
        resp = await async_client.post(
            f"/api/v1/cmis/browser/root/{source_id}",
            data={
                "cmisaction": "createDocument",
                "propertyId[0]": "cmis:name",
                "propertyValue[0]": "movable.txt",
            },
            files={"file": ("movable.txt", b"move me", "text/plain")},
            headers=headers,
        )
        doc_id = resp.json()["succinctProperties"]["cmis:objectId"]

        # Move document
        resp = await async_client.post(
            f"/api/v1/cmis/browser/root/{doc_id}",
            data={
                "cmisaction": "move",
                "sourceFolderId": source_id,
                "targetFolderId": target_id,
            },
            headers=headers,
        )
        assert resp.status_code == 200

        # Verify document is in target folder
        resp = await async_client.get(
            f"/api/v1/cmis/browser/root/{target_id}",
            params={"cmisselector": "children"},
            headers=headers,
        )
        data = resp.json()
        doc_ids = [
            obj["succinctProperties"]["cmis:objectId"]
            for obj in data["objects"]
        ]
        assert doc_id in doc_ids
