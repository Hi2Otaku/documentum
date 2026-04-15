"""Identity provider management and SSO login/callback endpoints."""

import uuid

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_active_admin
from app.models.user import User
from app.schemas.common import EnvelopeResponse
from app.schemas.identity import (
    IdentityProviderCreate,
    IdentityProviderResponse,
    IdentityProviderUpdate,
    SSOCallbackResponse,
)
from app.services import identity_service
from app.services.identity_service import mask_config

router = APIRouter(prefix="/identity", tags=["identity"])


# ---------------------------------------------------------------------------
# Provider CRUD (admin only)
# ---------------------------------------------------------------------------


@router.post("/providers", response_model=EnvelopeResponse[IdentityProviderResponse])
async def create_provider(
    payload: IdentityProviderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Create an identity provider configuration."""
    provider = await identity_service.create_provider(
        db,
        name=payload.name,
        provider_type=payload.provider_type,
        config=payload.config,
        is_enabled=payload.is_enabled,
    )
    return EnvelopeResponse(
        data=IdentityProviderResponse(
            id=provider.id,
            name=provider.name,
            provider_type=provider.provider_type,
            config=mask_config(provider.config),
            is_enabled=provider.is_enabled,
            created_at=provider.created_at,
        )
    )


@router.get("/providers", response_model=EnvelopeResponse[list[IdentityProviderResponse]])
async def list_providers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """List all identity providers."""
    providers = await identity_service.list_providers(db)
    return EnvelopeResponse(
        data=[
            IdentityProviderResponse(
                id=p.id,
                name=p.name,
                provider_type=p.provider_type,
                config=mask_config(p.config),
                is_enabled=p.is_enabled,
                created_at=p.created_at,
            )
            for p in providers
        ]
    )


@router.get("/providers/public", response_model=EnvelopeResponse[list[dict]])
async def list_enabled_providers(
    db: AsyncSession = Depends(get_db),
):
    """List enabled identity providers (public -- for login page SSO buttons).

    Returns minimal info: id, name, provider_type. No config or sensitive data.
    """
    providers = await identity_service.list_providers(db)
    enabled = [
        {"id": str(p.id), "name": p.name, "provider_type": p.provider_type}
        for p in providers
        if p.is_enabled
    ]
    return EnvelopeResponse(data=enabled)


@router.get("/providers/{provider_id}", response_model=EnvelopeResponse[IdentityProviderResponse])
async def get_provider(
    provider_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Get a single identity provider (sensitive config fields masked)."""
    provider = await identity_service.get_provider(db, provider_id)
    return EnvelopeResponse(
        data=IdentityProviderResponse(
            id=provider.id,
            name=provider.name,
            provider_type=provider.provider_type,
            config=mask_config(provider.config),
            is_enabled=provider.is_enabled,
            created_at=provider.created_at,
        )
    )


@router.put("/providers/{provider_id}", response_model=EnvelopeResponse[IdentityProviderResponse])
async def update_provider(
    provider_id: uuid.UUID,
    payload: IdentityProviderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Update an identity provider configuration."""
    update_data = payload.model_dump(exclude_none=True)
    provider = await identity_service.update_provider(db, provider_id, **update_data)
    return EnvelopeResponse(
        data=IdentityProviderResponse(
            id=provider.id,
            name=provider.name,
            provider_type=provider.provider_type,
            config=mask_config(provider.config),
            is_enabled=provider.is_enabled,
            created_at=provider.created_at,
        )
    )


@router.delete("/providers/{provider_id}")
async def delete_provider(
    provider_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Soft-delete an identity provider."""
    await identity_service.delete_provider(db, provider_id)
    return EnvelopeResponse(data={"message": "Identity provider deleted"})


# ---------------------------------------------------------------------------
# LDAP-specific (admin only)
# ---------------------------------------------------------------------------


@router.post("/providers/{provider_id}/ldap/test")
async def test_ldap_connection(
    provider_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Test LDAP connection for a provider."""
    result = await identity_service.test_ldap_connection(db, provider_id)
    return EnvelopeResponse(data=result)


@router.post("/providers/{provider_id}/ldap/sync")
async def sync_ldap_users(
    provider_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Trigger manual LDAP user/group sync."""
    result = await identity_service.sync_ldap_users(db, provider_id)
    return EnvelopeResponse(data=result)


# ---------------------------------------------------------------------------
# SSO login flows (public -- no auth required)
# ---------------------------------------------------------------------------


@router.get("/sso/{provider_id}/login")
async def sso_login(
    provider_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Initiate SSO login flow.

    For SAML: returns redirect URL to IdP.
    For OIDC: returns authorization URL with PKCE parameters.
    """
    provider = await identity_service.get_provider(db, provider_id)

    if provider.provider_type == "saml":
        redirect_url = await identity_service.initiate_saml_login(db, provider_id)
        return EnvelopeResponse(data={"redirect_url": redirect_url})

    elif provider.provider_type == "oidc":
        result = await identity_service.initiate_oidc_login(db, provider_id)
        return EnvelopeResponse(data=result)

    else:
        return EnvelopeResponse(
            data=None,
            errors=[{"detail": f"SSO login not supported for {provider.provider_type} providers"}],
        )


@router.post("/sso/saml/acs")
async def saml_acs(
    request: Request,
    db: AsyncSession = Depends(get_db),
    SAMLResponse: str = Form(...),
    RelayState: str = Form(""),
):
    """SAML Assertion Consumer Service endpoint.

    Receives SAML response from IdP, validates it, provisions user,
    and redirects to frontend with JWT token.
    """
    # RelayState should contain the provider_id
    provider_id_str = RelayState if RelayState else request.query_params.get("provider_id", "")
    if not provider_id_str:
        # Try to find enabled SAML provider
        providers = await identity_service.list_providers(db)
        saml_providers = [p for p in providers if p.provider_type == "saml" and p.is_enabled]
        if not saml_providers:
            return EnvelopeResponse(
                data=None,
                errors=[{"detail": "No SAML provider configured"}],
            )
        provider_id = saml_providers[0].id
    else:
        try:
            provider_id = uuid.UUID(provider_id_str)
        except ValueError:
            return EnvelopeResponse(
                data=None,
                errors=[{"detail": "Invalid provider_id in RelayState"}],
            )

    token, is_new = await identity_service.handle_saml_response(db, SAMLResponse, provider_id)

    # Redirect to frontend with token
    frontend_url = settings.frontend_url.rstrip("/")
    return RedirectResponse(
        url=f"{frontend_url}/login?sso_token={token}&is_new_user={str(is_new).lower()}",
        status_code=302,
    )


@router.get("/sso/oidc/callback")
async def oidc_callback(
    db: AsyncSession = Depends(get_db),
    code: str = Query(...),
    state: str = Query(...),
    provider_id: uuid.UUID = Query(...),
    code_verifier: str = Query(""),
):
    """OIDC callback endpoint.

    Receives authorization code from IdP, exchanges for tokens,
    provisions user, and redirects to frontend with JWT.
    """
    token, is_new = await identity_service.handle_oidc_callback(
        db, code, state, provider_id, code_verifier or None
    )

    # Redirect to frontend with token
    frontend_url = settings.frontend_url.rstrip("/")
    return RedirectResponse(
        url=f"{frontend_url}/login?sso_token={token}&is_new_user={str(is_new).lower()}",
        status_code=302,
    )
