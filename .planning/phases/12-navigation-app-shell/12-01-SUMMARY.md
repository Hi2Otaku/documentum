---
phase: 12-navigation-app-shell
plan: 01
subsystem: frontend-auth-scaffolding
tags: [auth, zustand, shadcn, routing, placeholder-pages]
dependency_graph:
  requires: [JWT-auth, users-api]
  provides: [authStore-profile, AdminRoute, placeholder-pages, tooltip-component, avatar-component]
  affects: [12-02-sidebar]
tech_stack:
  added: ["@radix-ui/react-tooltip", "@radix-ui/react-avatar"]
  patterns: [jwt-decode-atob, optimistic-state-update, route-guard]
key_files:
  created:
    - frontend/src/api/users.ts
    - frontend/src/components/ui/tooltip.tsx
    - frontend/src/components/ui/avatar.tsx
    - frontend/src/components/layout/AdminRoute.tsx
    - frontend/src/pages/InboxPage.tsx
    - frontend/src/pages/DocumentsPage.tsx
    - frontend/src/pages/WorkflowsPage.tsx
  modified:
    - frontend/src/stores/authStore.ts
    - frontend/src/pages/LoginPage.tsx
    - frontend/package.json
    - frontend/package-lock.json
decisions:
  - "JWT decoded client-side via atob for userId/username; isSuperuser fetched from API since not in JWT payload"
  - "LoginPage redirects to /inbox instead of /templates as default landing page"
  - "setAvailability uses optimistic update with rollback pattern"
metrics:
  duration: 2m
  completed: "2026-04-06T03:37:10Z"
---

# Phase 12 Plan 01: Auth Foundation & Navigation Scaffolding Summary

Extended authStore with JWT-decoded user profile fields and API-fetched isSuperuser/isAvailable, created user API module, AdminRoute guard, Tooltip/Avatar shadcn components, and three placeholder pages for sidebar routing targets.

## What Was Done

### Task 1: Extend authStore and create user API module
- Rewrote `authStore.ts` with full profile fields: `userId`, `username`, `isSuperuser`, `isAvailable`
- JWT payload decoded via `atob(token.split('.')[1])` on `setToken` and on store initialization from localStorage
- Added `loadProfile()` action that fetches `/api/v1/users/{userId}` to get `is_superuser` and `is_available`
- Added `setAvailability()` with optimistic update and error rollback
- Created `api/users.ts` with `fetchUserProfile` and `updateAvailability` functions
- Updated `LoginPage.tsx` to call `loadProfile()` after login and redirect to `/inbox`
- **Commit:** `49054c9`

### Task 2: Install shadcn components, create AdminRoute and placeholder pages
- Installed `@radix-ui/react-tooltip` and `@radix-ui/react-avatar`
- Created shadcn `Tooltip` component wrapping Radix primitives with cn() styling
- Created shadcn `Avatar` component wrapping Radix primitives with cn() styling
- Created `AdminRoute` component that checks `isSuperuser` and redirects non-admins to `/inbox`
- Created `InboxPage`, `DocumentsPage`, `WorkflowsPage` placeholder pages with "Coming Soon" content
- **Commit:** `36f7848`

## Deviations from Plan

None - plan executed exactly as written.

## Verification

- TypeScript compilation passes (`npx tsc --noEmit` exits 0) after both tasks
- All acceptance criteria met for both tasks

## Known Stubs

| File | Description | Reason |
|------|-------------|--------|
| `frontend/src/pages/InboxPage.tsx` | "Coming Soon" placeholder | Intentional - real inbox UI is a future plan |
| `frontend/src/pages/DocumentsPage.tsx` | "Coming Soon" placeholder | Intentional - real documents UI is a future plan |
| `frontend/src/pages/WorkflowsPage.tsx` | "Coming Soon" placeholder | Intentional - real workflows UI is a future plan |

These stubs are intentional per the plan - they serve as routing targets for the sidebar (Plan 02). Real page content will be implemented in future phases.

## Self-Check: PASSED

All 7 created files verified on disk. Both commit hashes (49054c9, 36f7848) found in git history.
