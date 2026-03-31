"""Alias set CRUD endpoints."""
import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.alias import (
    AliasMappingCreate,
    AliasMappingResponse,
    AliasSetCreate,
    AliasSetDetailResponse,
    AliasSetResponse,
    AliasSetUpdate,
)
from app.schemas.common import EnvelopeResponse, PaginationMeta
from app.services import alias_service

router = APIRouter(prefix="/alias-sets", tags=["alias-sets"])


@router.post(
    "/",
    response_model=EnvelopeResponse[AliasSetDetailResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_alias_set(
    body: AliasSetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new alias set with optional initial mappings."""
    mappings_dicts = [m.model_dump() for m in body.mappings] if body.mappings else None
    alias_set = await alias_service.create_alias_set(
        db,
        name=body.name,
        description=body.description,
        mappings=mappings_dicts,
        user_id=str(current_user.id),
    )
    # Reload with mappings
    alias_set = await alias_service.get_alias_set(db, alias_set.id)
    return EnvelopeResponse(data=AliasSetDetailResponse.model_validate(alias_set))


@router.get(
    "/",
    response_model=EnvelopeResponse[list[AliasSetResponse]],
)
async def list_alias_sets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List alias sets with pagination."""
    skip = (page - 1) * page_size
    alias_sets, total = await alias_service.list_alias_sets(db, skip=skip, limit=page_size)
    return EnvelopeResponse(
        data=[AliasSetResponse.model_validate(s) for s in alias_sets],
        meta=PaginationMeta(
            page=page,
            page_size=page_size,
            total_count=total,
            total_pages=max(1, math.ceil(total / page_size)),
        ),
    )


@router.get(
    "/{alias_set_id}",
    response_model=EnvelopeResponse[AliasSetDetailResponse],
)
async def get_alias_set(
    alias_set_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get alias set detail with mappings."""
    try:
        alias_set = await alias_service.get_alias_set(db, alias_set_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return EnvelopeResponse(data=AliasSetDetailResponse.model_validate(alias_set))


@router.patch(
    "/{alias_set_id}",
    response_model=EnvelopeResponse[AliasSetResponse],
)
async def update_alias_set(
    alias_set_id: uuid.UUID,
    body: AliasSetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update alias set name/description."""
    try:
        alias_set = await alias_service.update_alias_set(
            db,
            alias_set_id,
            name=body.name,
            description=body.description,
            user_id=str(current_user.id),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return EnvelopeResponse(data=AliasSetResponse.model_validate(alias_set))


@router.delete(
    "/{alias_set_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_alias_set(
    alias_set_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft-delete an alias set."""
    try:
        await alias_service.delete_alias_set(db, alias_set_id, user_id=str(current_user.id))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/{alias_set_id}/mappings",
    response_model=EnvelopeResponse[AliasMappingResponse],
    status_code=status.HTTP_201_CREATED,
)
async def add_alias_mapping(
    alias_set_id: uuid.UUID,
    body: AliasMappingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a mapping to an alias set."""
    try:
        mapping = await alias_service.add_alias_mapping(
            db,
            alias_set_id,
            alias_name=body.alias_name,
            target_type=body.target_type,
            target_id=body.target_id,
            user_id=str(current_user.id),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return EnvelopeResponse(data=AliasMappingResponse.model_validate(mapping))


@router.delete(
    "/{alias_set_id}/mappings/{mapping_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_alias_mapping(
    alias_set_id: uuid.UUID,
    mapping_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a mapping from an alias set."""
    try:
        await alias_service.remove_alias_mapping(db, mapping_id, user_id=str(current_user.id))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
