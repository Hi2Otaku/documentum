"""Identity service: LDAP sync, SAML assertion handling, OIDC token exchange, JIT provisioning.

External dependencies (python3-saml, ldap3, authlib) are optional -- if not installed,
the corresponding feature raises HTTP 501 (graceful degradation).
"""

import hashlib
import secrets
import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import create_access_token
from app.models.identity_provider import IdentityProvider
from app.models.user import Group, User, user_groups
from app.schemas.identity import (
    LDAPConfig,
    OIDCConfig,
    SAMLConfig,
)
from app.services.audit_service import create_audit_record

# ---------------------------------------------------------------------------
# Sensitive config fields that should be masked in API responses
# ---------------------------------------------------------------------------
_SENSITIVE_FIELDS = {"bind_password", "client_secret"}


def mask_config(config: dict) -> dict:
    """Return a copy of config with sensitive fields replaced by '***'."""
    masked = {}
    for key, value in config.items():
        if key in _SENSITIVE_FIELDS and value:
            masked[key] = "***"
        else:
            masked[key] = value
    return masked


# ---------------------------------------------------------------------------
# Provider CRUD
# ---------------------------------------------------------------------------


async def create_provider(
    db: AsyncSession, *, name: str, provider_type: str, config: dict, is_enabled: bool = False
) -> IdentityProvider:
    """Create a new identity provider."""
    # Validate config schema per type
    _validate_provider_config(provider_type, config)

    provider = IdentityProvider(
        name=name,
        provider_type=provider_type,
        config=config,
        is_enabled=is_enabled,
    )
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    return provider


async def get_provider(db: AsyncSession, provider_id: uuid.UUID) -> IdentityProvider:
    """Get a single identity provider by ID."""
    result = await db.execute(
        select(IdentityProvider).where(
            IdentityProvider.id == provider_id,
            IdentityProvider.is_deleted == False,  # noqa: E712
        )
    )
    provider = result.scalar_one_or_none()
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Identity provider not found",
        )
    return provider


async def list_providers(db: AsyncSession) -> list[IdentityProvider]:
    """List all non-deleted identity providers."""
    result = await db.execute(
        select(IdentityProvider).where(
            IdentityProvider.is_deleted == False  # noqa: E712
        )
    )
    return list(result.scalars().all())


async def update_provider(
    db: AsyncSession, provider_id: uuid.UUID, **kwargs: Any
) -> IdentityProvider:
    """Update an identity provider."""
    provider = await get_provider(db, provider_id)
    for key, value in kwargs.items():
        if value is not None:
            if key == "config":
                _validate_provider_config(provider.provider_type, value)
            setattr(provider, key, value)
    await db.commit()
    await db.refresh(provider)
    return provider


async def delete_provider(db: AsyncSession, provider_id: uuid.UUID) -> None:
    """Soft-delete an identity provider."""
    provider = await get_provider(db, provider_id)
    provider.is_deleted = True
    provider.is_enabled = False
    await db.commit()


# ---------------------------------------------------------------------------
# Config validation
# ---------------------------------------------------------------------------


def _validate_provider_config(provider_type: str, config: dict) -> None:
    """Validate provider config against the expected schema."""
    try:
        if provider_type == "ldap":
            LDAPConfig(**config)
        elif provider_type == "saml":
            SAMLConfig(**config)
        elif provider_type == "oidc":
            OIDCConfig(**config)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown provider type: {provider_type}",
            )
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid config for {provider_type}: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# JIT (Just-In-Time) User Provisioning
# ---------------------------------------------------------------------------


async def jit_provision_user(
    db: AsyncSession,
    username: str,
    email: str | None,
    groups_list: list[str],
    provider_name: str,
) -> tuple[User, bool]:
    """Provision or update a user from SSO attributes.

    Returns (user, is_new_user).
    """
    result = await db.execute(
        select(User)
        .options(selectinload(User.groups))
        .where(User.username == username, User.is_deleted == False)  # noqa: E712
    )
    user = result.scalar_one_or_none()
    is_new = user is None

    if is_new:
        # Create user with a random unusable password (SSO users don't use local auth)
        random_password = secrets.token_urlsafe(32)
        from app.core.security import hash_password

        user = User(
            username=username,
            email=email,
            hashed_password=hash_password(random_password),
            is_active=True,
            is_superuser=False,
        )
        db.add(user)
        await db.flush()

    # Map group names from IdP to system Group objects
    if groups_list:
        target_groups: list[Group] = []
        for group_name in groups_list:
            grp_result = await db.execute(
                select(Group).where(Group.name == group_name, Group.is_deleted == False)  # noqa: E712
            )
            group = grp_result.scalar_one_or_none()
            if group is None:
                # Create missing group
                group = Group(name=group_name)
                db.add(group)
                await db.flush()
            target_groups.append(group)

        user.groups = target_groups

    await db.commit()
    await db.refresh(user)

    # Audit record
    await create_audit_record(
        db,
        entity_type="user",
        entity_id=str(user.id),
        action="user_provisioned" if is_new else "user_sso_updated",
        user_id=str(user.id),
        details=f"SSO provider: {provider_name}",
    )

    return user, is_new


