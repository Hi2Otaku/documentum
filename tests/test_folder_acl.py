"""Tests for folder ACL inheritance (FOLD-05)."""
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.acl import FolderACL
from app.models.document import Document
from app.models.enums import PermissionLevel
from app.models.folder import Folder, document_folders
from app.models.user import Group, User, user_groups
from app.services.acl_service import (
    check_permission,
    create_folder_acl_entry,
    get_folder_acls,
    remove_folder_acl_entry,
)
from app.services.folder_service import get_folder_documents


# ── Helpers ─────────────────────────────────────────────────────────────────


async def _make_folder(db: AsyncSession, name: str, is_cabinet: bool = True, parent_id=None, created_by: str = "test") -> Folder:
    folder = Folder(
        name=name,
        is_cabinet=is_cabinet,
        parent_id=parent_id,
        created_by=created_by,
    )
    db.add(folder)
    await db.flush()
    await db.refresh(folder)
    return folder


async def _make_document(db: AsyncSession, title: str = "Test Doc", created_by: str = "test") -> Document:
    doc = Document(
        title=title,
        filename="test.pdf",
        content_type="application/pdf",
        created_by=created_by,
        current_major_version=1,
        current_minor_version=0,
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)
    return doc


async def _file_document(db: AsyncSession, doc_id: uuid.UUID, folder_id: uuid.UUID, filed_by: str = "test") -> None:
    await db.execute(
        document_folders.insert().values(
            document_id=doc_id,
            folder_id=folder_id,
            filed_at=datetime.now(timezone.utc),
            filed_by=filed_by,
        )
    )
    await db.flush()


async def _grant_folder_acl(
    db: AsyncSession,
    folder_id: uuid.UUID,
    principal_id: uuid.UUID,
    principal_type: str = "user",
    permission_level: PermissionLevel = PermissionLevel.READ,
    created_by: str = "test",
) -> FolderACL:
    acl = FolderACL(
        folder_id=folder_id,
        principal_id=principal_id,
        principal_type=principal_type,
        permission_level=permission_level.value,
        created_by=created_by,
    )
    db.add(acl)
    await db.flush()
    await db.refresh(acl)
    return acl


# ── Tests ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_folder_acl_model(db_session: AsyncSession, admin_user: User):
    """FolderACL model can be created with correct columns."""
    folder = await _make_folder(db_session, "Test Cabinet", created_by=str(admin_user.id))
    acl = FolderACL(
        folder_id=folder.id,
        principal_id=admin_user.id,
        principal_type="user",
        permission_level=PermissionLevel.READ.value,
        created_by=str(admin_user.id),
    )
    db_session.add(acl)
    await db_session.flush()
    await db_session.refresh(acl)

    assert acl.id is not None
    assert acl.folder_id == folder.id
    assert acl.principal_id == admin_user.id
    assert acl.principal_type == "user"
    assert acl.permission_level == PermissionLevel.READ.value


@pytest.mark.asyncio
async def test_folder_read_grants_document_access(db_session: AsyncSession, regular_user: User, admin_user: User):
    """User with folder READ ACL can access documents in that folder."""
    folder = await _make_folder(db_session, "Cabinet", created_by=str(admin_user.id))
    doc = await _make_document(db_session, created_by=str(admin_user.id))
    await _file_document(db_session, doc.id, folder.id)
    await _grant_folder_acl(db_session, folder.id, regular_user.id)

    result = await check_permission(db_session, doc.id, regular_user.id, PermissionLevel.READ)
    assert result is True


@pytest.mark.asyncio
async def test_no_folder_permission_hides_documents(db_session: AsyncSession, regular_user: User, admin_user: User):
    """User without folder ACL cannot access documents in ACL-restricted folder."""
    folder = await _make_folder(db_session, "Restricted Cabinet", created_by=str(admin_user.id))
    doc = await _make_document(db_session, created_by=str(admin_user.id))
    await _file_document(db_session, doc.id, folder.id)

    # Grant ACL to admin, not to regular_user
    await _grant_folder_acl(db_session, folder.id, admin_user.id)

    result = await check_permission(db_session, doc.id, regular_user.id, PermissionLevel.READ)
    assert result is False


