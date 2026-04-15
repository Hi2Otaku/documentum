---
phase: 36-identity-sso
plan: 01
subsystem: auth
tags: [auth, service-tokens, strategy-pattern, identity-provider]
dependency_graph:
  requires: []
  provides: [auth-backend-registry, service-token-crud, identity-provider-model]
  affects: [get_current_user, auth-endpoints]
tech_stack:
  added: []
  patterns: [strategy-pattern, pluggable-auth-backend]
key_files:
  created:
    - src/app/core/auth_backend.py
    - src/app/models/identity_provider.py
    - alembic/versions/phase36_identity_provider.py
  modified:
    - src/app/core/config.py
    - src/app/core/dependencies.py
    - src/app/routers/auth.py
    - src/app/schemas/auth.py
    - src/app/services/auth_service.py
decisions:
  - Strategy pattern for auth backends with ordered iteration (LocalAuth first, then ServiceToken)
  - SHA-256 hashing for service tokens with svc_ prefix to distinguish from JWTs
  - Service tokens reference a user_id (act-as identity) for Celery workers
metrics:
  duration: 2min
  completed: 2026-04-15
  tasks: 2
  files: 8
---

# Phase 36 Plan 01: Auth Backend Registry and Service Tokens Summary

Pluggable auth backend abstraction (Strategy pattern) with local JWT + service token backends, enabling future SAML/OIDC/LDAP integration without modifying get_current_user.

## What Was Built

### Auth Backend Registry (src/app/core/auth_backend.py)
- Abstract `AuthBackend` base class with `validate_token(token, db) -> User | None`
- `LocalAuthBackend`: decodes JWT, looks up user by sub claim (same logic as previous get_current_user)
- `ServiceTokenBackend`: SHA-256 hashes incoming token, looks up in service_tokens table, checks is_active and expiry, updates last_used_at
- `AuthBackendRegistry`: iterates backends in order until one returns a User
- Module-level singleton: `auth_backend_registry` with [LocalAuthBackend, ServiceTokenBackend]

### Identity Provider + Service Token Models (src/app/models/identity_provider.py)
- `IdentityProvider`: name, provider_type (ldap/saml/oidc), config (JSONB), is_enabled
- `ServiceToken`: token_hash (unique index), name, user_id (FK users), is_active, expires_at, last_used_at

### Migration (alembic/versions/phase36_identity_provider.py)
- Creates identity_providers and service_tokens tables
- Unique index on service_tokens.token_hash

### Rewired get_current_user (src/app/core/dependencies.py)
- Replaced hardcoded JWT decode with `auth_backend_registry.validate_token(token, db)`
- Existing OAuth2PasswordBearer tokenUrl and downstream dependencies unchanged

### Service Token CRUD Endpoints (src/app/routers/auth.py)
- POST /auth/service-tokens (admin only) - creates token, returns raw token once
- GET /auth/service-tokens (admin only) - lists all tokens (no raw token)
- DELETE /auth/service-tokens/{token_id} (admin only) - revokes token

### Service Token Service (src/app/services/auth_service.py)
- create_service_token: generates svc_ prefixed token, SHA-256 hashes for storage
- list_service_tokens: returns all non-deleted tokens
- revoke_service_token: sets is_active=False

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 2759b1b | Auth backend registry, identity provider and service token models |
| 2 | 310ead6 | Rewire get_current_user and add service token CRUD endpoints |

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED
