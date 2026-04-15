import uuid

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_admin
from app.models.user import User
from app.schemas.auth import (
    ServiceTokenCreate,
    ServiceTokenListItem,
    ServiceTokenResponse,
    TokenResponse,
)
from app.schemas.common import EnvelopeResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=EnvelopeResponse[TokenResponse])
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user and return JWT access token."""
    token = await auth_service.login(db, form_data.username, form_data.password)
    return EnvelopeResponse(
        data=TokenResponse(access_token=token),
    )


@router.post("/service-tokens", response_model=EnvelopeResponse[ServiceTokenResponse])
async def create_service_token(
    payload: ServiceTokenCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Create a service token for API/worker authentication (admin only)."""
    svc_token, raw_token = await auth_service.create_service_token(
        db, payload.name, payload.user_id
    )
    return EnvelopeResponse(
        data=ServiceTokenResponse(
            id=svc_token.id,
            name=svc_token.name,
            user_id=svc_token.user_id,
            token=raw_token,
            created_at=svc_token.created_at,
        ),
    )


@router.get("/service-tokens", response_model=EnvelopeResponse[list[ServiceTokenListItem]])
async def list_service_tokens(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """List all service tokens (admin only)."""
    tokens = await auth_service.list_service_tokens(db)
    return EnvelopeResponse(
        data=[ServiceTokenListItem.model_validate(t) for t in tokens],
    )


@router.delete("/service-tokens/{token_id}")
async def revoke_service_token(
    token_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Revoke a service token (admin only)."""
    await auth_service.revoke_service_token(db, token_id)
    return EnvelopeResponse(data={"message": "Service token revoked"})
