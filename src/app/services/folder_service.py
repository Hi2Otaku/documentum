"""Service layer for Folder/Cabinet hierarchy: CRUD, tree, path, filing, move, copy, delete."""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import delete, func, literal_column, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.document import Document
from app.models.folder import Folder, document_folders


# ── Internal helpers ──────────────────────────────────────────────────────────


async def _fetch_folder_or_404(db: AsyncSession, folder_id: uuid.UUID) -> Folder:
    """Fetch a non-deleted folder by ID or raise 404."""
    result = await db.execute(
        select(Folder)
        .options(selectinload(Folder.parent))
        .where(Folder.id == folder_id, Folder.is_deleted == False)
    )
    folder = result.scalar_one_or_none()
    if folder is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found"
        )
    return folder


async def _get_folder_path(
    db: AsyncSession, folder_id: uuid.UUID
) -> list[dict]:
    """Return breadcrumb path from root to the given folder using a recursive CTE.

    Each element is {"id": str, "name": str}, ordered root-first.
    """
    # Anchor: the folder itself at depth 0
    folder_table = Folder.__table__
    anchor = (
        select(
            folder_table.c.id,
            folder_table.c.name,
            folder_table.c.parent_id,
            literal_column("0").label("depth"),
        )
        .where(
            folder_table.c.id == folder_id,
            folder_table.c.is_deleted == False,
        )
        .cte(name="ancestors", recursive=True)
    )

    # Recursive term: walk up to each parent
    parent_alias = anchor.alias("anc")
    recursive_term = select(
        folder_table.c.id,
        folder_table.c.name,
        folder_table.c.parent_id,
        (parent_alias.c.depth + 1).label("depth"),
    ).join(parent_alias, folder_table.c.id == parent_alias.c.parent_id)

    ancestors_cte = anchor.union_all(recursive_term)

    result = await db.execute(
        select(ancestors_cte.c.id, ancestors_cte.c.name).order_by(
            ancestors_cte.c.depth.desc()
        )
    )
    return [{"id": str(row.id), "name": row.name} for row in result.all()]


async def _is_descendant(
    db: AsyncSession, folder_id: uuid.UUID, candidate_id: uuid.UUID
) -> bool:
    """Return True if candidate_id is a descendant of folder_id."""
    folder_table = Folder.__table__

    # Anchor: direct children of folder_id
    anchor = (
        select(folder_table.c.id)
        .where(
            folder_table.c.parent_id == folder_id,
            folder_table.c.is_deleted == False,
        )
        .cte(name="descendants", recursive=True)
    )

    # Recursive term: children of already-found descendants
    descendants_alias = anchor.alias("desc")
    recursive_term = select(folder_table.c.id).join(
        descendants_alias, folder_table.c.parent_id == descendants_alias.c.id
    ).where(folder_table.c.is_deleted == False)

    descendants_cte = anchor.union_all(recursive_term)

    result = await db.execute(
        select(descendants_cte.c.id).where(descendants_cte.c.id == candidate_id)
    )
    return result.scalar_one_or_none() is not None


# ── Public API ────────────────────────────────────────────────────────────────


async def create_cabinet(
    db: AsyncSession,
    name: str,
    description: str | None,
    created_by: str,
) -> Folder:
    """Create a cabinet (root folder with is_cabinet=True)."""
    folder = Folder(
        name=name,
        description=description,
        is_cabinet=True,
        parent_id=None,
        created_by=created_by,
    )
    db.add(folder)
    await db.flush()
    await db.refresh(folder)
    return folder


async def create_folder(
    db: AsyncSession,
    parent_id: uuid.UUID,
    name: str,
    description: str | None,
    created_by: str,
) -> Folder:
    """Create a subfolder under an existing folder."""
    await _fetch_folder_or_404(db, parent_id)
    folder = Folder(
        name=name,
        description=description,
        is_cabinet=False,
        parent_id=parent_id,
        created_by=created_by,
    )
    db.add(folder)
    await db.flush()
    await db.refresh(folder)
    return folder


async def get_folder(db: AsyncSession, folder_id: uuid.UUID) -> dict:
    """Return folder detail dict with path breadcrumb and document count."""
    folder = await _fetch_folder_or_404(db, folder_id)

    path = await _get_folder_path(db, folder_id)

    count_result = await db.execute(
        select(func.count()).select_from(document_folders).where(
            document_folders.c.folder_id == folder_id
        )
    )
    document_count = count_result.scalar_one()

    return {
        "folder": folder,
        "path": path,
        "document_count": document_count,
    }


