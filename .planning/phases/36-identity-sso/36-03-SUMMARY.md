---
phase: 36-identity-sso
plan: "03"
subsystem: frontend-identity
tags: [sso, identity, admin-ui, login]
dependency_graph:
  requires: [36-02]
  provides: [sso-settings-ui, sso-login-buttons]
  affects: [login-page, admin-nav, identity-router]
tech_stack:
  added: []
  patterns: [admin-crud-dialog, public-endpoint, sso-redirect-flow]
key_files:
  created:
    - frontend/src/api/identity.ts
    - frontend/src/pages/SSOSettingsPage.tsx
  modified:
    - frontend/src/pages/LoginPage.tsx
    - frontend/src/App.tsx
    - frontend/src/components/layout/SidebarNav.tsx
    - src/app/routers/identity.py
decisions:
  - KeyRound icon for SSO Settings nav (Shield already used by Retention)
  - LDAP providers excluded from login SSO buttons (users log in with local creds after sync)
  - PKCE code_verifier stored in sessionStorage for OIDC redirect flows
  - Public /providers/public endpoint placed before /{provider_id} to avoid route shadowing
metrics:
  duration: 3min
  completed: "2026-04-15T05:29:15Z"
  tasks: 2
  files: 6
requirements:
  - AUTH-01
  - AUTH-02
  - AUTH-03
  - AUTH-05
---

# Phase 36 Plan 03: SSO Frontend - Admin Settings and Login SSO Buttons Summary

Admin SSO settings page with LDAP/SAML/OIDC provider CRUD, plus login page SSO buttons with IdP redirect and token handling.

## What Was Built

### Task 1: Identity API Client + SSO Settings Admin Page
- **frontend/src/api/identity.ts**: Full API client with fetchProviders, createProvider, updateProvider, deleteProvider, testLdapConnection, syncLdap, fetchEnabledProviders (public), initiateSSOLogin
- **frontend/src/pages/SSOSettingsPage.tsx**: Admin page with provider table (name, type badge, enabled toggle, created date), CRUD via dialog with type-specific config fields (LDAP: server/bind/base DN/filters/sync interval; SAML: metadata URL/entity IDs/ACS URL; OIDC: issuer/client ID/secret/redirect URI/scopes), LDAP test connection and sync buttons, delete confirmation, sonner toast feedback
- Added /admin/sso route in App.tsx under AdminRoute
- Added "SSO Settings" nav item with KeyRound icon in SidebarNav.tsx admin section
- Added public /providers/public endpoint to backend identity router for login page consumption

### Task 2: Login Page SSO Buttons + Token Handling
- On mount, checks URL for sso_token parameter and authenticates (stores token, loads profile, navigates to /inbox)
- Fetches enabled providers from public endpoint for SSO buttons (graceful degradation on failure)
- Renders "Or sign in with" divider and buttons for SAML (Shield icon) and OIDC (KeyRound icon) providers
- LDAP providers excluded from buttons (they sync users who then use local login)
- Stores PKCE code_verifier in sessionStorage for OIDC flows
- Local login form (username/password/submit) completely preserved

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added public /providers/public endpoint to backend**
- **Found during:** Task 1
- **Issue:** Plan 02 backend did not include a public (unauthenticated) endpoint for the login page to fetch enabled providers
- **Fix:** Added GET /providers/public to identity router, returning minimal provider info (id, name, provider_type) for enabled providers only, placed before /{provider_id} route to avoid shadowing
- **Files modified:** src/app/routers/identity.py
- **Commit:** 7015104

## Decisions Made

1. Used KeyRound icon for SSO Settings nav item since Shield was already used by Retention
2. LDAP providers excluded from login page SSO buttons -- LDAP syncs users who then authenticate via local credentials
3. PKCE code_verifier stored in sessionStorage (survives redirect, cleared on tab close)
4. Public endpoint placed before parameterized route to prevent FastAPI path matching conflict

## Known Stubs

None -- all data flows are wired to real backend endpoints.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 7015104 | Admin SSO settings page with provider CRUD and nav integration |
| 2 | 6e2ea7c | Login page SSO buttons and sso_token handling |

## Self-Check: PASSED
