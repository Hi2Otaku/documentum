"""ACL (Access Control List) service.

Provides CRUD operations for document-level permissions, permission hierarchy
checking with group resolution, and convenience functions for owner ACL creation.
"""
import logging
import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.acl import DocumentACL
from app.models.enums import PermissionLevel
from app.services.audit_service import create_audit_record

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Permission hierarchy: ADMIN > DELETE > WRITE > READ
# ---------------------------------------------------------------------------

PERMISSION_HIERARCHY: dict[PermissionLevel, int] = {
    PermissionLevel.READ: 1,
    PermissionLevel.WRITE: 2,
    PermissionLevel.DELETE: 3,
    PermissionLevel.ADMIN: 4,
}


def has_sufficient_permission(granted: PermissionLevel, required: PermissionLevel) -> bool:
    """Check if granted permission level meets or exceeds the required level."""
    return PERMISSION_HIERARCHY[granted] >= PERMISSION_HIERARCHY[required]


async def create_acl_entry(
    db: AsyncSession,
    document_id: uuid.UUID,
    principal_id: uuid.UUID,
    principal_type: str,
    permission_level: PermissionLevel,
    user_id: str | None = None,
) -> DocumentACL:
    """Create an ACL entry, or return existing if duplicate.

    Uses merge-like logic: checks if an entry with the same
    (document_id, principal_id, principal_type, permission_level) exists.
    """
    result = await db.execute(
        select(DocumentACL).where(
            DocumentACL.document_id == document_id,
            DocumentACL.principal_id == principal_id,
            DocumentACL.principal_type == principal_type,
            DocumentACL.permission_level == permission_level.value,
            DocumentACL.is_deleted == False,  # noqa: E712
        )
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        return existing

    entry = DocumentACL(
        document_id=document_id,
        principal_id=principal_id,
        principal_type=principal_type,
        permission_level=permission_level.value,
        created_by=user_id,
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)

    await create_audit_record(
        db,
        entity_type="document_acl",
        entity_id=str(document_id),
        action="acl_granted",
        user_id=user_id,
        after_state={
            "principal_id": str(principal_id),
            "principal_type": principal_type,
            "permission_level": permission_level.value,
        },
    )

    return entry


async def remove_acl_entry(
    db: AsyncSession,
    document_id: uuid.UUID,
    principal_id: uuid.UUID | None,
    principal_type: str | None,
    permission_level: PermissionLevel,
    user_id: str | None = None,
) -> int:
    """Remove matching ACL entries for a document.

    If principal_id is None, removes all entries matching the permission_level
    for the document (bulk removal for lifecycle rules).
    Returns count of deleted entries.
    """
    stmt = select(DocumentACL).where(
        DocumentACL.document_id == document_id,
        DocumentACL.permission_level == permission_level.value,
        DocumentACL.is_deleted == False,  # noqa: E712
    )
    if principal_id is not None:
        stmt = stmt.where(DocumentACL.principal_id == principal_id)
    if principal_type is not None:
        stmt = stmt.where(DocumentACL.principal_type == principal_type)

    result = await db.execute(stmt)
    entries = result.scalars().all()
    count = 0

    for entry in entries:
        await db.delete(entry)
        await create_audit_record(
            db,
            entity_type="document_acl",
            entity_id=str(document_id),
            action="acl_revoked",
            user_id=user_id,
            before_state={
                "principal_id": str(entry.principal_id),
                "principal_type": entry.principal_type,
                "permission_level": entry.permission_level,
            },
        )
        count += 1

    return count


async def _get_ancestor_folder_ids(
    db: AsyncSession,
    folder_ids: list[uuid.UUID],
) -> list[uuid.UUID]:
    """Return all ancestor folder IDs (including the input folder_ids themselves)
    by walking the parent_id chain via recursive CTE.

    Used by check_permission() for folder ACL inheritance and by
    get_access_source() for determining access source.
    """
    if not folder_ids:
        return []

    from app.models.folder import Folder
    folder_table = Folder.__table__

    anchor = (
        select(
            folder_table.c.id,
            folder_table.c.parent_id,
        )
        .where(
            folder_table.c.id.in_(folder_ids),
            folder_table.c.is_deleted == False,  # noqa: E712
        )
        .cte(name="folder_ancestors", recursive=True)
    )
    anc_alias = anchor.alias("anc")
    recursive_term = select(
        folder_table.c.id,
        folder_table.c.parent_id,
    ).join(
        anc_alias, folder_table.c.id == anc_alias.c.parent_id
    )
    ancestors_cte = anchor.union_all(recursive_term)

    result = await db.execute(select(ancestors_cte.c.id))
    return [row[0] for row in result.all()]


async def check_permission(
    db: AsyncSession,
    document_id: uuid.UUID,
    user_id: uuid.UUID,
    required_level: PermissionLevel,
    is_superuser: bool = False,
) -> bool:
    """Check if a user has sufficient permission on a document.

    Priority order:
    1. Direct user/group ACL on the document
    2. Folder ACL inheritance (walks ancestor chain)
    3. Workflow participant fallback (READ only)
    4. Open access (no ACL entries at all → backward compat)
    """
    if is_superuser:
        return True

    from app.models.folder import document_folders
    from app.models.acl import FolderACL
    from app.models.user import user_groups

    # --- 1. Check direct document ACL entries for this user ---
    result = await db.execute(
        select(DocumentACL).where(
            DocumentACL.document_id == document_id,
            DocumentACL.principal_id == user_id,
            DocumentACL.principal_type == "user",
            DocumentACL.is_deleted == False,  # noqa: E712
        )
    )
    for entry in result.scalars().all():
        if has_sufficient_permission(PermissionLevel(entry.permission_level), required_level):
            return True

    # Check group-based document ACL entries
    group_result = await db.execute(
        select(user_groups.c.group_id).where(user_groups.c.user_id == user_id)
    )
    group_ids = [row[0] for row in group_result.fetchall()]

    if group_ids:
        group_acl_result = await db.execute(
            select(DocumentACL).where(
                DocumentACL.document_id == document_id,
                DocumentACL.principal_type == "group",
                DocumentACL.principal_id.in_(group_ids),
                DocumentACL.is_deleted == False,  # noqa: E712
            )
        )
        for entry in group_acl_result.scalars().all():
            if has_sufficient_permission(PermissionLevel(entry.permission_level), required_level):
                return True

    # --- 2. Folder ACL inheritance ---
    folder_result = await db.execute(
        select(document_folders.c.folder_id).where(
            document_folders.c.document_id == document_id
        )
    )
    doc_folder_ids = [row[0] for row in folder_result.all()]

    if doc_folder_ids:
        all_ancestor_ids = await _get_ancestor_folder_ids(db, doc_folder_ids)

        # Check user entries on ancestor folders
        user_facl_result = await db.execute(
            select(FolderACL).where(
                FolderACL.folder_id.in_(all_ancestor_ids),
                FolderACL.principal_id == user_id,
                FolderACL.principal_type == "user",
                FolderACL.is_deleted == False,  # noqa: E712
            )
        )
        for entry in user_facl_result.scalars().all():
            if has_sufficient_permission(PermissionLevel(entry.permission_level), required_level):
                return True

        # Check group entries on ancestor folders
        if group_ids:
            group_facl_result = await db.execute(
                select(FolderACL).where(
                    FolderACL.folder_id.in_(all_ancestor_ids),
                    FolderACL.principal_type == "group",
                    FolderACL.principal_id.in_(group_ids),
                    FolderACL.is_deleted == False,  # noqa: E712
                )
            )
            for entry in group_facl_result.scalars().all():
                if has_sufficient_permission(PermissionLevel(entry.permission_level), required_level):
                    return True

    # --- 3. Workflow participant fallback (READ only) ---
    if required_level == PermissionLevel.READ:
        from app.models.workflow import WorkItem, WorkflowPackage, ActivityInstance
        from app.models.enums import WorkItemState
        participant_result = await db.execute(
            select(func.count()).select_from(WorkItem).join(
                ActivityInstance, WorkItem.activity_instance_id == ActivityInstance.id
            ).join(
                WorkflowPackage,
                WorkflowPackage.workflow_instance_id == ActivityInstance.workflow_instance_id,
            ).where(
                WorkflowPackage.document_id == document_id,
                WorkItem.performer_id == user_id,
                WorkItem.state.in_([WorkItemState.AVAILABLE, WorkItemState.ACQUIRED]),
            )
        )
        if participant_result.scalar() > 0:
            return True

    # --- 4. Open access fallback ---
    # If NO ACL entries exist anywhere (no direct doc ACL, no folder ACL), allow access
    # for backward compatibility (no ACL = open access).
    count_result = await db.execute(
        select(func.count()).select_from(DocumentACL).where(
            DocumentACL.document_id == document_id,
            DocumentACL.is_deleted == False,  # noqa: E712
        )
    )
    has_direct_acl = count_result.scalar() > 0

    has_folder_acl = False
    if doc_folder_ids:
        from sqlalchemy import func as sa_func
        facl_count = await db.execute(
            select(sa_func.count()).select_from(FolderACL).where(
                FolderACL.folder_id.in_(all_ancestor_ids),
                FolderACL.is_deleted == False,  # noqa: E712
            )
        )
        has_folder_acl = facl_count.scalar() > 0

    if not has_direct_acl and not has_folder_acl:
        return True  # No ACL anywhere → open access

    return False


async def get_document_acls(
    db: AsyncSession,
    document_id: uuid.UUID,
) -> list[DocumentACL]:
    """Return all non-deleted ACL entries for a document."""
    result = await db.execute(
        select(DocumentACL).where(
            DocumentACL.document_id == document_id,
            DocumentACL.is_deleted == False,  # noqa: E712
        )
    )
    return list(result.scalars().all())


async def create_owner_acl(
    db: AsyncSession,
    document_id: uuid.UUID,
    user_id: uuid.UUID,
) -> DocumentACL:
    """Create ADMIN-level ACL for the document creator.

    Convenience function called from document upload to grant
    the creator full access to their document.
    """
    return await create_acl_entry(
        db,
        document_id=document_id,
        principal_id=user_id,
        principal_type="user",
        permission_level=PermissionLevel.ADMIN,
        user_id=str(user_id),
    )


# ---------------------------------------------------------------------------
# Folder ACL CRUD functions
# ---------------------------------------------------------------------------


async def create_folder_acl_entry(
    db: AsyncSession,
    folder_id: uuid.UUID,
    principal_id: uuid.UUID,
    principal_type: str,
    permission_level: PermissionLevel,
    user_id: str | None = None,
):
    """Create a folder ACL entry, or return existing if duplicate."""
    from app.models.acl import FolderACL
    result = await db.execute(
        select(FolderACL).where(
            FolderACL.folder_id == folder_id,
            FolderACL.principal_id == principal_id,
            FolderACL.principal_type == principal_type,
            FolderACL.permission_level == permission_level.value,
            FolderACL.is_deleted == False,  # noqa: E712
        )
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        return existing

    entry = FolderACL(
        folder_id=folder_id,
        principal_id=principal_id,
        principal_type=principal_type,
        permission_level=permission_level.value,
        created_by=user_id,
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)

    await create_audit_record(
        db, entity_type="folder_acl", entity_id=str(folder_id),
        action="acl_granted", user_id=user_id,
        after_state={"principal_id": str(principal_id), "principal_type": principal_type, "permission_level": permission_level.value},
    )
    return entry


async def get_folder_acls(db: AsyncSession, folder_id: uuid.UUID) -> list:
    """Return all non-deleted ACL entries for a folder."""
    from app.models.acl import FolderACL
    result = await db.execute(
        select(FolderACL).where(
            FolderACL.folder_id == folder_id,
            FolderACL.is_deleted == False,  # noqa: E712
        )
    )
    return list(result.scalars().all())


async def remove_folder_acl_entry(
    db: AsyncSession,
    folder_id: uuid.UUID,
    acl_id: uuid.UUID,
    user_id: str | None = None,
) -> bool:
    """Remove a specific folder ACL entry by id. Returns True if found and deleted."""
    from app.models.acl import FolderACL
    result = await db.execute(
        select(FolderACL).where(
            FolderACL.id == acl_id,
            FolderACL.folder_id == folder_id,
            FolderACL.is_deleted == False,  # noqa: E712
        )
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        return False
    await db.delete(entry)
    await create_audit_record(
        db, entity_type="folder_acl", entity_id=str(folder_id),
        action="acl_revoked", user_id=user_id,
        before_state={"principal_id": str(entry.principal_id), "principal_type": entry.principal_type, "permission_level": entry.permission_level},
    )
    return True


async def get_access_source(
    db: AsyncSession,
    document_id: uuid.UUID,
    user_id: uuid.UUID,
    is_superuser: bool = False,
) -> dict:
    """Determine how a user gained access to a document.

    Returns {"access_source": "direct"|"folder_inherited"|"open", "access_source_folder_name": str|None}

    Uses _get_ancestor_folder_ids() shared helper for CTE ancestor walk
    (same helper used by check_permission).
    """
    if is_superuser:
        return {"access_source": "direct", "access_source_folder_name": None}

    # Check if this user has a direct ACL entry on the document
    from app.models.folder import document_folders, Folder
    from app.models.acl import FolderACL
    from app.models.user import user_groups

    user_direct = await db.execute(
        select(func.count()).select_from(DocumentACL).where(
            DocumentACL.document_id == document_id,
            DocumentACL.principal_id == user_id,
            DocumentACL.principal_type == "user",
            DocumentACL.is_deleted == False,  # noqa: E712
        )
    )
    if user_direct.scalar() > 0:
        return {"access_source": "direct", "access_source_folder_name": None}

    # Check group-based direct ACL
    group_result = await db.execute(
        select(user_groups.c.group_id).where(user_groups.c.user_id == user_id)
    )
    group_ids = [row[0] for row in group_result.fetchall()]
    if group_ids:
        group_direct = await db.execute(
            select(func.count()).select_from(DocumentACL).where(
                DocumentACL.document_id == document_id,
                DocumentACL.principal_type == "group",
                DocumentACL.principal_id.in_(group_ids),
                DocumentACL.is_deleted == False,  # noqa: E712
            )
        )
        if group_direct.scalar() > 0:
            return {"access_source": "direct", "access_source_folder_name": None}

    # Check folder ACL inheritance
    folder_result = await db.execute(
        select(document_folders.c.folder_id).where(
            document_folders.c.document_id == document_id
        )
    )
    doc_folder_ids = [row[0] for row in folder_result.all()]

    if doc_folder_ids:
        all_ancestor_ids = await _get_ancestor_folder_ids(db, doc_folder_ids)

        # Check user entries on ancestor folders
        user_acl_result = await db.execute(
            select(FolderACL.folder_id).where(
                FolderACL.folder_id.in_(all_ancestor_ids),
                FolderACL.principal_id == user_id,
                FolderACL.principal_type == "user",
                FolderACL.is_deleted == False,  # noqa: E712
            ).limit(1)
        )
        user_acl_folder = user_acl_result.scalar_one_or_none()
        if user_acl_folder:
            folder_name_result = await db.execute(
                select(Folder.name).where(Folder.id == user_acl_folder)
            )
            folder_name = folder_name_result.scalar_one_or_none()
            return {"access_source": "folder_inherited", "access_source_folder_name": folder_name}

        # Check group entries on ancestor folders
        if group_ids:
            group_acl_result = await db.execute(
                select(FolderACL.folder_id).where(
                    FolderACL.folder_id.in_(all_ancestor_ids),
                    FolderACL.principal_type == "group",
                    FolderACL.principal_id.in_(group_ids),
                    FolderACL.is_deleted == False,  # noqa: E712
                ).limit(1)
            )
            group_acl_folder = group_acl_result.scalar_one_or_none()
            if group_acl_folder:
                folder_name_result = await db.execute(
                    select(Folder.name).where(Folder.id == group_acl_folder)
                )
                folder_name = folder_name_result.scalar_one_or_none()
                return {"access_source": "folder_inherited", "access_source_folder_name": folder_name}

    return {"access_source": "open", "access_source_folder_name": None}


async def check_folder_permission(
    db: AsyncSession,
    folder_id: uuid.UUID,
    user_id: uuid.UUID,
    required_level: PermissionLevel,
    is_superuser: bool = False,
) -> bool:
    """Check if user has sufficient permission on a folder via FolderACL (for ACL management gating)."""
    if is_superuser:
        return True
    from app.models.acl import FolderACL
    from app.models.user import user_groups

    # Check direct user entries
    result = await db.execute(
        select(FolderACL).where(
            FolderACL.folder_id == folder_id,
            FolderACL.principal_id == user_id,
            FolderACL.principal_type == "user",
            FolderACL.is_deleted == False,  # noqa: E712
        )
    )
    for entry in result.scalars().all():
        if has_sufficient_permission(PermissionLevel(entry.permission_level), required_level):
            return True

    # Check group entries
    group_result = await db.execute(select(user_groups.c.group_id).where(user_groups.c.user_id == user_id))
    group_ids = [row[0] for row in group_result.fetchall()]
    if group_ids:
        group_acl_result = await db.execute(
            select(FolderACL).where(
                FolderACL.folder_id == folder_id,
                FolderACL.principal_type == "group",
                FolderACL.principal_id.in_(group_ids),
                FolderACL.is_deleted == False,  # noqa: E712
            )
        )
        for entry in group_acl_result.scalars().all():
            if has_sufficient_permission(PermissionLevel(entry.permission_level), required_level):
                return True

    return False
