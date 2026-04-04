---
phase: "08"
plan: "02"
subsystem: frontend/app-shell-auth
tags: [react, react-router, shadcn-ui, auth, login, template-list, protected-routes]
dependency_graph:
  requires: [react-frontend, backend-template-api, backend-auth-api]
  provides: [app-shell, login-page, template-list-page, protected-routes, auth-store]
  affects: [frontend/src/App.tsx, frontend/src/main.tsx]
tech_stack:
  added: [sonner, "@fontsource/inter", lucide-react, class-variance-authority, clsx, tailwind-merge, "@radix-ui/react-dialog", "@radix-ui/react-dropdown-menu"]
  patterns: [shadcn-ui-components, zustand-auth-store, protected-route-pattern, form-data-auth]
key_files:
  created:
    - frontend/src/pages/LoginPage.tsx
    - frontend/src/components/layout/AppShell.tsx
    - frontend/src/components/layout/ProtectedRoute.tsx
    - frontend/src/components/ui/button.tsx
    - frontend/src/components/ui/input.tsx
    - frontend/src/components/ui/card.tsx
    - frontend/src/components/ui/badge.tsx
    - frontend/src/components/ui/skeleton.tsx
    - frontend/src/components/ui/dialog.tsx
    - frontend/src/components/ui/dropdown-menu.tsx
    - frontend/src/lib/utils.ts
    - frontend/src/stores/authStore.ts
    - frontend/src/api/auth.ts
    - frontend/src/types/api.ts
    - frontend/src/vite-env.d.ts
  modified:
    - frontend/src/App.tsx
    - frontend/src/main.tsx
    - frontend/src/index.css
    - frontend/src/pages/TemplateListPage.tsx
    - frontend/src/api/templates.ts
    - frontend/package.json
decisions:
  - OAuth2 form-data auth (application/x-www-form-urlencoded) for login API
  - shadcn/ui components created manually (no interactive CLI) with Radix UI primitives
  - Auth store persists token in localStorage for session survival
  - deleteTemplate API function added to templates.ts (missing from Plan 01)
metrics:
  duration: 4min
  completed: "2026-04-04T04:46:35Z"
---

# Phase 08 Plan 02: App Shell, Auth, and Template List Summary

Authenticated SPA with login page, protected routes, app shell nav bar, and template list page using shadcn/ui components with create/delete functionality and toast notifications.

## What Was Built

### Task 1: App Shell, Routing, Protected Routes, and Login Page
- Updated `main.tsx` with `QueryClientProvider`, `BrowserRouter`, `Toaster` (sonner), and `@fontsource/inter` import
- Updated `App.tsx` with react-router Routes: `/login`, `/` (redirect), `/templates`, `/templates/:id/edit` (placeholder)
- Created `ProtectedRoute` component reading `isAuthenticated` from auth store, redirecting to `/login`
- Created `AppShell` with 48px nav bar: "Workflow Designer" title, "Templates" center link, "Logout" ghost button
- Created `LoginPage` with centered card, username/password inputs, "Sign In" button, error message, loading state
- Created auth store (Zustand) with token/isAuthenticated/setToken/logout
- Created auth API using OAuth2 form-data format (application/x-www-form-urlencoded)
- Installed and configured shadcn/ui utility components (Button, Input, Card, Badge, Skeleton, Dialog, DropdownMenu)
- Updated CSS with shadcn theme variables (oklch colors) and Inter font family
- **Commit:** 973d06c

### Task 2: Template List Page with Cards, Create, and Delete
- Rewrote `TemplateListPage` using shadcn/ui Card components instead of raw HTML table
- Each card shows: template name (font-semibold), state Badge (Draft=secondary, Active=green), version (v{n}), last modified date
- Clicking card navigates to `/templates/{id}/edit`
- "New Template" button creates "Untitled Template" and navigates to editor
- Three-dot overflow DropdownMenu on each card with "Delete" option (red text)
- Delete confirmation Dialog with cancel/delete buttons
- Loading state: 3 Skeleton cards with animated shimmer
- Empty state: "No workflow templates" heading, descriptive text, "New Template" button
- Error state: error message with "Retry" button
- Toast notifications via sonner for delete success/error
- Added `deleteTemplate` function to templates API client
- **Commit:** e7ce49c

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added deleteTemplate API function**
- **Found during:** Task 2
- **Issue:** Plan referenced `deleteTemplate` from templates API but it was not implemented in Plan 01
- **Fix:** Added `deleteTemplate(id: string): Promise<void>` to `frontend/src/api/templates.ts`
- **Files modified:** frontend/src/api/templates.ts
- **Commit:** 973d06c

**2. [Rule 3 - Blocking] Added vite-env.d.ts for @fontsource/inter**
- **Found during:** Task 2 verification
- **Issue:** `tsc -b` (build mode) could not resolve `@fontsource/inter` module types
- **Fix:** Created `frontend/src/vite-env.d.ts` with module declaration
- **Files modified:** frontend/src/vite-env.d.ts
- **Commit:** e7ce49c

## Known Stubs

None -- all components are fully wired to backend APIs and auth store.

## Verification

- `npx tsc --noEmit` passes with zero errors
- `npm run build` succeeds: 423KB JS (133KB gzipped), 42KB CSS (8KB gzipped)
- LoginPage contains loginApi, setToken, "Sign In", "Invalid username or password"
- ProtectedRoute contains isAuthenticated, Navigate, /login
- AppShell contains "Workflow Designer", "Logout", "Templates"
- App.tsx contains Route, /login, /templates, /templates/:id/edit
- TemplateListPage contains useQuery, listTemplates, useMutation, deleteTemplate, Dialog, Badge, "No workflow templates"
- main.tsx contains QueryClientProvider, BrowserRouter, Toaster

## Self-Check: PASSED
