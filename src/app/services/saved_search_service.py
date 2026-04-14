"""CRUD operations for saved searches and smart folders."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.saved_search import SavedSearch
from app.schemas.saved_search import SavedSearchCreate, SavedSearchUpdate


async def list_saved_searches(
    db: AsyncSession, user_id: uuid.UUID
) -> list[SavedSearch]:
    """Return all non-deleted saved searches for a user, ordered by display_order then created_at."""
    result = await db.execute(
        select(SavedSearch)
        .where(
            SavedSearch.user_id == user_id,
            SavedSearch.is_deleted == False,  # noqa: E712
        )
        .order_by(SavedSearch.display_order.asc(), SavedSearch.created_at.desc())
    )
    return list(result.scalars().all())


async def list_smart_folders(
    db: AsyncSession, user_id: uuid.UUID
) -> list[SavedSearch]:
    """Return only smart-folder saved searches for a user."""
    result = await db.execute(
        select(SavedSearch)
        .where(
            SavedSearch.user_id == user_id,
            SavedSearch.is_smart_folder == True,  # noqa: E712
            SavedSearch.is_deleted == False,  # noqa: E712
        )
        .order_by(SavedSearch.display_order.asc(), SavedSearch.created_at.desc())
    )
    return list(result.scalars().all())


async def get_saved_search(
    db: AsyncSession, search_id: uuid.UUID, user_id: uuid.UUID
) -> SavedSearch | None:
    """Get a single saved search by id, scoped to the user."""
    result = await db.execute(
        select(SavedSearch).where(
            SavedSearch.id == search_id,
            SavedSearch.user_id == user_id,
            SavedSearch.is_deleted == False,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def create_saved_search(
    db: AsyncSession, user_id: uuid.UUID, data: SavedSearchCreate
) -> SavedSearch:
    """Create a new saved search for the given user."""
    saved_search = SavedSearch(
        name=data.name,
        query=data.query,
        filters=data.filters,
        is_smart_folder=data.is_smart_folder,
        display_order=data.display_order,
        user_id=user_id,
    )
    db.add(saved_search)
    await db.commit()
    await db.refresh(saved_search)
    return saved_search


async def update_saved_search(
    db: AsyncSession,
    search_id: uuid.UUID,
    user_id: uuid.UUID,
    data: SavedSearchUpdate,
) -> SavedSearch | None:
    """Partially update a saved search. Returns None if not found."""
    existing = await get_saved_search(db, search_id, user_id)
    if existing is None:
        return None

    update_data = data.model_dump(exclude_unset=True)
    if update_data:
        update_data["updated_at"] = datetime.now(timezone.utc)
        await db.execute(
            update(SavedSearch)
            .where(SavedSearch.id == search_id)
            .values(**update_data)
        )
        await db.commit()
        await db.refresh(existing)
    return existing


async def delete_saved_search(
    db: AsyncSession, search_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    """Soft-delete a saved search. Returns True if found and deleted."""
    existing = await get_saved_search(db, search_id, user_id)
    if existing is None:
        return False

    await db.execute(
        update(SavedSearch)
        .where(SavedSearch.id == search_id)
        .values(is_deleted=True, updated_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return True