async def get_folder_tree(
    db: AsyncSession,
    user_id: uuid.UUID | None = None,
    is_superuser: bool = False,
) -> list[dict]:
    """Return the folder hierarchy as a nested tree of dicts.

    For superusers: returns all folders.
    For regular users: returns only folders where the user has ACL access
    (directly or via ancestor), plus folders with no ACL entries in the chain (open access).
    """
    # All non-deleted folders
    folders_result = await db.execute(
        select(Folder).where(Folder.is_deleted == False).order_by(Folder.name)  # noqa: E712
    )
    all_folders = folders_result.scalars().all()

    # Document counts per folder
    counts_result = await db.execute(
        select(
            document_folders.c.folder_id,
            func.count().label("cnt"),
        ).group_by(document_folders.c.folder_id)
    )
    counts_by_id: dict[uuid.UUID, int] = {
        row.folder_id: row.cnt for row in counts_result.all()
    }

    # ACL filtering for non-superusers
    visible_folder_ids: set[uuid.UUID] | None = None
    if user_id and not is_superuser:
        from app.models.acl import FolderACL
        from app.models.user import user_groups

        # Get user's group IDs
        group_result = await db.execute(
            select(user_groups.c.group_id).where(user_groups.c.user_id == user_id)
        )
        group_ids = [row[0] for row in group_result.fetchall()]

        # Find all folder IDs that have ANY ACL entry
        acl_folder_result = await db.execute(
            select(FolderACL.folder_id).where(
                FolderACL.is_deleted == False  # noqa: E712
            ).distinct()
        )
        folders_with_acl = {row[0] for row in acl_folder_result.all()}

        # Find folders where this user has access (direct user or group)
        user_acl_result = await db.execute(
            select(FolderACL.folder_id).where(
                FolderACL.principal_id == user_id,
                FolderACL.principal_type == "user",
                FolderACL.is_deleted == False,  # noqa: E712
            )
        )
        user_acl_folders = {row[0] for row in user_acl_result.all()}

        group_acl_folders: set[uuid.UUID] = set()
        if group_ids:
            group_acl_result = await db.execute(
                select(FolderACL.folder_id).where(
                    FolderACL.principal_id.in_(group_ids),
                    FolderACL.principal_type == "group",
                    FolderACL.is_deleted == False,  # noqa: E712
                )
            )
            group_acl_folders = {row[0] for row in group_acl_result.all()}

        accessible_acl_folders = user_acl_folders | group_acl_folders

        # Build set of visible folders:
        # - Folders with no ACL anywhere in their ancestor chain (open access)
        # - Folders where user has ACL access
        # - Ancestors of accessible folders (so the tree path is visible)
        all_folder_map = {f.id: f for f in all_folders}
        visible_folder_ids = set()

        for f in all_folders:
            # Check if this folder or any ancestor has ACL entries
            has_acl_in_chain = False
            user_has_access = False
            current = f
            while current:
                if current.id in folders_with_acl:
                    has_acl_in_chain = True
                if current.id in accessible_acl_folders:
                    user_has_access = True
                current = all_folder_map.get(current.parent_id) if current.parent_id else None

            if not has_acl_in_chain:
                # No ACL in chain → open access
                visible_folder_ids.add(f.id)
            elif user_has_access:
                # User has access → visible, plus add all ancestors for tree path
                visible_folder_ids.add(f.id)
                current = f
                while current and current.parent_id:
                    visible_folder_ids.add(current.parent_id)
                    current = all_folder_map.get(current.parent_id)

    # Build tree in Python
    by_id: dict[uuid.UUID, dict] = {}
    for f in all_folders:
        if visible_folder_ids is not None and f.id not in visible_folder_ids:
            continue
        by_id[f.id] = {
            "id": str(f.id),
            "name": f.name,
            "is_cabinet": f.is_cabinet,
            "parent_id": str(f.parent_id) if f.parent_id else None,
            "document_count": counts_by_id.get(f.id, 0),
            "children": [],
        }

    roots: list[dict] = []
    for fid, node in by_id.items():
        parent_id_str = node["parent_id"]
        if parent_id_str is not None:
            parent_uuid = uuid.UUID(parent_id_str)
            if parent_uuid in by_id:
                by_id[parent_uuid]["children"].append(node)
            else:
                roots.append(node)
        else:
            roots.append(node)

    return roots