# ---------------------------------------------------------------------------
# SAML 2.0
# ---------------------------------------------------------------------------


async def initiate_saml_login(
    db: AsyncSession, provider_id: uuid.UUID, relay_state: str | None = None
) -> str:
    """Build SAML AuthnRequest redirect URL.

    Returns the redirect URL to the IdP.
    """
    try:
        from onelogin.saml2.auth import OneLogin_Saml2_Auth  # type: ignore[import-untyped]
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="SAML support not available (python3-saml not installed)",
        )

    provider = await get_provider(db, provider_id)
    if provider.provider_type != "saml":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider is not a SAML provider",
        )

    config = SAMLConfig(**provider.config)

    # Build python3-saml settings dict
    saml_settings = {
        "strict": True,
        "debug": False,
        "sp": {
            "entityId": config.sp_entity_id,
            "assertionConsumerService": {
                "url": config.sp_acs_url,
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
            },
            "NameIDFormat": config.name_id_format,
        },
        "idp": {
            "entityId": config.idp_entity_id,
            "singleSignOnService": {
                "url": config.idp_metadata_url,
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
        },
    }

    # Create a fake request for python3-saml
    request_data = {
        "https": "off",
        "http_host": "localhost",
        "script_name": "",
        "get_data": {},
        "post_data": {},
    }

    auth = OneLogin_Saml2_Auth(request_data, old_settings=saml_settings)
    redirect_url = auth.login(return_to=relay_state or "")
    return redirect_url


async def handle_saml_response(
    db: AsyncSession, saml_response_xml: str, provider_id: uuid.UUID
) -> tuple[str, bool]:
    """Validate SAML response and provision/authenticate user.

    Returns (jwt_token, is_new_user).
    """
    try:
        from onelogin.saml2.auth import OneLogin_Saml2_Auth  # type: ignore[import-untyped]
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="SAML support not available (python3-saml not installed)",
        )

    provider = await get_provider(db, provider_id)
    if provider.provider_type != "saml":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider is not a SAML provider",
        )

    config = SAMLConfig(**provider.config)

    saml_settings = {
        "strict": True,
        "debug": False,
        "sp": {
            "entityId": config.sp_entity_id,
            "assertionConsumerService": {
                "url": config.sp_acs_url,
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
            },
            "NameIDFormat": config.name_id_format,
        },
        "idp": {
            "entityId": config.idp_entity_id,
            "singleSignOnService": {
                "url": config.idp_metadata_url,
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
        },
    }

    request_data = {
        "https": "off",
        "http_host": "localhost",
        "script_name": "",
        "get_data": {},
        "post_data": {"SAMLResponse": saml_response_xml},
    }

    auth = OneLogin_Saml2_Auth(request_data, old_settings=saml_settings)
    auth.process_response()

    errors = auth.get_errors()
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"SAML validation failed: {', '.join(errors)}",
        )

    if not auth.is_authenticated():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="SAML authentication failed",
        )

    attributes = auth.get_attributes()
    attr_map = config.attribute_mapping

    username = _extract_attribute(attributes, attr_map.get("username", "uid"))
    email = _extract_attribute(attributes, attr_map.get("email", "mail"))
    groups_raw = attributes.get(attr_map.get("groups", "memberOf"), [])
    groups_list = groups_raw if isinstance(groups_raw, list) else [groups_raw]

    user, is_new = await jit_provision_user(db, username, email, groups_list, provider.name)

    token = create_access_token(
        data={"sub": str(user.id), "username": user.username, "auth_source": "saml"}
    )

    return token, is_new


# ---------------------------------------------------------------------------
# OIDC / OAuth2 Authorization Code with PKCE
# ---------------------------------------------------------------------------


async def initiate_oidc_login(db: AsyncSession, provider_id: uuid.UUID) -> dict:
    """Build OIDC authorization URL with PKCE.

    Returns {"redirect_url": url, "state": state, "code_verifier": verifier}.
    """
    provider = await get_provider(db, provider_id)
    if provider.provider_type != "oidc":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider is not an OIDC provider",
        )

    config = OIDCConfig(**provider.config)

    # Generate PKCE code_verifier and code_challenge
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = (
        hashlib.sha256(code_verifier.encode("ascii"))
        .digest()
    )
    import base64

    code_challenge_b64 = (
        base64.urlsafe_b64encode(code_challenge).rstrip(b"=").decode("ascii")
    )

    state = secrets.token_urlsafe(32)

    # Build authorization URL
    from urllib.parse import urlencode

    params = {
        "response_type": "code",
        "client_id": config.client_id,
        "redirect_uri": config.redirect_uri,
        "scope": " ".join(config.scopes),
        "state": state,
        "code_challenge": code_challenge_b64,
        "code_challenge_method": "S256",
    }

    # Discover authorization endpoint from issuer
    auth_endpoint = config.issuer_url.rstrip("/") + "/authorize"

    redirect_url = f"{auth_endpoint}?{urlencode(params)}"

    return {
        "redirect_url": redirect_url,
        "state": state,
        "code_verifier": code_verifier,
    }


