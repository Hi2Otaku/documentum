# Phase 13: Inbox & Work Items - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the Inbox page where users manage their daily workflow tasks — viewing pending work items in a split-pane layout, acting on them (acquire/complete/reject), delegating tasks to other users, and browsing shared work queues to claim tasks. This is the primary daily-use surface of the application.

</domain>

<decisions>
## Implementation Decisions

### Inbox Layout
- **D-01:** Split-pane layout — work item table on the left, detail panel on the right. Clicking a row in the table loads its details in the side panel (no separate page navigation).
- **D-02:** Two tabs at the top of the page: "My Inbox" (personal work items) and "Queues" (shared work queue pools). Use shadcn Tabs component.
- **D-03:** Table in "My Inbox" tab uses TanStack Table with columns for task name, workflow name, priority, state badge, and created date. Filterable by state. Paginated.

### Work Item Actions
- **D-04:** Action buttons (Acquire, Complete, Reject) appear in the detail panel only — not inline in the table rows.
- **D-05:** Complete action: opens a dialog with optional comment text area + confirm button.
- **D-06:** Reject action: opens a dialog with required comment text area (cannot submit empty) + confirm button.
- **D-07:** Acquire action: single-click button in detail panel, no dialog needed.
- **D-08:** Detail panel shows: activity name, parent workflow name/state, performer info, priority, due date, comment history (chronological).

### Delegation
- **D-09:** Delegate button in the detail panel (Claude's discretion on UX — user-picker dialog is the standard approach).
- **D-10:** Availability toggle stays in sidebar only (Phase 12). No extra inbox-specific availability UI needed. System auto-routes when user is unavailable.

### Queue Browsing
- **D-11:** "Queues" tab shows a list of work queues the user belongs to. Click a queue to see its unclaimed items.
- **D-12:** Each queue item has a "Claim" button. Claiming moves the item to the user's personal inbox.

### Claude's Discretion
- Empty state for inbox when no work items exist
- Empty state for queues when no queues or no unclaimed items
- Detail panel when no item is selected
- Loading skeleton pattern for table and detail panel
- Table column widths and responsive behavior
- Comment display format (avatar, timestamp, threading)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Backend APIs
- `src/app/routers/inbox.py` — Inbox endpoints (list, detail, acquire, complete, reject, comments)
- `src/app/routers/queues.py` — Work queue endpoints (list, detail, members, claim)
- `src/app/schemas/inbox.py` — Request/response schemas for inbox endpoints
- `src/app/services/inbox_service.py` — Inbox business logic
- `src/app/routers/users.py` — User availability and delegation endpoints

### Frontend Patterns (from Phase 12)
- `frontend/src/stores/authStore.ts` — User state (userId, username, isSuperuser, isAvailable)
- `frontend/src/api/users.ts` — User API module pattern to follow
- `frontend/src/pages/InboxPage.tsx` — Placeholder to replace
- `frontend/src/components/query/QueryResultTable.tsx` — Reusable table pattern with TanStack Table
- `frontend/src/components/query/WorkItemQueryTab.tsx` — Existing work item query UI (different from inbox but shows data shape)
- `frontend/src/api/query.ts` — API module pattern to follow

### UI Components Available
- `frontend/src/components/ui/tabs.tsx` — For My Inbox / Queues tabs
- `frontend/src/components/ui/table.tsx` — For work item table
- `frontend/src/components/ui/badge.tsx` — For state badges
- `frontend/src/components/ui/dialog.tsx` — For complete/reject/delegate dialogs
- `frontend/src/components/ui/card.tsx` — For detail panel sections
- `frontend/src/components/ui/skeleton.tsx` — For loading states

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `QueryResultTable` component: headless TanStack Table wrapper with pagination — can be adapted for inbox table
- `api/query.ts`: fetch pattern with envelope unwrapping — follow for inbox API module
- `api/users.ts`: user profile/availability API — reuse for delegation user picker
- `badge.tsx`, `dialog.tsx`, `tabs.tsx`, `card.tsx`: all available shadcn components

### Established Patterns
- TanStack Query for server state (`useQuery`, `useMutation`)
- Zustand for UI state (authStore)
- Envelope response unwrapping (`response.data.data`)
- shadcn/ui + Tailwind for styling

### Integration Points
- `InboxPage.tsx` is the placeholder to replace (already routed at `/inbox`)
- authStore provides `userId` for filtering work items by current user
- Sidebar already highlights /inbox route

</code_context>

<specifics>
## Specific Ideas

No specific external references. Standard split-pane inbox pattern similar to email clients (Outlook, Gmail).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 13-inbox-work-items*
*Context gathered: 2026-04-06*
