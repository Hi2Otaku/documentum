---
phase: 36-identity-sso
plan: "02"
subsystem: identity
tags: [sso, ldap, saml, oidc, jit-provisioning, auth]
dependency_graph:
  requires: [36-01]
  provides: [identity-service, sso-endpoints, jit-provisioning]
  affects: [auth-system, user-management]
tech_stack:
  added: []
  patterns: [graceful-degradation-imports, pkce-oauth2, jit-user-provisioning, strategy-pattern-auth]
key_files:
  created:
    - src/app/services/identity_service.py
    - src/app/schemas/identity.py
    - src/app/routers/identity.py
  modified:
    - src/app/core/config.py
    - src/app/main.py
decisions:
  - "Optional SSO library imports with try/except ImportError returning 501 for graceful degradation"
  - "SSO callbacks redirect to frontend with JWT as query param rather than returning JSON"
  - "OIDC uses PKCE with S256 code challenge method for public client security"
  - "JIT provisioning creates missing groups automatically on first SSO login"
metrics:
  duration: "4min"
  completed: "2026-04-15"
  tasks_completed: 2
  tasks_total: 2
  files_created: 3
  files_modified: 2
---

# Phase 36 Plan 02: LDAP/SAML/OIDC SSO Integration Summary

Identity service with LDAP directory sync, SAML 2.0 SP-initiated flow, OIDC authorization code with PKCE, and JIT user provisioning on first SSO login.

## What Was Built

### Task 1: Identity Service + Schemas (8c7a436)

Created the core identity service layer:

- **Schemas** (`src/app/schemas/identity.py`): LDAPConfig, SAMLConfig, OIDCConfig for provider-specific configuration; IdentityProviderCreate/Update/Response for CRUD; SSOCallbackResponse for SSO flow results
- **Identity service** (`src/app/services/identity_service.py`):
  - Provider CRUD: create, get, list, update, soft-delete with config validation per type
  - JIT provisioning: creates user on first SSO login, maps IdP groups to system groups, creates missing groups, records audit trail
  - SAML: initiate_saml_login builds AuthnRequest redirect; handle_saml_response validates assertion, extracts attributes, provisions user, creates JWT
  - OIDC: initiate_oidc_login generates PKCE code_verifier/challenge and authorization URL; handle_oidc_callback exchanges code for tokens, decodes id_token claims, provisions user
  - LDAP: sync_ldap_users connects to directory, searches users/groups, provisions via JIT; test_ldap_connection verifies bind
  - Graceful degradation: python3-saml, ldap3, authlib are optional imports -- HTTP 501 if not installed
- **Config** (`src/app/core/config.py`): Added sso_session_secret and frontend_url settings

### Task 2: Identity Router + Registration (2adf08a)

Created REST endpoints and registered them:

- **Router** (`src/app/routers/identity.py`):
  - Provider CRUD (admin only): POST/GET/PUT/DELETE /identity/providers with sensitive field masking
  - LDAP management (admin only): POST /identity/providers/{id}/ldap/test and /ldap/sync
  - SSO flows (public): GET /identity/sso/{provider_id}/login, POST /identity/sso/saml/acs, GET /identity/sso/oidc/callback
  - SSO callbacks redirect to frontend with JWT token as query parameter
- **Registration** (`src/app/main.py`): identity router added to application router list

## Deviations from Plan

None - plan executed exactly as written.

## Decisions Made

1. **Graceful degradation via ImportError**: python3-saml, ldap3, and httpx for OIDC are imported inside function bodies with try/except. System works without SSO libraries installed, returning HTTP 501 for unsupported features.
2. **Frontend redirect pattern**: SSO callbacks redirect to `{frontend_url}/login?sso_token={jwt}&is_new_user={bool}` rather than returning JSON, since the browser arrives at ACS/callback from IdP redirect.
3. **PKCE S256**: OIDC flow uses SHA-256 code challenge method for authorization code security.
4. **Auto-create groups**: JIT provisioning creates missing system groups when IdP returns group names that don't exist locally.

## Known Stubs

None -- all service functions contain complete implementation logic. External SSO libraries (python3-saml, ldap3) are optional dependencies that enable full functionality when installed.

## Self-Check: PASSED