async def handle_oidc_callback(
    db: AsyncSession,
    code: str,
    state: str,
    provider_id: uuid.UUID,
    code_verifier: str | None = None,
) -> tuple[str, bool]:
    """Exchange authorization code for tokens and provision/authenticate user.

    Returns (jwt_token, is_new_user).
    """
    try:
        import httpx  # noqa: F811
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="OIDC support not available (httpx not installed)",
        )

    provider = await get_provider(db, provider_id)
    if provider.provider_type != "oidc":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider is not an OIDC provider",
        )

    config = OIDCConfig(**provider.config)

    # Exchange authorization code for tokens
    token_endpoint = config.issuer_url.rstrip("/") + "/token"
    token_request_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": config.redirect_uri,
        "client_id": config.client_id,
        "client_secret": config.client_secret,
    }
    if code_verifier:
        token_request_data["code_verifier"] = code_verifier

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(token_endpoint, data=token_request_data)
        if token_resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Token exchange failed: {token_resp.text}",
            )
        token_data = token_resp.json()

    # Decode ID token to extract claims
    id_token = token_data.get("id_token")
    if not id_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No id_token in OIDC token response",
        )

    # Decode without verification for claim extraction
    # (token was received directly from IdP over TLS)
    import jwt as pyjwt

    try:
        claims = pyjwt.decode(id_token, options={"verify_signature": False})
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to decode id_token: {exc}",
        ) from exc

    attr_map = config.attribute_mapping
    username = claims.get(attr_map.get("username", "preferred_username"), "")
    email = claims.get(attr_map.get("email", "email"))
    groups_claim = claims.get(attr_map.get("groups", "groups"), [])
    groups_list = groups_claim if isinstance(groups_claim, list) else [groups_claim]

    if not username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No username claim found in OIDC id_token",
        )

    user, is_new = await jit_provision_user(db, username, email, groups_list, provider.name)

    token = create_access_token(
        data={"sub": str(user.id), "username": user.username, "auth_source": "oidc"}
    )

    return token, is_new


# ---------------------------------------------------------------------------
# LDAP
# ---------------------------------------------------------------------------


async def sync_ldap_users(db: AsyncSession, provider_id: uuid.UUID) -> dict:
    """Sync users and groups from an LDAP directory.

    Returns {"synced_users": count, "synced_groups": count}.
    """
    try:
        import ldap3  # type: ignore[import-untyped]
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="LDAP support not available (ldap3 not installed)",
        )

    provider = await get_provider(db, provider_id)
    if provider.provider_type != "ldap":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider is not an LDAP provider",
        )

    config = LDAPConfig(**provider.config)

    server = ldap3.Server(config.server_url, get_info=ldap3.ALL)
    conn = ldap3.Connection(server, user=config.bind_dn, password=config.bind_password, auto_bind=True)

    # Search for users
    conn.search(
        search_base=config.base_dn,
        search_filter=config.user_search_filter.replace("{username}", "*"),
        attributes=["uid", "mail", "memberOf"],
    )
    users_found = conn.entries

    synced_users = 0
    synced_groups = set()

    for entry in users_found:
        username = str(entry.uid) if hasattr(entry, "uid") else None
        email = str(entry.mail) if hasattr(entry, "mail") else None
        member_of = entry.memberOf.values if hasattr(entry, "memberOf") else []

        if not username:
            continue

        # Map LDAP group DNs to system group names using group_mapping
        mapped_groups = []
        for dn in member_of:
            system_name = config.group_mapping.get(str(dn))
            if system_name:
                mapped_groups.append(system_name)
                synced_groups.add(system_name)

        await jit_provision_user(db, username, email, mapped_groups, provider.name)
        synced_users += 1

    conn.unbind()

    return {"synced_users": synced_users, "synced_groups": len(synced_groups)}


async def test_ldap_connection(db: AsyncSession, provider_id: uuid.UUID) -> dict:
    """Test LDAP connectivity.

    Returns {"success": bool, "message": str}.
    """
    try:
        import ldap3  # type: ignore[import-untyped]
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="LDAP support not available (ldap3 not installed)",
        )

    provider = await get_provider(db, provider_id)
    if provider.provider_type != "ldap":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider is not an LDAP provider",
        )

    config = LDAPConfig(**provider.config)

    try:
        server = ldap3.Server(config.server_url, get_info=ldap3.ALL, connect_timeout=10)
        conn = ldap3.Connection(
            server, user=config.bind_dn, password=config.bind_password, auto_bind=True
        )
        conn.unbind()
        return {"success": True, "message": "LDAP connection successful"}
    except Exception as exc:
        return {"success": False, "message": f"LDAP connection failed: {exc}"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_attribute(attributes: dict, key: str) -> str:
    """Extract a single value from SAML attributes dict (values are lists)."""
    values = attributes.get(key, [])
    if isinstance(values, list) and values:
        return str(values[0])
    if isinstance(values, str):
        return values
    return ""
