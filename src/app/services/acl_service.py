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


async def check_permission(
    db: AsyncSession,
    document_id: uuid.UUID,
    user_id: uuid.UUID,
    required_level: PermissionLevel,
) -> bool:
    """Check if a user has sufficient permission on a document.

    Checks both direct user ACL entries and group-based entries.
    If NO ACL entries exist for the document at all, returns True
    (backward compatibility: no ACL = open access).
    """
    # Check if any ACL entries exist for this document
    count_result = await db.execute(
        select(func.count()).select_from(DocumentACL).where(
            DocumentACL.document_id == document_id,
            DocumentACL.is_deleted == False,  # noqa: E712
        )
    )
    total_entries = count_result.scalar()
    if total_entries == 0:
        return True  # No ACL = open access (backward compat)

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