async def rename_folder(
    db: AsyncSession, folder_id: uuid.UUID, name: str
) -> Folder:
    """Rename a folder."""
    folder = await _fetch_folder_or_404(db, folder_id)
    folder.name = name
    await db.flush()
    await db.refresh(folder)
    return folder


async def move_folder(
    db: AsyncSession, folder_id: uuid.UUID, new_parent_id: uuid.UUID
) -> Folder:
    """Move a folder under a new parent, with circular-reference guards."""
    if new_parent_id == folder_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot move folder into itself",
        )
    if await _is_descendant(db, folder_id, new_parent_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot move folder into its own subtree",
        )
    folder = await _fetch_folder_or_404(db, folder_id)
    await _fetch_folder_or_404(db, new_parent_id)

    folder.parent_id = new_parent_id
    folder.is_cabinet = False
    await db.flush()
    await db.refresh(folder)
    return folder


async def copy_folder(
    db: AsyncSession,
    folder_id: uuid.UUID,
    dest_parent_id: uuid.UUID | None,
    created_by: str,
) -> Folder:
    """Deep-copy a folder subtree to a destination parent.

    If dest_parent_id is None, copies adjacent to the source (same parent).
    Returns the root copy Folder.
    """
    source = await _fetch_folder_or_404(db, folder_id)
    effective_parent_id = dest_parent_id if dest_parent_id is not None else source.parent_id

    if effective_parent_id is not None:
        await _fetch_folder_or_404(db, effective_parent_id)

    # Collect all folders in the subtree (depth-first) via recursive CTE
    folder_table = Folder.__table__
    anchor = (
        select(folder_table.c.id, literal_column("0").label("depth"))
        .where(folder_table.c.id == folder_id, folder_table.c.is_deleted == False)
        .cte(name="subtree", recursive=True)
    )
    subtree_alias = anchor.alias("st")
    recursive_part = select(
        folder_table.c.id,
        (subtree_alias.c.depth + 1).label("depth"),
    ).join(subtree_alias, folder_table.c.parent_id == subtree_alias.c.id).where(
        folder_table.c.is_deleted == False
    )
    subtree_cte = anchor.union_all(recursive_part)

    subtree_result = await db.execute(
        select(subtree_cte.c.id, subtree_cte.c.depth).order_by(subtree_cte.c.depth)
    )
    subtree_rows = subtree_result.all()

    if not subtree_rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found"
        )

    # Load all source folders
    source_ids = [row.id for row in subtree_rows]
    sources_result = await db.execute(
        select(Folder).where(Folder.id.in_(source_ids))
    )
    sources_by_id: dict[uuid.UUID, Folder] = {
        f.id: f for f in sources_result.scalars().all()
    }

    # Create copies in depth order, maintaining an id_map
    id_map: dict[uuid.UUID, uuid.UUID] = {}
    root_copy: Folder | None = None

    for row in subtree_rows:
        src = sources_by_id[row.id]
        if src.id == folder_id:
            new_parent = effective_parent_id
        else:
            new_parent = id_map.get(src.parent_id)  # type: ignore[arg-type]

        copy = Folder(
            name=src.name,
            description=src.description,
            is_cabinet=False,
            parent_id=new_parent,
            created_by=created_by,
        )
        db.add(copy)
        await db.flush()
        await db.refresh(copy)
        id_map[src.id] = copy.id
        if src.id == folder_id:
            root_copy = copy

    # Copy document_folders rows
    now = datetime.now(timezone.utc)
    for src_id, new_id in id_map.items():
        df_result = await db.execute(
            select(document_folders).where(document_folders.c.folder_id == src_id)
        )
        for df_row in df_result.all():
            await db.execute(
                document_folders.insert().values(
                    document_id=df_row.document_id,
                    folder_id=new_id,
                    filed_at=now,
                    filed_by=created_by,
                )
            )

    await db.flush()
    assert root_copy is not None
    return root_copy