@pytest.mark.asyncio
async def test_direct_acl_overrides_folder_acl(db_session: AsyncSession, regular_user: User, admin_user: User):
    """Document with direct ACL ignores folder ACL entirely."""
    folder = await _make_folder(db_session, "Cabinet", created_by=str(admin_user.id))
    doc = await _make_document(db_session, created_by=str(admin_user.id))
    await _file_document(db_session, doc.id, folder.id)

    # Folder ACL grants access only to admin, NOT to regular_user
    await _grant_folder_acl(db_session, folder.id, admin_user.id)

    # Direct document ACL grants regular_user READ
    from app.models.acl import DocumentACL
    doc_acl = DocumentACL(
        document_id=doc.id,
        principal_id=regular_user.id,
        principal_type="user",
        permission_level=PermissionLevel.READ.value,
        created_by=str(admin_user.id),
    )
    db_session.add(doc_acl)
    await db_session.flush()

    # Direct ACL grants access (overrides folder ACL path entirely)
    result = await check_permission(db_session, doc.id, regular_user.id, PermissionLevel.READ)
    assert result is True


@pytest.mark.asyncio
async def test_no_folder_acl_means_open_access(db_session: AsyncSession, regular_user: User, admin_user: User):
    """Folder with no ACL entries means open access (backward compat)."""
    folder = await _make_folder(db_session, "Open Cabinet", created_by=str(admin_user.id))
    doc = await _make_document(db_session, created_by=str(admin_user.id))
    await _file_document(db_session, doc.id, folder.id)

    # No folder ACL entries at all
    result = await check_permission(db_session, doc.id, regular_user.id, PermissionLevel.READ)
    assert result is True


@pytest.mark.asyncio
async def test_multi_folder_or_logic(db_session: AsyncSession, regular_user: User, admin_user: User):
    """Document in multiple folders: access via ANY folder chain grants access."""
    folder1 = await _make_folder(db_session, "Restricted", created_by=str(admin_user.id))
    folder2 = await _make_folder(db_session, "Accessible", created_by=str(admin_user.id))
    doc = await _make_document(db_session, created_by=str(admin_user.id))
    await _file_document(db_session, doc.id, folder1.id)
    await _file_document(db_session, doc.id, folder2.id)

    # folder1 has ACL for admin only (restricted for regular_user)
    await _grant_folder_acl(db_session, folder1.id, admin_user.id)
    # folder2 has ACL for regular_user (accessible)
    await _grant_folder_acl(db_session, folder2.id, regular_user.id)

    # Should return True because access via folder2 grants access
    result = await check_permission(db_session, doc.id, regular_user.id, PermissionLevel.READ)
    assert result is True


@pytest.mark.asyncio
async def test_superuser_bypasses_folder_acl(db_session: AsyncSession, admin_user: User, regular_user: User):
    """Superuser access returns True regardless of folder ACL."""
    folder = await _make_folder(db_session, "Restricted Cabinet", created_by=str(regular_user.id))
    doc = await _make_document(db_session, created_by=str(regular_user.id))
    await _file_document(db_session, doc.id, folder.id)

    # Folder ACL restricts to regular_user only
    await _grant_folder_acl(db_session, folder.id, regular_user.id)

    # Superuser bypass
    result = await check_permission(db_session, doc.id, admin_user.id, PermissionLevel.READ, is_superuser=True)
    assert result is True


@pytest.mark.asyncio
async def test_nested_folder_inheritance(db_session: AsyncSession, regular_user: User, admin_user: User):
    """ACL on cabinet propagates to documents in nested subfolders."""
    # Cabinet -> subfolder -> doc
    cabinet = await _make_folder(db_session, "Cabinet", is_cabinet=True, created_by=str(admin_user.id))
    subfolder = await _make_folder(db_session, "Subfolder", is_cabinet=False, parent_id=cabinet.id, created_by=str(admin_user.id))
    doc = await _make_document(db_session, created_by=str(admin_user.id))
    await _file_document(db_session, doc.id, subfolder.id)

    # ACL is on cabinet (grandparent), doc is in subfolder
    await _grant_folder_acl(db_session, cabinet.id, regular_user.id)

    result = await check_permission(db_session, doc.id, regular_user.id, PermissionLevel.READ)
    assert result is True


