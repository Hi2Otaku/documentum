# Phase 36: Identity & SSO - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous YOLO mode)

<domain>
## Phase Boundary

Add enterprise identity provider integration (LDAP, SAML 2.0, OAuth2/OIDC) alongside existing local auth. Include JIT user provisioning on first SSO login and service tokens for background services (Celery workers, Workflow Agent).

Requirements: AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-06

Critical pitfall from research: existing get_current_user dependency is hardwired to local HS256 JWT. Need auth backend abstraction (Strategy pattern) + ServiceToken for background tasks before touching any SSO code.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion. Key research guidance:

- **Auth backend abstraction first**: Create a pluggable auth backend (Strategy pattern) so get_current_user can validate tokens from multiple sources (local JWT, SAML assertion, OIDC token, service token)
- **Libraries**: authlib for OAuth2/OIDC, python3-saml for SAML 2.0, ldap3 for LDAP directory sync
- **Service tokens**: Separate token type for Celery workers / Workflow Agent that doesn't require browser flow. Use a dedicated service account + long-lived JWT with "service" claim
- **JIT provisioning**: On first SSO login, create user record + map IdP groups to system groups
- **LDAP sync**: Admin configures connection string, base DN, group mapping. Periodic sync via Celery Beat task
- **Preserve local auth**: All existing username/password login must continue working unchanged
- **Admin settings page**: UI for configuring LDAP connection, SAML metadata URL, OAuth2 client ID/secret
- **Docker**: xmlsec1 system dependency needed for python3-saml — add to Dockerfile

</decisions>

<code_context>
## Existing Code Insights

### Key Files to Modify
- src/app/core/security.py — current JWT creation/verification
- src/app/core/dependencies.py — get_current_user dependency
- src/app/routers/auth.py — login endpoint
- All 28+ routers that use get_current_user

### Established Patterns
- FastAPI dependency injection for auth
- Pydantic settings for configuration
- Alembic migrations for schema changes
- Celery tasks for background processing

</code_context>

<specifics>
## Specific Ideas

- Auth backend should be a registry of providers, each with a `validate_token()` method
- Token prefix or claim distinguishes token source (local vs SSO vs service)
- SAML: implement SP-initiated flow (redirect to IdP, consume POST assertion)
- OAuth2/OIDC: authorization code flow with PKCE

</specifics>

<deferred>
## Deferred Ideas

None.

</deferred>
