"""Tests for CMIS 1.1 Browser Binding service layer and endpoints."""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.services import cmis_service


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