async def delete_folder(db: AsyncSession, folder_id: uuid.UUID) -> None:
    """Soft-delete a folder and all its descendants using a recursive CTE.

    Also removes all document_folders rows for the deleted folders.
    """
    folder_table = Folder.__table__

    # Recursive CTE: anchor = the target folder, recursive = its descendants
    anchor = (
        select(folder_table.c.id)
        .where(
            folder_table.c.id == folder_id,
            folder_table.c.is_deleted == False,
        )
        .cte(name="to_delete", recursive=True)
    )
    to_delete_alias = anchor.alias("td")
    recursive_part = select(folder_table.c.id).join(
        to_delete_alias, folder_table.c.parent_id == to_delete_alias.c.id
    ).where(folder_table.c.is_deleted == False)

    subtree_cte = anchor.union_all(recursive_part)

    id_result = await db.execute(select(subtree_cte.c.id))
    ids_to_delete = [row[0] for row in id_result.all()]

    if not ids_to_delete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found"
        )

    # Soft-delete all folders in the subtree
    await db.execute(
        update(Folder)
        .where(Folder.id.in_(ids_to_delete))
        .values(is_deleted=True)
    )

    # Remove document_folders rows for deleted folders
    await db.execute(
        delete(document_folders).where(
            document_folders.c.folder_id.in_(ids_to_delete)
        )
    )

    await db.flush()


async def file_document(
    db: AsyncSession,
    folder_id: uuid.UUID,
    document_id: uuid.UUID,
    filed_by: str,
) -> None:
    """File a document into a folder (creates a document_folders row)."""
    await _fetch_folder_or_404(db, folder_id)

    # Verify document exists and is not deleted
    doc_result = await db.execute(
        select(Document).where(
            Document.id == document_id, Document.is_deleted == False
        )
    )
    if doc_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    # Check it's not already filed in this folder
    existing = await db.execute(
        select(document_folders).where(
            document_folders.c.document_id == document_id,
            document_folders.c.folder_id == folder_id,
        )
    )
    if existing.first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document is already filed in this folder",
        )

    await db.execute(
        document_folders.insert().values(
            document_id=document_id,
            folder_id=folder_id,
            filed_at=datetime.now(timezone.utc),
            filed_by=filed_by,
        )
    )
    await db.flush()


async def unfile_document(
    db: AsyncSession, folder_id: uuid.UUID, document_id: uuid.UUID
) -> None:
    """Remove a document from a folder (deletes the document_folders row)."""
    result = await db.execute(
        delete(document_folders).where(
            document_folders.c.document_id == document_id,
            document_folders.c.folder_id == folder_id,
        )
    )
    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document is not filed in this folder",
        )
    await db.flush()


async def get_folder_documents(
    db: AsyncSession,
    folder_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
    user_id: uuid.UUID | None = None,
    is_superuser: bool = False,
) -> tuple[list[Document], int]:
    """Return paginated documents filed in a folder.

    When user_id is provided and is_superuser is False, filters documents
    by per-document ACL check (N+1 is acceptable with page_size cap of 20-50).
    """
    await _fetch_folder_or_404(db, folder_id)

    if user_id is not None and not is_superuser:
        from app.services.acl_service import check_permission
        from app.models.enums import PermissionLevel

        # Fetch all non-deleted documents in this folder (before pagination)
        all_docs_result = await db.execute(
            select(Document)
            .join(document_folders, Document.id == document_folders.c.document_id)
            .where(
                document_folders.c.folder_id == folder_id,
                Document.is_deleted == False,  # noqa: E712
            )
            .order_by(Document.created_at.desc())
        )
        all_docs = list(all_docs_result.scalars().all())

        # Filter by permission check per document
        visible_docs = []
        for doc in all_docs:
            has_access = await check_permission(
                db, doc.id, user_id, PermissionLevel.READ, is_superuser=False
            )
            if has_access:
                visible_docs.append(doc)

        # Apply pagination to the filtered list
        total = len(visible_docs)
        start = (page - 1) * page_size
        end = start + page_size
        return visible_docs[start:end], total

    # Superuser or unauthenticated: return all documents (original behavior)
    count_result = await db.execute(
        select(func.count())
        .select_from(document_folders)
        .where(document_folders.c.folder_id == folder_id)
    )
    total = count_result.scalar_one()

    docs_result = await db.execute(
        select(Document)
        .join(document_folders, Document.id == document_folders.c.document_id)
        .where(
            document_folders.c.folder_id == folder_id,
            Document.is_deleted == False,  # noqa: E712
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    documents = list(docs_result.scalars().all())
    return documents, total


async def get_document_folder_ids(
    db: AsyncSession, document_id: uuid.UUID
) -> list[str]:
    """Return the IDs of all non-deleted folders that contain a given document."""
    folder_table = Folder.__table__
    result = await db.execute(
        select(document_folders.c.folder_id)
        .join(
            folder_table,
            document_folders.c.folder_id == folder_table.c.id,
        )
        .where(
            document_folders.c.document_id == document_id,
            folder_table.c.is_deleted == False,
        )
    )
    return [str(row[0]) for row in result.all()]
