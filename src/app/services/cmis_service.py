"""CMIS 1.1 Browser Binding service layer.

Provides property mapping between internal Document/Folder models and CMIS
standard property names, plus repository info and type definitions.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


# ── CMIS property name -> internal model field mapping ───────────────────────

# Reverse map: CMIS property -> internal field name (for create/update)
CMIS_TO_INTERNAL: dict[str, str] = {
    "cmis:name": "title",  # document title or folder name
    "cmis:contentStreamFileName": "filename",
    "cmis:contentStreamMimeType": "content_type",
    "cmis:description": "description",
}

# For folder create/update, cmis:name maps to "name" not "title"
CMIS_TO_INTERNAL_FOLDER: dict[str, str] = {
    "cmis:name": "name",
    "cmis:description": "description",
}


def _prop_def(
    prop_id: str,
    display_name: str,
    property_type: str = "string",
    updatability: str = "readwrite",
    required: bool = False,
) -> dict[str, Any]:
    """Build a CMIS propertyDefinition dict."""
    return {
        "id": prop_id,
        "localName": prop_id.split(":")[-1],
        "displayName": display_name,
        "queryName": prop_id,
        "propertyType": property_type,
        "cardinality": "single",
        "updatability": updatability,
        "required": required,
    }


# ── Repository info ──────────────────────────────────────────────────────────


def get_repository_info(root_folder_id: str) -> dict[str, Any]:
    """Return CMIS 1.1 repository info."""
    return {
        "repositoryId": "documentum-clone",
        "repositoryName": "Documentum Clone Repository",
        "repositoryDescription": "Documentum Workflow Clone ECM Repository",
        "vendorName": "Documentum Clone Project",
        "productName": "Documentum Clone",
        "productVersion": "1.4.0",
        "rootFolderId": root_folder_id,
        "cmisVersionSupported": "1.1",
        "capabilities": {
            "capabilityACL": "manage",
            "capabilityQuery": "metadataonly",
            "capabilityContentStreamUpdatability": "anytime",
            "capabilityChanges": "none",
            "capabilityRenditions": "none",
            "capabilityGetDescendants": True,
            "capabilityGetFolderTree": True,
            "capabilityMultifiling": True,
            "capabilityUnfiling": True,
            "capabilityVersionSpecificFiling": False,
            "capabilityPWCUpdatable": True,
        },
    }


# ── Type definitions ─────────────────────────────────────────────────────────

_DOCUMENT_PROPERTY_DEFS: dict[str, dict[str, Any]] = {
    "cmis:objectId": _prop_def("cmis:objectId", "Object ID", "id", "readonly"),
    "cmis:name": _prop_def("cmis:name", "Name", "string", "readwrite", required=True),
    "cmis:baseTypeId": _prop_def("cmis:baseTypeId", "Base Type ID", "id", "readonly"),
    "cmis:objectTypeId": _prop_def("cmis:objectTypeId", "Object Type ID", "id", "readonly"),
    "cmis:createdBy": _prop_def("cmis:createdBy", "Created By", "string", "readonly"),
    "cmis:creationDate": _prop_def("cmis:creationDate", "Creation Date", "datetime", "readonly"),
    "cmis:lastModificationDate": _prop_def("cmis:lastModificationDate", "Last Modified", "datetime", "readonly"),
    "cmis:contentStreamFileName": _prop_def("cmis:contentStreamFileName", "Filename", "string", "readonly"),
    "cmis:contentStreamMimeType": _prop_def("cmis:contentStreamMimeType", "MIME Type", "string", "readonly"),
    "cmis:contentStreamLength": _prop_def("cmis:contentStreamLength", "Content Length", "integer", "readonly"),
    "cmis:isVersionSeriesCheckedOut": _prop_def("cmis:isVersionSeriesCheckedOut", "Checked Out", "boolean", "readonly"),
    "cmis:versionSeriesCheckedOutBy": _prop_def("cmis:versionSeriesCheckedOutBy", "Checked Out By", "string", "readonly"),
    "cmis:versionLabel": _prop_def("cmis:versionLabel", "Version Label", "string", "readonly"),
}

_FOLDER_PROPERTY_DEFS: dict[str, dict[str, Any]] = {
    "cmis:objectId": _prop_def("cmis:objectId", "Object ID", "id", "readonly"),
    "cmis:name": _prop_def("cmis:name", "Name", "string", "readwrite", required=True),
    "cmis:baseTypeId": _prop_def("cmis:baseTypeId", "Base Type ID", "id", "readonly"),
    "cmis:objectTypeId": _prop_def("cmis:objectTypeId", "Object Type ID", "id", "readonly"),
    "cmis:createdBy": _prop_def("cmis:createdBy", "Created By", "string", "readonly"),
    "cmis:creationDate": _prop_def("cmis:creationDate", "Creation Date", "datetime", "readonly"),
    "cmis:lastModificationDate": _prop_def("cmis:lastModificationDate", "Last Modified", "datetime", "readonly"),
    "cmis:parentId": _prop_def("cmis:parentId", "Parent ID", "id", "readonly"),
}


def get_type_definition(type_id: str) -> dict[str, Any]:
    """Return CMIS type definition for cmis:document or cmis:folder."""
    if type_id == "cmis:document":
        return {
            "id": "cmis:document",
            "localName": "document",
            "displayName": "Document",
            "queryName": "cmis:document",
            "baseId": "cmis:document",
            "propertyDefinitions": _DOCUMENT_PROPERTY_DEFS,
        }
    elif type_id == "cmis:folder":
        return {
            "id": "cmis:folder",
            "localName": "folder",
            "displayName": "Folder",
            "queryName": "cmis:folder",
            "baseId": "cmis:folder",
            "propertyDefinitions": _FOLDER_PROPERTY_DEFS,
        }
    else:
        raise ValueError(f"Unknown CMIS type: {type_id}")


# ── Object conversion ────────────────────────────────────────────────────────


def to_cmis_document(doc: Any, version: Any | None = None) -> dict[str, Any]:
    """Convert a Document ORM object to CMIS succinctProperties dict."""
    created_at = doc.created_at
    updated_at = doc.updated_at

    props: dict[str, Any] = {
        "cmis:objectId": str(doc.id),
        "cmis:name": doc.title,
        "cmis:baseTypeId": "cmis:document",
        "cmis:objectTypeId": "cmis:document",
        "cmis:createdBy": doc.created_by,
        "cmis:creationDate": _format_datetime(created_at),
        "cmis:lastModificationDate": _format_datetime(updated_at),
        "cmis:contentStreamFileName": doc.filename,
        "cmis:contentStreamMimeType": doc.content_type,
        "cmis:isVersionSeriesCheckedOut": doc.locked_by is not None,
        "cmis:versionLabel": f"{doc.current_major_version}.{doc.current_minor_version}",
    }

    if doc.locked_by is not None:
        props["cmis:versionSeriesCheckedOutBy"] = str(doc.locked_by)

    if version is not None:
        props["cmis:contentStreamLength"] = version.content_size

    return props


def to_cmis_folder(folder: Any) -> dict[str, Any]:
    """Convert a Folder ORM object to CMIS succinctProperties dict."""
    return {
        "cmis:objectId": str(folder.id),
        "cmis:name": folder.name,
        "cmis:baseTypeId": "cmis:folder",
        "cmis:objectTypeId": "cmis:folder",
        "cmis:createdBy": folder.created_by,
        "cmis:creationDate": _format_datetime(folder.created_at),
        "cmis:lastModificationDate": _format_datetime(folder.updated_at),
        "cmis:parentId": str(folder.parent_id) if folder.parent_id else None,
    }


def to_cmis_object(obj: Any, is_folder: bool = False) -> dict[str, Any]:
    """Wrap an object in CMIS Browser Binding succinct response format."""
    if is_folder:
        props = to_cmis_folder(obj)
    else:
        props = to_cmis_document(obj)
    return {
        "succinctProperties": props,
        "propertiesExtension": {},
    }


def from_cmis_properties(cmis_props: dict[str, Any]) -> dict[str, Any]:
    """Reverse-map CMIS property names to internal field names for create/update.

    Unknown CMIS properties are silently ignored.
    """
    result: dict[str, Any] = {}
    for cmis_key, value in cmis_props.items():
        if cmis_key in CMIS_TO_INTERNAL:
            result[CMIS_TO_INTERNAL[cmis_key]] = value
    return result


def from_cmis_properties_folder(cmis_props: dict[str, Any]) -> dict[str, Any]:
    """Reverse-map CMIS property names to internal Folder field names."""
    result: dict[str, Any] = {}
    for cmis_key, value in cmis_props.items():
        if cmis_key in CMIS_TO_INTERNAL_FOLDER:
            result[CMIS_TO_INTERNAL_FOLDER[cmis_key]] = value
    return result


# ── Helpers ──────────────────────────────────────────────────────────────────


def _format_datetime(dt: datetime | None) -> str | None:
    """Format datetime as ISO 8601 for CMIS responses."""
    if dt is None:
        return None
    return dt.isoformat()