@pytest.mark.asyncio
async def test_group_folder_acl(db_session: AsyncSession, regular_user: User, admin_user: User):
    """Group-based folder ACL grants access to group members."""
    folder = await _make_folder(db_session, "Group Cabinet", created_by=str(admin_user.id))
    doc = await _make_document(db_session, created_by=str(admin_user.id))
    await _file_document(db_session, doc.id, folder.id)

    # Create a group and add regular_user to it
    group = Group(name="test_group", created_by=str(admin_user.id))
    db_session.add(group)
    await db_session.flush()
    await db_session.execute(user_groups.insert().values(user_id=regular_user.id, group_id=group.id))
    await db_session.flush()

    # Grant folder ACL to the group
    await _grant_folder_acl(db_session, folder.id, group.id, principal_type="group")

    result = await check_permission(db_session, doc.id, regular_user.id, PermissionLevel.READ)
    assert result is True


@pytest.mark.asyncio
async def test_folder_documents_filtered_by_acl(db_session: AsyncSession, regular_user: User, admin_user: User):
    """get_folder_documents filters inaccessible docs for non-superusers."""
    folder = await _make_folder(db_session, "Mixed Cabinet", created_by=str(admin_user.id))

    # doc1: accessible (regular_user has folder ACL)
    doc1 = await _make_document(db_session, "Accessible Doc", created_by=str(admin_user.id))
    await _file_document(db_session, doc1.id, folder.id)

    # doc2: inaccessible (folder has ACL for admin only, regular_user has no access)
    doc2 = await _make_document(db_session, "Hidden Doc", created_by=str(admin_user.id))
    await _file_document(db_session, doc2.id, folder.id)

    # Grant folder ACL to regular_user (both docs in same folder, both accessible)
    # To test filtering, create a second folder with ACL only for admin
    folder2 = await _make_folder(db_session, "Restricted Cabinet", created_by=str(admin_user.id))
    doc3 = await _make_document(db_session, "Restricted Doc", created_by=str(admin_user.id))
    await _file_document(db_session, doc3.id, folder2.id)
    await _grant_folder_acl(db_session, folder2.id, admin_user.id)  # only admin can access folder2

    # Grant regular_user access to folder (not folder2)
    await _grant_folder_acl(db_session, folder.id, regular_user.id)

    # get_folder_documents on folder: regular_user should see doc1 and doc2 (both in accessible folder)
    docs, total = await get_folder_documents(db_session, folder.id, user_id=regular_user.id, is_superuser=False)
    doc_ids = {d.id for d in docs}
    assert doc1.id in doc_ids
    assert doc2.id in doc_ids
    assert total == 2

    # get_folder_documents on folder2: regular_user should NOT see doc3 (no access to folder2)
    docs2, total2 = await get_folder_documents(db_session, folder2.id, user_id=regular_user.id, is_superuser=False)
    assert total2 == 0
    assert len(docs2) == 0


@pytest.mark.asyncio
async def test_folder_acl_crud(db_session: AsyncSession, regular_user: User, admin_user: User):
    """create_folder_acl_entry, get_folder_acls, remove_folder_acl_entry work correctly."""
    folder = await _make_folder(db_session, "CRUD Cabinet", created_by=str(admin_user.id))

    # Create
    entry = await create_folder_acl_entry(
        db_session,
        folder_id=folder.id,
        principal_id=regular_user.id,
        principal_type="user",
        permission_level=PermissionLevel.READ,
        user_id=str(admin_user.id),
    )
    assert entry.id is not None
    assert entry.folder_id == folder.id
    assert entry.principal_id == regular_user.id

    # Idempotent duplicate returns existing
    entry2 = await create_folder_acl_entry(
        db_session,
        folder_id=folder.id,
        principal_id=regular_user.id,
        principal_type="user",
        permission_level=PermissionLevel.READ,
        user_id=str(admin_user.id),
    )
    assert entry2.id == entry.id

    # Get list
    acls = await get_folder_acls(db_session, folder.id)
    assert len(acls) == 1
    assert acls[0].id == entry.id

    # Remove
    removed = await remove_folder_acl_entry(db_session, folder.id, entry.id, user_id=str(admin_user.id))
    assert removed is True

    # After removal, list is empty
    acls_after = await get_folder_acls(db_session, folder.id)
    assert len(acls_after) == 0

    # Remove non-existent returns False
    removed_again = await remove_folder_acl_entry(db_session, folder.id, entry.id)
    assert removed_again is False


@pytest.mark.asyncio
async def test_access_source_field():
    """Placeholder for access_source field test (implemented in Plan 02)."""
    pass
