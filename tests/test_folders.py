"""Tests for Cabinet/Folder Hierarchy (FOLD-01 through FOLD-04).

Wave 0 stubs: all tests are marked skip and will be implemented in Plan 02.
They cover cabinet creation, subfolder creation, folder tree retrieval,
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
    """Helper: create a cabinet (root folder) via the API."""
    payload: dict = {"name": name}
    if description is not None:
        payload["description"] = description
    return await client.post(
        "/api/v1/folders/cabinets",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )


async def _create_subfolder(
    client: AsyncClient,
    token: str,
    parent_id: str,
    name: str = "Test Subfolder",
) -> dict:
    """Helper: create a subfolder under an existing folder via the API."""
    return await client.post(
        f"/api/v1/folders/{parent_id}/children",
        json={"name": name},
        headers={"Authorization": f"Bearer {token}"},
    )


async def _upload_doc(
    client: AsyncClient,
    token: str,
    title: str = "Test Doc",
) -> dict:
    """Helper: upload a document via the API."""
    files = {"file": ("test.pdf", b"test content", "application/pdf")}
    data: dict = {"title": title}
    return await client.post(
        "/api/v1/documents",
        files=files,
        data=data,
        headers={"Authorization": f"Bearer {token}"},
    )


# ── FOLD-01: Cabinet and Subfolder Creation ───────────────────────────────────


@pytest.mark.asyncio
async def test_create_cabinet(async_client: AsyncClient, admin_token: str) -> None:
    """FOLD-01: Admin can create a cabinet (root folder with is_cabinet=True)."""
    pytest.skip("Wave 0 stub")


@pytest.mark.asyncio
async def test_create_subfolder(async_client: AsyncClient, admin_token: str) -> None:
    """FOLD-01: Admin can create a subfolder under an existing cabinet or folder."""
    pytest.skip("Wave 0 stub")


@pytest.mark.asyncio
async def test_create_subfolder_regular_user(
    async_client: AsyncClient, regular_token: str
) -> None:
    """FOLD-01: Regular users can also create subfolders (no admin restriction)."""
    pytest.skip("Wave 0 stub")


# ── FOLD-02: Folder Tree Retrieval ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_folder_tree(async_client: AsyncClient, admin_token: str) -> None:
    """FOLD-02: GET /api/v1/folders/tree returns nested cabinet/folder hierarchy."""
    pytest.skip("Wave 0 stub")


@pytest.mark.asyncio
async def test_tree_excludes_deleted(
    async_client: AsyncClient, admin_token: str
) -> None:
    """FOLD-02: Soft-deleted folders are excluded from the tree response."""
    pytest.skip("Wave 0 stub")


# ── FOLD-03: Document Filing ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_file_document(async_client: AsyncClient, admin_token: str) -> None:
    """FOLD-03: A document can be filed into a folder."""
    pytest.skip("Wave 0 stub")


@pytest.mark.asyncio
async def test_multi_file_document(
    async_client: AsyncClient, admin_token: str
) -> None:
    """FOLD-03: A document can be filed into multiple folders simultaneously."""
    pytest.skip("Wave 0 stub")


@pytest.mark.asyncio
async def test_unfile_document(async_client: AsyncClient, admin_token: str) -> None:
    """FOLD-03: A document can be removed from a folder (unfile)."""
    pytest.skip("Wave 0 stub")


@pytest.mark.asyncio
async def test_document_response_includes_folder_ids(
    async_client: AsyncClient, admin_token: str
) -> None:
    """FOLD-03: Document detail/list responses include folder_ids for filed documents."""
    pytest.skip("Wave 0 stub")


@pytest.mark.asyncio
async def test_list_documents_by_folder(
    async_client: AsyncClient, admin_token: str
) -> None:
    """FOLD-03: GET /api/v1/folders/{id}/documents returns documents filed in folder."""
    pytest.skip("Wave 0 stub")


# ── FOLD-04: Move, Copy, Rename, Delete ──────────────────────────────────────


@pytest.mark.asyncio
async def test_move_folder(async_client: AsyncClient, admin_token: str) -> None:
    """FOLD-04: A folder (and its subtree) can be moved to a new parent."""
    pytest.skip("Wave 0 stub")


@pytest.mark.asyncio
async def test_move_circular_rejected(
    async_client: AsyncClient, admin_token: str
) -> None:
    """FOLD-04: Moving a folder into its own descendant raises 400."""
    pytest.skip("Wave 0 stub")


@pytest.mark.asyncio
async def test_move_self_rejected(
    async_client: AsyncClient, admin_token: str
) -> None:
    """FOLD-04: Moving a folder into itself raises 400."""
    pytest.skip("Wave 0 stub")


@pytest.mark.asyncio
async def test_rename_folder(async_client: AsyncClient, admin_token: str) -> None:
    """FOLD-04: A folder can be renamed without changing its position in the tree."""
    pytest.skip("Wave 0 stub")


@pytest.mark.asyncio
async def test_copy_folder(async_client: AsyncClient, admin_token: str) -> None:
    """FOLD-04: A folder subtree can be copied to another parent."""
    pytest.skip("Wave 0 stub")


@pytest.mark.asyncio
async def test_folder_detail_has_path(
    async_client: AsyncClient, admin_token: str
) -> None:
    """FOLD-04: GET /api/v1/folders/{id} response includes breadcrumb path from root."""
    pytest.skip("Wave 0 stub")


@pytest.mark.asyncio
async def test_delete_cascades_subtree(
    async_client: AsyncClient, admin_token: str
) -> None:
    """FOLD-04: Deleting a folder soft-deletes all descendant folders recursively."""
    pytest.skip("Wave 0 stub")


@pytest.mark.asyncio
async def test_delete_unfiles_documents(
    async_client: AsyncClient, admin_token: str
) -> None:
    """FOLD-04: Deleting a folder removes its document_folders rows for all descendants."""
    pytest.skip("Wave 0 stub")
