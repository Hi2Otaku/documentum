"""Alias set CRUD operations and resolve-at-start logic."""
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.workflow import AliasMapping, AliasSet
from app.services.audit_service import create_audit_record


async def create_alias_set(
    db: AsyncSession,
    *,
    name: str,
    description: str | None = None,
    mappings: list[dict] | None = None,
    user_id: str | None = None,
) -> AliasSet:
    """Create an alias set with optional initial mappings."""
    alias_set = AliasSet(
        name=name,
        description=description,
        created_by=user_id,
    )
    db.add(alias_set)
    await db.flush()

    if mappings:
        for m in mappings:
            mapping = AliasMapping(
                alias_set_id=alias_set.id,
                alias_name=m["alias_name"],
                target_type=m["target_type"],
                target_id=m["target_id"],
                created_by=user_id,
            )
            db.add(mapping)

    await db.flush()

    await create_audit_record(
        db,
        entity_type="alias_set",
        entity_id=str(alias_set.id),
        action="alias_set_created",
        user_id=user_id,
        after_state={"name": name, "description": description},
    )

    return alias_set


async def get_alias_set(
    db: AsyncSession,
    alias_set_id: uuid.UUID,
) -> AliasSet:
    """Load an alias set with its non-deleted mappings. Raises ValueError if not found or deleted."""
    result = await db.execute(
        select(AliasSet)
        .options(
            selectinload(AliasSet.mappings.and_(AliasMapping.is_deleted == False))  # noqa: E712
        )
        .where(AliasSet.id == alias_set_id, AliasSet.is_deleted == False)  # noqa: E712
    )
    alias_set = result.scalar_one_or_none()
    if alias_set is None:
        raise ValueError(f"Alias set {alias_set_id} not found")
    return alias_set


async def list_alias_sets(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[AliasSet], int]:
    """Paginated list of non-deleted alias sets."""
    count_result = await db.execute(
        select(func.count()).select_from(AliasSet).where(AliasSet.is_deleted == False)  # noqa: E712
    )
    total = count_result.scalar_one()

    result = await db.execute(
        select(AliasSet)
        .where(AliasSet.is_deleted == False)  # noqa: E712
        .order_by(AliasSet.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    alias_sets = list(result.scalars().all())
    return alias_sets, total


async def update_alias_set(
    db: AsyncSession,
    alias_set_id: uuid.UUID,
    *,
    name: str | None = None,
    description: str | None = None,
    user_id: str | None = None,
) -> AliasSet:
    """Update alias set name/description."""
    alias_set = await get_alias_set(db, alias_set_id)
    before = {"name": alias_set.name, "description": alias_set.description}

    if name is not None:
        alias_set.name = name
    if description is not None:
        alias_set.description = description

    await db.flush()

    await create_audit_record(
        db,
        entity_type="alias_set",
        entity_id=str(alias_set.id),
        action="alias_set_updated",
        user_id=user_id,
        before_state=before,
        after_state={"name": alias_set.name, "description": alias_set.description},
    )

    return alias_set


async def delete_alias_set(
    db: AsyncSession,
    alias_set_id: uuid.UUID,
    *,
    user_id: str | None = None,
) -> None:
    """Soft-delete an alias set."""
    alias_set = await get_alias_set(db, alias_set_id)
    alias_set.is_deleted = True
    await db.flush()

    await create_audit_record(
        db,
        entity_type="alias_set",
        entity_id=str(alias_set.id),
        action="alias_set_deleted",
        user_id=user_id,
    )


async def add_alias_mapping(
    db: AsyncSession,
    alias_set_id: uuid.UUID,
    *,
    alias_name: str,
    target_type: str,
    target_id: uuid.UUID,
    user_id: str | None = None,
) -> AliasMapping:
    """Add a mapping to an alias set."""
    # Verify set exists
    await get_alias_set(db, alias_set_id)

    mapping = AliasMapping(
        alias_set_id=alias_set_id,
        alias_name=alias_name,
        target_type=target_type,
        target_id=target_id,
        created_by=user_id,
    )
    db.add(mapping)
    await db.flush()

    await create_audit_record(
        db,
        entity_type="alias_mapping",
        entity_id=str(mapping.id),
        action="alias_mapping_created",
        user_id=user_id,
        after_state={
            "alias_set_id": str(alias_set_id),
            "alias_name": alias_name,
            "target_type": target_type,
            "target_id": str(target_id),
        },
    )

    return mapping


async def remove_alias_mapping(
    db: AsyncSession,
    mapping_id: uuid.UUID,
    *,
    user_id: str | None = None,
) -> None:
    """Soft-delete an alias mapping."""
    result = await db.execute(
        select(AliasMapping).where(
            AliasMapping.id == mapping_id,
            AliasMapping.is_deleted == False,  # noqa: E712
        )
    )
    mapping = result.scalar_one_or_none()
    if mapping is None:
        raise ValueError(f"Alias mapping {mapping_id} not found")

    mapping.is_deleted = True
    await db.flush()

    await create_audit_record(
        db,
        entity_type="alias_mapping",
        entity_id=str(mapping.id),
        action="alias_mapping_deleted",
        user_id=user_id,
    )


async def resolve_alias_snapshot(
    db: AsyncSession,
    alias_set_id: uuid.UUID,
) -> dict[str, str]:
    """Resolve all mappings in an alias set to a {alias_name: target_id} dict.

    Used at workflow start to snapshot alias mappings onto the workflow instance.
    """
    alias_set = await get_alias_set(db, alias_set_id)
    snapshot: dict[str, str] = {}
    for mapping in alias_set.mappings:
        if not mapping.is_deleted:
            snapshot[mapping.alias_name] = str(mapping.target_id)
    return snapshot
