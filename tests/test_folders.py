"""Tests for Cabinet/Folder Hierarchy (FOLD-01 through FOLD-04).

Covers cabinet creation, subfolder creation, folder tree retrieval,
document filing/unfiling, move/copy/delete with recursive cascade.
"""

import pytest
from httpx import AsyncClient


# ── Helpers ──────────────────────────────────────────────────────────────────


async def _create_cabinet(
    client: AsyncClient,
    token: str,
    name: str = "Test Cabinet",
    description: str | None = None,
) -> dict:
    """Helper: create a cabinet (root folder) via the API. Returns response data dict."""
    payload: dict = {"name": name}
    if description is not None:
        payload["description"] = description
    resp = await client.post(
        "/api/v1/folders/",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    return resp.json()["data"]


async def _create_subfolder(
    client: AsyncClient,
    token: str,
    parent_id: str,
    name: str = "Test Subfolder",
) -> dict:
    """Helper: create a subfolder under an existing folder via the API. Returns response data dict."""
    resp = await client.post(
        f"/api/v1/folders/{parent_id}/children",
        json={"name": name},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    return resp.json()["data"]


async def _upload_doc(
    client: AsyncClient,
    token: str,
    title: str = "Test Doc",
) -> dict:
    """Helper: upload a document via the API. Returns response data dict."""
    files = {"file": ("test.pdf", b"test content", "application/pdf")}
    data: dict = {"title": title}
    resp = await client.post(
        "/api/v1/documents/",
        files=files,
        data=data,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    return resp.json()["data"]


async def _file_document(
    client: AsyncClient,
    token: str,
    folder_id: str,
    document_id: str,
) -> None:
    """Helper: file a document into a folder."""
    resp = await client.post(
        f"/api/v1/folders/{folder_id}/documents",
        json={"document_id": document_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"


# ── FOLD-01: Cabinet and Subfolder Creation ───────────────────────────────────


@pytest.mark.asyncio
async def test_create_cabinet(async_client: AsyncClient, admin_token: str) -> None:
    """FOLD-01: Admin can create a cabinet (root folder with is_cabinet=True)."""
    cabinet = await _create_cabinet(async_client, admin_token, name="Finance Cabinet")
    assert cabinet["is_cabinet"] is True
    assert cabinet["parent_id"] is None
    assert cabinet["name"] == "Finance Cabinet"
    assert "id" in cabinet


@pytest.mark.asyncio
async def test_create_subfolder(async_client: AsyncClient, admin_token: str) -> None:
    """FOLD-01: Admin can create a subfolder under an existing cabinet or folder."""
    cabinet = await _create_cabinet(async_client, admin_token, name="Root Cabinet")
    subfolder = await _create_subfolder(async_client, admin_token, cabinet["id"], "Sub Folder")
    assert subfolder["is_cabinet"] is False
    assert subfolder["parent_id"] == cabinet["id"]
    assert subfolder["name"] == "Sub Folder"


@pytest.mark.asyncio
async def test_create_subfolder_regular_user(
    async_client: AsyncClient, admin_token: str, regular_token: str
) -> None:
    """FOLD-01: Regular users can also create subfolders (no admin restriction)."""
    # Admin creates the cabinet
    cabinet = await _create_cabinet(async_client, admin_token, name="Shared Cabinet")
    # Regular user creates a subfolder under it
    subfolder = await _create_subfolder(async_client, regular_token, cabinet["id"], "User Subfolder")
    assert subfolder["is_cabinet"] is False
    assert subfolder["parent_id"] == cabinet["id"]


# ── FOLD-02: Folder Tree Retrieval ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_folder_tree(async_client: AsyncClient, admin_token: str) -> None:
    """FOLD-02: GET /api/v1/folders/tree returns nested cabinet/folder hierarchy."""
    cabinet = await _create_cabinet(async_client, admin_token, name="Tree Cabinet")
    subfolder = await _create_subfolder(async_client, admin_token, cabinet["id"], "Tree Sub")

    resp = await async_client.get(
        "/api/v1/folders/tree",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    tree = resp.json()["data"]
    assert isinstance(tree, list)

    # Find the cabinet in the tree
    cabinet_nodes = [n for n in tree if n["id"] == cabinet["id"]]
    assert len(cabinet_nodes) == 1, f"Cabinet not found in tree: {tree}"
    cabinet_node = cabinet_nodes[0]

    # Check children
    child_ids = [c["id"] for c in cabinet_node["children"]]
    assert subfolder["id"] in child_ids, f"Subfolder not in cabinet children: {cabinet_node}"


@pytest.mark.asyncio
async def test_tree_excludes_deleted(
    async_client: AsyncClient, admin_token: str
) -> None:
    """FOLD-02: Soft-deleted folders are excluded from the tree response."""
    cabinet = await _create_cabinet(async_client, admin_token, name="To Delete Cabinet")

    # Delete the cabinet
    resp = await async_client.delete(
        f"/api/v1/folders/{cabinet['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200

    # Tree should not contain the deleted cabinet
    resp = await async_client.get(
        "/api/v1/folders/tree",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    tree = resp.json()["data"]
    all_ids = {n["id"] for n in tree}
    assert cabinet["id"] not in all_ids


# ── FOLD-03: Document Filing ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_file_document(async_client: AsyncClient, admin_token: str) -> None:
    """FOLD-03: A document can be filed into a folder."""
    cabinet = await _create_cabinet(async_client, admin_token, name="Filing Cabinet")
    doc = await _upload_doc(async_client, admin_token, "Filed Doc")
    await _file_document(async_client, admin_token, cabinet["id"], doc["id"])

    # GET /{folder_id}/documents should contain the document
    resp = await async_client.get(
        f"/api/v1/folders/{cabinet['id']}/documents",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    doc_ids = [d["id"] for d in data]
    assert doc["id"] in doc_ids


@pytest.mark.asyncio
async def test_multi_file_document(
    async_client: AsyncClient, admin_token: str
) -> None:
    """FOLD-03: A document can be filed into multiple folders simultaneously."""
    cabinet_a = await _create_cabinet(async_client, admin_token, name="Cabinet A")
    cabinet_b = await _create_cabinet(async_client, admin_token, name="Cabinet B")
    doc = await _upload_doc(async_client, admin_token, "Multi-Filed Doc")

    await _file_document(async_client, admin_token, cabinet_a["id"], doc["id"])
    await _file_document(async_client, admin_token, cabinet_b["id"], doc["id"])

    # GET /documents/{id} should return folder_ids with both folders
    resp = await async_client.get(
        f"/api/v1/documents/{doc['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "folder_ids" in data
    assert cabinet_a["id"] in data["folder_ids"]
    assert cabinet_b["id"] in data["folder_ids"]


@pytest.mark.asyncio
async def test_unfile_document(async_client: AsyncClient, admin_token: str) -> None:
    """FOLD-03: A document can be removed from a folder (unfile)."""
    cabinet = await _create_cabinet(async_client, admin_token, name="Unfile Cabinet")
    doc = await _upload_doc(async_client, admin_token, "Unfile Doc")
    await _file_document(async_client, admin_token, cabinet["id"], doc["id"])

    # Unfile the document
    resp = await async_client.delete(
        f"/api/v1/folders/{cabinet['id']}/documents/{doc['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200

    # The folder should now have no documents
    resp = await async_client.get(
        f"/api/v1/folders/{cabinet['id']}/documents",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 0


@pytest.mark.asyncio
async def test_document_response_includes_folder_ids(
    async_client: AsyncClient, admin_token: str
) -> None:
    """FOLD-03: Document detail/list responses include folder_ids for filed documents."""
    cabinet = await _create_cabinet(async_client, admin_token, name="FolderIds Cabinet")
    doc = await _upload_doc(async_client, admin_token, "FolderIds Doc")
    await _file_document(async_client, admin_token, cabinet["id"], doc["id"])

    # GET /documents/{id} should include folder_ids
    resp = await async_client.get(
        f"/api/v1/documents/{doc['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "folder_ids" in data
    assert cabinet["id"] in data["folder_ids"]


@pytest.mark.asyncio
async def test_list_documents_by_folder(
    async_client: AsyncClient, admin_token: str
) -> None:
    """FOLD-03: GET /api/v1/documents/?folder_id={id} returns documents filed in folder."""
    cabinet = await _create_cabinet(async_client, admin_token, name="Filter Cabinet")
    doc = await _upload_doc(async_client, admin_token, "Filtered Doc")
    await _file_document(async_client, admin_token, cabinet["id"], doc["id"])

    # Also create an unfiled document to verify filtering works
    _other_doc = await _upload_doc(async_client, admin_token, "Unfiled Doc")

    # GET /documents/?folder_id={id}
    resp = await async_client.get(
        f"/api/v1/documents/?folder_id={cabinet['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    doc_ids = [d["id"] for d in data]
    assert doc["id"] in doc_ids
    assert _other_doc["id"] not in doc_ids


# ── FOLD-04: Move, Copy, Rename, Delete ──────────────────────────────────────


@pytest.mark.asyncio
async def test_move_folder(async_client: AsyncClient, admin_token: str) -> None:
    """FOLD-04: A folder (and its subtree) can be moved to a new parent."""
    cabinet_a = await _create_cabinet(async_client, admin_token, name="Move Source Cabinet")
    cabinet_b = await _create_cabinet(async_client, admin_token, name="Move Target Cabinet")
    subfolder = await _create_subfolder(async_client, admin_token, cabinet_a["id"], "Movable Sub")

    # Move subfolder from A to B
    resp = await async_client.put(
        f"/api/v1/folders/{subfolder['id']}",
        json={"parent_id": cabinet_b["id"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["parent_id"] == cabinet_b["id"]


@pytest.mark.asyncio
async def test_move_circular_rejected(
    async_client: AsyncClient, admin_token: str
) -> None:
    """FOLD-04: Moving a folder into its own descendant raises 400."""
    cabinet = await _create_cabinet(async_client, admin_token, name="Circular Cabinet")
    subfolder = await _create_subfolder(async_client, admin_token, cabinet["id"], "Circular Sub")

    # Try to move the cabinet into its own subfolder
    resp = await async_client.put(
        f"/api/v1/folders/{cabinet['id']}",
        json={"parent_id": subfolder["id"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_move_self_rejected(
    async_client: AsyncClient, admin_token: str
) -> None:
    """FOLD-04: Moving a folder into itself raises 400."""
    cabinet = await _create_cabinet(async_client, admin_token, name="Self Move Cabinet")

    # Try to move the cabinet into itself
    resp = await async_client.put(
        f"/api/v1/folders/{cabinet['id']}",
        json={"parent_id": cabinet["id"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_rename_folder(async_client: AsyncClient, admin_token: str) -> None:
    """FOLD-04: A folder can be renamed without changing its position in the tree."""
    cabinet = await _create_cabinet(async_client, admin_token, name="Old Cabinet Name")

    resp = await async_client.put(
        f"/api/v1/folders/{cabinet['id']}",
        json={"name": "New Cabinet Name"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["name"] == "New Cabinet Name"
    assert data["id"] == cabinet["id"]
    # Parent stays the same (still a cabinet with no parent)
    assert data["parent_id"] is None


@pytest.mark.asyncio
async def test_copy_folder(async_client: AsyncClient, admin_token: str) -> None:
    """FOLD-04: A folder subtree can be copied to another parent."""
    cabinet_src = await _create_cabinet(async_client, admin_token, name="Copy Source")
    cabinet_dest = await _create_cabinet(async_client, admin_token, name="Copy Dest")
    doc = await _upload_doc(async_client, admin_token, "Copy Doc")
    await _file_document(async_client, admin_token, cabinet_src["id"], doc["id"])

    # Copy cabinet_src into cabinet_dest
    resp = await async_client.post(
        f"/api/v1/folders/{cabinet_src['id']}/copy",
        json={"destination_parent_id": cabinet_dest["id"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    copy_data = resp.json()["data"]
    copy_id = copy_data["id"]
    assert copy_id != cabinet_src["id"]
    assert copy_data["parent_id"] == cabinet_dest["id"]

    # The copy should also have the document filed
    resp = await async_client.get(
        f"/api/v1/folders/{copy_id}/documents",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    copy_docs = resp.json()["data"]
    doc_ids = [d["id"] for d in copy_docs]
    assert doc["id"] in doc_ids


@pytest.mark.asyncio
async def test_folder_detail_has_path(
    async_client: AsyncClient, admin_token: str
) -> None:
    """FOLD-04: GET /api/v1/folders/{id} response includes breadcrumb path from root."""
    cabinet = await _create_cabinet(async_client, admin_token, name="Root Path Cabinet")
    sub1 = await _create_subfolder(async_client, admin_token, cabinet["id"], "Level 1")
    sub2 = await _create_subfolder(async_client, admin_token, sub1["id"], "Level 2")

    # GET sub-subfolder detail
    resp = await async_client.get(
        f"/api/v1/folders/{sub2['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    path = data["path"]
    # Path should include root cabinet, sub1, and sub2
    assert len(path) == 3
    path_ids = [p["id"] for p in path]
    assert cabinet["id"] in path_ids
    assert sub1["id"] in path_ids
    assert sub2["id"] in path_ids


@pytest.mark.asyncio
async def test_delete_cascades_subtree(
    async_client: AsyncClient, admin_token: str
) -> None:
    """FOLD-04: Deleting a folder soft-deletes all descendant folders recursively."""
    cabinet = await _create_cabinet(async_client, admin_token, name="Cascade Cabinet")
    subfolder = await _create_subfolder(async_client, admin_token, cabinet["id"], "Cascade Sub")

    # Delete the cabinet
    resp = await async_client.delete(
        f"/api/v1/folders/{cabinet['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200

    # Both cabinet and subfolder should return 404
    resp = await async_client.get(
        f"/api/v1/folders/{cabinet['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404

    resp = await async_client.get(
        f"/api/v1/folders/{subfolder['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_unfiles_documents(
    async_client: AsyncClient, admin_token: str
) -> None:
    """FOLD-04: Deleting a folder removes its document_folders rows; doc still exists."""
    cabinet = await _create_cabinet(async_client, admin_token, name="Unfile On Delete Cabinet")
    doc = await _upload_doc(async_client, admin_token, "Unfile On Delete Doc")
    await _file_document(async_client, admin_token, cabinet["id"], doc["id"])

    # Delete the cabinet
    resp = await async_client.delete(
        f"/api/v1/folders/{cabinet['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200

    # Document should still exist but folder_ids should be empty
    resp = await async_client.get(
        f"/api/v1/documents/{doc['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["folder_ids"] == []
