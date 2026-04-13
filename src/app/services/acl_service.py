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

    Checks both direct user ACL entries and group-based entries.
    If NO ACL entries exist for the document at all, checks folder ACL inheritance.
    If no folder ACL entries exist either, returns True (backward compat: no ACL = open access).
    """
    if is_superuser:
        return True

    # Check if any ACL entries exist for this document
    count_result = await db.execute(
        select(func.count()).select_from(DocumentACL).where(
            DocumentACL.document_id == document_id,
            DocumentACL.is_deleted == False,  # noqa: E712
        )
    )
    total_entries = count_result.scalar()
    if total_entries == 0:
        # No direct ACL entries — check folder ACL inheritance
        from app.models.folder import document_folders
        from app.models.acl import FolderACL

        # Get all folders this document is filed in
        folder_result = await db.execute(
            select(document_folders.c.folder_id).where(
                document_folders.c.document_id == document_id
            )
        )
        doc_folder_ids = [row[0] for row in folder_result.all()]

        if not doc_folder_ids:
            return True  # Not filed in any folder, no direct ACL -> open access

        # Use shared helper to get all ancestor folder IDs
        all_ancestor_ids = await _get_ancestor_folder_ids(db, doc_folder_ids)

        # Check if ANY FolderACL entries exist on any ancestor folder
        from sqlalchemy import func as sa_func
        acl_count_result = await db.execute(
            select(sa_func.count()).select_from(FolderACL).where(
                FolderACL.folder_id.in_(all_ancestor_ids),
                FolderACL.is_deleted == False,  # noqa: E712
            )
        )
        total_folder_acl_entries = acl_count_result.scalar()

        if total_folder_acl_entries == 0:
            return True  # No folder ACL entries anywhere in chain -> open access (backward compat)

        # Folder ACL entries exist — check user access
        # Check direct user entries
        user_acl_result = await db.execute(
            select(FolderACL).where(
                FolderACL.folder_id.in_(all_ancestor_ids),
                FolderACL.principal_id == user_id,
                FolderACL.principal_type == "user",
                FolderACL.is_deleted == False,  # noqa: E712
            )
        )
        for entry in user_acl_result.scalars().all():
            if has_sufficient_permission(PermissionLevel(entry.permission_level), required_level):
                return True

        # Check group entries
        from app.models.user import user_groups as ug_table
        group_result = await db.execute(select(ug_table.c.group_id).where(ug_table.c.user_id == user_id))
        group_ids = [row[0] for row in group_result.fetchall()]

        if group_ids:
            group_acl_result = await db.execute(
                select(FolderACL).where(
                    FolderACL.folder_id.in_(all_ancestor_ids),
                    FolderACL.principal_type == "group",
                    FolderACL.principal_id.in_(group_ids),
                    FolderACL.is_deleted == False,  # noqa: E712
                )
            )
            for entry in group_acl_result.scalars().all():
                if has_sufficient_permission(PermissionLevel(entry.permission_level), required_level):
                    return True

        return False  # Folder ACL entries exist but user has no access

    # Check direct user ACL entries
    result = await db.execute(
        select(DocumentACL).where(
            DocumentACL.document_id == document_id,
            DocumentACL.principal_id == user_id,
            DocumentACL.principal_type == "user",
            DocumentACL.is_deleted == False,  # noqa: E712
        )
    )
    user_entries = result.scalars().all()

    for entry in user_entries:
        granted = PermissionLevel(entry.permission_level)
        if has_sufficient_permission(granted, required_level):
            return True

    # Check group-based ACL entries
    # Lazy import to avoid circular dependency
    from app.models.user import user_groups
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
        group_entries = group_acl_result.scalars().all()

        for entry in group_entries:
            granted = PermissionLevel(entry.permission_level)
            if has_sufficient_permission(granted, required_level):
                return True

    # Workflow participant fallback: only if user has an ACTIVE work item
    # (available or acquired) on a workflow with this document attached
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
