"""Saved searches and smart folders REST API."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.common import EnvelopeResponse
from app.schemas.saved_search import (
    SavedSearchCreate,
    SavedSearchResponse,
    SavedSearchUpdate,
)
from app.services import saved_search_service

router = APIRouter(prefix="/saved-searches", tags=["saved-searches"])


@router.get("/", response_model=EnvelopeResponse[list[SavedSearchResponse]])
async def list_saved_searches(
    smart_folders_only: bool = Query(False, description="If true, return only smart folders"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List saved searches for the current user.

    Pass ?smart_folders_only=true to filter to smart folders only.
    """
    if smart_folders_only:
        items = await saved_search_service.list_smart_folders(db, current_user.id)
    else:
        items = await saved_search_service.list_saved_searches(db, current_user.id)

    return EnvelopeResponse(
        data=[SavedSearchResponse.model_validate(s) for s in items]
    )


@router.post(
    "/",
    response_model=EnvelopeResponse[SavedSearchResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_saved_search(
    body: SavedSearchCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new saved search or smart folder."""
    saved = await saved_search_service.create_saved_search(
        db, current_user.id, body
    )
    return EnvelopeResponse(data=SavedSearchResponse.model_validate(saved))


@router.put(
    "/{search_id}",
    response_model=EnvelopeResponse[SavedSearchResponse],
)
async def update_saved_search(
    search_id: uuid.UUID,
    body: SavedSearchUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a saved search by ID."""
    updated = await saved_search_service.update_saved_search(
        db, search_id, current_user.id, body
    )
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved search not found",
        )
    return EnvelopeResponse(data=SavedSearchResponse.model_validate(updated))


@router.delete("/{search_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved_search(
    search_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft-delete a saved search by ID."""
    deleted = await saved_search_service.delete_saved_search(
        db, search_id, current_user.id
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved search not found",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
