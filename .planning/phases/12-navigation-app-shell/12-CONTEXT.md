# Phase 12: Navigation & App Shell - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the current top header bar (`AppShell.tsx`) with a collapsible left sidebar connecting all 6 application pages (Templates, Inbox, Documents, Workflows, Dashboard, Query). Add role-based visibility for admin-only pages and a user menu with availability toggle. This is a layout/navigation overhaul — no new pages are created in this phase.

</domain>

<decisions>
## Implementation Decisions

### Sidebar Layout
- **D-01:** Collapsible sidebar — toggle between icon+text (expanded) and icon-only (collapsed)
- **D-02:** Default to collapsed on page load. Persist expanded/collapsed preference in localStorage.
- **D-03:** Toggle mechanism: explicit toggle button to lock state, PLUS hover-to-peek when collapsed (sidebar temporarily expands on hover)
- **D-04:** Icon + text branding at top — workflow/document icon next to "Documentum", icon-only when collapsed
- **D-05:** Use Lucide icons (already available via shadcn/ui) for all nav items
- **D-06:** Group nav links by role: Main section (Templates, Inbox, Documents, Workflows) separated from Admin section (Dashboard, Query) with a divider
- **D-07:** Active page indicator: left accent border bar + subtle background highlight (both combined)

### User Menu
- **D-08:** User menu positioned at TOP of sidebar, under the logo/branding area
- **D-09:** Availability shown as a green/red status dot next to username. Click opens dropdown to toggle Available/Unavailable.
- **D-10:** User menu dropdown includes: username, availability toggle, "Admin" badge (if admin), logout button
- **D-11:** authStore needs to be extended to store user profile (username, is_superuser) — decode from JWT or fetch on login

### Role-Based Visibility
- **D-12:** Admin-only pages (Dashboard, Query) hidden from sidebar for non-admin users
- **D-13:** Direct URL access to admin pages by non-admin redirects silently to /inbox
- **D-14:** Admin users get a subtle "Admin" badge next to their username in the user menu

### Claude's Discretion
- Sidebar color scheme (dark vs light) — pick what works best with shadcn default theme
- Exact Lucide icon choices for each nav item
- Hover-to-peek animation timing and behavior
- Mobile/responsive behavior (the sidebar at small viewports)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Layout Code
- `frontend/src/components/layout/AppShell.tsx` — Current top-bar layout to be replaced
- `frontend/src/components/layout/ProtectedRoute.tsx` — Auth gate, needs role-based extension
- `frontend/src/stores/authStore.ts` — Zustand store, needs user profile data
- `frontend/src/App.tsx` — Route definitions, needs new routes for Inbox, Documents, Workflows

### UI Components
- `frontend/src/components/ui/dropdown-menu.tsx` — For user menu dropdown
- `frontend/src/components/ui/separator.tsx` — For section dividers
- `frontend/src/components/ui/button.tsx` — For toggle and menu items

### Backend APIs
- `src/app/routers/users.py` — User availability endpoint (PATCH)
- `src/app/routers/auth.py` — Login endpoint returns JWT with user info

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `dropdown-menu.tsx` (shadcn): Can be used for user menu dropdown
- `separator.tsx` (shadcn): For dividing Main and Admin nav sections
- `button.tsx` (shadcn): For sidebar toggle and nav items
- `badge.tsx` (shadcn): For "Admin" badge on user menu

### Established Patterns
- Zustand for client state (`authStore.ts`) — extend this store for user profile
- React Router 7 for routing (`App.tsx`) — add new routes, keep `ProtectedRoute` pattern
- shadcn/ui + Tailwind for all components — follow existing styling conventions
- `useAuthStore` hook pattern for auth state access

### Integration Points
- `AppShell.tsx` is the primary file to rewrite (wraps all protected routes via `<Outlet />`)
- `ProtectedRoute.tsx` needs a role-aware variant for admin routes
- `App.tsx` route definitions need `/inbox`, `/documents`, `/workflows` routes (placeholder pages for now)
- Login flow needs to store user profile data after successful auth

</code_context>

<specifics>
## Specific Ideas

No specific external references — standard collapsible sidebar pattern with the decisions captured above.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 12-navigation-app-shell*
*Context gathered: 2026-04-06*
