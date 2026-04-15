"""Schemas for identity provider configuration, SSO flows, and LDAP management."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class LDAPConfig(BaseModel):
    """LDAP directory connection configuration."""

    server_url: str = Field(..., description="LDAP server URL (e.g. ldap://ldap.example.com:389)")
    bind_dn: str = Field(..., description="Bind DN for LDAP connection")
    bind_password: str = Field(..., description="Bind password")
    base_dn: str = Field(..., description="Base DN for user/group searches")
    user_search_filter: str = Field(
        "(uid={username})", description="LDAP filter for user lookup"
    )
    group_search_filter: str = Field(
        "(objectClass=groupOfNames)", description="LDAP filter for group lookup"
    )
    group_mapping: dict[str, str] = Field(
        default_factory=dict,
        description="Maps LDAP group DN to system group name",
    )
    sync_interval_minutes: int = Field(60, description="Auto-sync interval in minutes")


class SAMLConfig(BaseModel):
    """SAML 2.0 SP configuration."""

    idp_metadata_url: str = Field(..., description="IdP metadata URL")
    idp_entity_id: str = Field(..., description="IdP entity ID")
    sp_entity_id: str = Field(..., description="SP entity ID")
    sp_acs_url: str = Field(..., description="SP Assertion Consumer Service URL")
    name_id_format: str = Field(
        "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
        description="NameID format",
    )
    attribute_mapping: dict[str, str] = Field(
        default_factory=lambda: {
            "username": "uid",
            "email": "mail",
            "groups": "memberOf",
        },
        description="Maps SAML attributes to user fields",
    )


class OIDCConfig(BaseModel):
    """OAuth2/OIDC authorization code flow configuration."""

    issuer_url: str = Field(..., description="OIDC issuer URL")
    client_id: str = Field(..., description="OAuth2 client ID")
    client_secret: str = Field(..., description="OAuth2 client secret")
    redirect_uri: str = Field(..., description="OAuth2 redirect URI (callback)")
    scopes: list[str] = Field(
        default_factory=lambda: ["openid", "profile", "email"],
        description="OAuth2 scopes",
    )
    attribute_mapping: dict[str, str] = Field(
        default_factory=lambda: {
            "username": "preferred_username",
            "email": "email",
            "groups": "groups",
        },
        description="Maps OIDC claims to user fields",
    )


class IdentityProviderCreate(BaseModel):
    """Create an identity provider configuration."""

    name: str = Field(..., description="Display name for this provider")
    provider_type: Literal["ldap", "saml", "oidc"]
    config: dict = Field(..., description="Provider-specific configuration")
    is_enabled: bool = False


class IdentityProviderUpdate(BaseModel):
    """Update an identity provider configuration."""

    name: str | None = None
    config: dict | None = None
    is_enabled: bool | None = None


class IdentityProviderResponse(BaseModel):
    """Identity provider response (sensitive fields masked)."""

    id: uuid.UUID
    name: str
    provider_type: str
    config: dict
    is_enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SSOLoginInitiate(BaseModel):
    """Initiate SSO login request."""

    provider_id: uuid.UUID


class SSOCallbackResponse(BaseModel):
    """Response after successful SSO authentication."""

    access_token: str
    token_type: str = "bearer"
    is_new_user: bool
