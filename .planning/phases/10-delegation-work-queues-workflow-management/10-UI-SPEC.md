---
status: draft
phase: 10
phase_name: delegation-work-queues-workflow-management
design_system: shadcn/ui (v4 CLI, Tailwind CSS 4, Radix UI)
created: 2026-04-04
---

# UI-SPEC: Phase 10 — Delegation, Work Queues & Workflow Management

## 1. Design System

**Tool:** shadcn/ui v4 with Tailwind CSS 4
**Preset:** Default (New York style) — inherited from Phase 08
**Icons:** Lucide React (ships with shadcn/ui)
**Font:** Inter via `@fontsource/inter`

### shadcn Components Required

| Component | Usage | Status |
|-----------|-------|--------|
| `button` | All action buttons, admin controls | Exists |
| `input` | Search fields, queue name, date range inputs | Exists |
| `card` | Queue cards, workflow summary cards | Exists |
| `badge` | Workflow state badges, queue member count, delegation status | Exists |
| `dialog` | Abort confirmation, delete queue confirmation, restart confirmation | Exists |
| `skeleton` | Loading states for all data tables and lists | Exists |
| `dropdown-menu` | Workflow row actions (halt/resume/abort/restart) | Exists |
| `table` | Workflow list, audit trail results, queue member list | NEW — install |
| `select` | Filter dropdowns (state, template, action type) | NEW — install |
| `switch` | Availability toggle (is_available on/off) | NEW — install |
| `label` | Form labels for filters and settings | NEW — install |
| `separator` | Section dividers in settings and detail panels | NEW — install |
| `popover` | Date range picker container | NEW — install |
| `calendar` | Date range selection for audit query filters | NEW — install |
| `tabs` | Admin section tabs (Workflows / Queues / Audit) | NEW — install |
| `alert-dialog` | Destructive action confirmations (abort, delete queue) | NEW — install |
| `avatar` | User avatars in queue member lists and delegation display | NEW — install |
| `command` | User search/picker for delegate selection and queue member add | Exists (Phase 08) |
| `scroll-area` | Scrollable audit results, long queue member lists | Exists (Phase 08) |
| `tooltip` | Action button descriptions, truncated text hover | Exists (Phase 08) |
| `sonner` (toast) | Success/error notifications for all admin actions | Exists |

### Third-Party Registries

None. All components from shadcn/ui official registry only.

## 2. Spacing

**Base unit:** 4px (inherited from Phase 08)
**Scale:** 4, 8, 16, 24, 32, 48, 64

| Token | Value | Usage |
|-------|-------|-------|
| `gap-1` | 4px | Inline icon-to-text spacing, badge internal spacing |
| `gap-2` | 8px | Between filter controls, table cell padding, between action buttons |
| `gap-4` | 16px | Between filter rows, between card sections, form field spacing |
| `gap-6` | 24px | Between major page sections (filters bar and table) |
| `gap-8` | 32px | Page container outer padding |
| `p-4` | 16px | Card inner padding, table header padding |
| `p-6` | 24px | Page section padding, dialog body padding |
| `p-8` | 32px | Page container padding |

### Touch/Click Targets

- Table row action buttons: minimum 36px height
- Filter dropdowns: 36px height (shadcn default)
- Switch toggle: 40px width x 24px height (shadcn default)
- Inline action icons (halt, resume, etc.): 32px square with 8px padding

### Layout Dimensions

| Element | Width | Notes |
|---------|-------|-------|
| Admin page max-width | 1200px | Centered container with `mx-auto` |
| Filter bar | 100% of container | Wraps on narrow viewports |
| Data table | 100% of container | Horizontal scroll if needed |
| Availability settings card | 480px max-width | Within user settings area |
| Queue detail panel | 400px max-width | Sidebar or inline panel |

## 3. Typography

Inherited from Phase 08. No changes.

**Font family:** `Inter` via `@fontsource/inter`
**Fallback:** `system-ui, -apple-system, sans-serif`

### Scale (4 sizes)

| Token | Size | Weight | Line Height | Usage |
|-------|------|--------|-------------|-------|
| `text-sm` | 14px | 400 (regular) | 1.43 (20px) | Table cell text, filter labels, badge text, helper text, metadata |
| `text-base` | 16px | 400 (regular) | 1.5 (24px) | Form inputs, dialog body text, descriptions |
| `text-lg` | 18px | 600 (semibold) | 1.33 (24px) | Section headings ("Workflows", "Work Queues"), card titles |
| `text-xl` | 20px | 600 (semibold) | 1.3 (26px) | Page title ("Administration") |

### Weights (2 only)

| Weight | Token | Usage |
|--------|-------|-------|
| 400 | `font-normal` | Body text, table cells, descriptions |
| 600 | `font-semibold` | Page titles, section headings, table headers, button labels |

## 4. Color

Inherited from Phase 08. Uses shadcn/ui CSS custom properties defined in `frontend/src/index.css`.

### 60/30/10 Distribution

| Role | Proportion | Token | Usage |
|------|-----------|-------|-------|
| Dominant surface | 60% | `--background` / `--card` | Page background, table background, dialog background |
| Secondary | 30% | `--muted` / `--accent` | Table header row, filter bar background, sidebar backgrounds, hover states |
| Accent | 10% | `--primary` | Primary action buttons, active tab indicator, selected row highlight |

### Accent Reserved For (this phase, exhaustive)

1. "Create Queue" button (primary variant)
2. "Save" button on availability settings
3. "Add Member" button in queue detail
4. Active tab indicator in admin tabs
5. "Apply Filters" button on audit query

### Workflow State Badge Colors

| State | Badge Variant | Background | Text |
|-------|--------------|------------|------|
| RUNNING | custom | `bg-green-100` | `text-green-700` |
| HALTED | custom | `bg-amber-100` | `text-amber-700` |
| FINISHED | custom | `bg-blue-100` | `text-blue-700` |
| FAILED | custom | `bg-red-100` | `text-red-700` |
| DORMANT | `secondary` | `--secondary` | `--secondary-foreground` |

### Work Item State Badge Colors

| State | Background | Text |
|-------|------------|------|
| AVAILABLE | `bg-green-100` | `text-green-700` |
| ACQUIRED | `bg-blue-100` | `text-blue-700` |
| SUSPENDED | `bg-amber-100` | `text-amber-700` |
| COMPLETED | `bg-gray-100` | `text-gray-700` |

### Delegation Status Indicator

| Status | Visual |
|--------|--------|
| Available | Green dot (8px circle `bg-green-500`) + "Available" text |
| Unavailable (with delegate) | Amber dot (8px circle `bg-amber-500`) + "Delegating to {name}" text |
| Unavailable (no delegate) | Red dot (8px circle `bg-red-500`) + "Unavailable" text |

### Semantic Colors

| Role | Token | Usage |
|------|-------|-------|
| Destructive | `--destructive` | Abort button, delete queue button, failed state badges |
| Success | `text-green-600` / `bg-green-100` | Running state badge, available indicator |
| Warning | `text-amber-600` / `bg-amber-100` | Halted state badge, suspended items, delegation active indicator |

## 5. Copywriting

### Primary CTAs

| Context | Label | Icon (Lucide) | Notes |
|---------|-------|---------------|-------|
| Create work queue | "Create Queue" | `Plus` | Admin queues page, primary button |
| Save availability | "Save" | none | User availability settings |
| Add queue member | "Add Member" | `UserPlus` | Queue detail panel |
| Apply audit filters | "Search" | `Search` | Audit query page |
| Halt workflow | "Halt" | `Pause` | Workflow row action, secondary variant |
| Resume workflow | "Resume" | `Play` | Workflow row action, secondary variant |
| Abort workflow | "Abort" | `XCircle` | Workflow row action, destructive variant |
| Restart workflow | "Restart" | `RotateCcw` | Workflow row action, secondary variant |

### Empty States

| Context | Heading | Body | Action |
|---------|---------|------|--------|
| Workflow list (no results) | "No workflows found" | "No workflow instances match your filters. Try adjusting the search criteria." | "Clear Filters" text button |
| Workflow list (none exist) | "No workflows yet" | "Workflow instances will appear here once users start workflows from installed templates." | None |
| Work queue list (none) | "No work queues" | "Create a work queue to enable shared task pools for your team." | "Create Queue" primary button |
| Queue members (empty) | "No members" | "Add users to this queue so they can claim incoming tasks." | "Add Member" button |
| Audit trail (no results) | "No audit records found" | "No records match your search criteria. Try widening the date range or removing filters." | "Clear Filters" text button |
| User delegation (not set) | N/A — always shows form | Switch is OFF, delegate picker is disabled/hidden | Toggle switch to enable |

### Error States

| Context | Message | Action |
|---------|---------|--------|
| Halt failed (wrong state) | Toast: "Cannot halt workflow. Current state: {state}. Only running workflows can be halted." | None (auto-dismiss 5s) |
| Resume failed (wrong state) | Toast: "Cannot resume workflow. Current state: {state}. Only halted workflows can be resumed." | None (auto-dismiss 5s) |
| Abort failed | Toast: "Failed to abort workflow. {error_detail}" | None |
| Restart failed (wrong state) | Toast: "Cannot restart workflow. Current state: {state}. Only failed workflows can be restarted." | None |
| Create queue failed (duplicate name) | Toast: "A queue with this name already exists." | Focus returns to name input |
| Add member failed (already member) | Toast: "This user is already a member of the queue." | None |
| Save availability failed | Toast: "Failed to update availability. Check your connection and try again." | Toast with "Retry" action |
| Delegate user not found | Inline error below picker: "Selected user could not be found." | None |
| API unreachable | Toast: "Cannot reach server. Check that the backend is running." | Automatic retry after 5s |

### Destructive Actions

| Action | Trigger | Confirmation |
|--------|---------|-------------|
| Abort workflow | "Abort" in workflow row dropdown | AlertDialog: "Abort workflow '{name}'? This will terminate the workflow and cancel all active tasks. This cannot be undone." with "Cancel" / "Abort Workflow" (destructive variant) buttons |
| Delete work queue | "Delete" in queue card action menu | AlertDialog: "Delete queue '{name}'? Activities assigned to this queue will lose their assignment. {N} active tasks will be affected." with "Cancel" / "Delete Queue" (destructive variant) buttons |
| Remove queue member | "Remove" next to member name | No confirmation for single member removal (reversible action) |
| Restart workflow | "Restart" in workflow row dropdown | AlertDialog: "Restart workflow '{name}'? This will reset the workflow to its initial state. All work items and progress will be cleared. Document attachments will be preserved." with "Cancel" / "Restart" buttons |

## 6. Component Inventory

### New Pages (3 total)

| Route | Page | Layout |
|-------|------|--------|
| `/admin` | Admin Dashboard (redirect to `/admin/workflows`) | App shell with nav bar |
| `/admin/workflows` | Workflow Management Page | App shell with admin tabs |
| `/admin/queues` | Work Queue Management Page | App shell with admin tabs |
| `/admin/audit` | Audit Trail Query Page | App shell with admin tabs |

### Modified Pages (1)

| Route | Page | Change |
|-------|------|--------|
| (new) `/settings` | User Settings Page | New page for delegation/availability settings |

### Navigation Changes

The AppShell header nav expands from a single "Templates" link to include:

```
[Workflow Designer]  Templates  |  Admin  |  Settings    [Logout]
```

- "Templates" links to `/templates` (existing)
- "Admin" links to `/admin/workflows` (visible only to superusers)
- "Settings" links to `/settings` (visible to all users)

### User Settings Page (`/settings`)

```
+--------------------------------------------------+
|  Page Title: "Settings"                          |
+--------------------------------------------------+
|                                                  |
|  +---[Availability Card, 480px max]------------+ |
|  | Section: "Delegation & Availability"        | |
|  |                                              | |
|  | [Switch] I am available for new tasks        | |
|  |                                              | |
|  | Delegate: [User Search Picker]               | |
|  | (visible only when switch is OFF)            | |
|  |                                              | |
|  | Helper: "When unavailable, new tasks will    | |
|  | automatically route to your delegate."       | |
|  |                                              | |
|  | [Save] button                                | |
|  +----------------------------------------------+ |
|                                                  |
+--------------------------------------------------+
```

- Switch component for `is_available` toggle
- When switch is OFF, delegate user picker appears (command component with search)
- When switch is ON, delegate picker is hidden
- "Save" button calls `PUT /api/v1/users/me/availability`
- Current status shown as colored dot + text (see Delegation Status Indicator above)

### Workflow Management Page (`/admin/workflows`)

```
+--------------------------------------------------+
|  Page Title: "Administration"                    |
|  Tabs: [Workflows] [Queues] [Audit Trail]        |
+--------------------------------------------------+
|  Filter Bar:                                     |
|  [State ▼] [Template ▼] [Created By ▼]          |
|  [Date From] [Date To]  [Search]                 |
+--------------------------------------------------+
|  Table:                                          |
|  | Name | Template | State | Started | Active   |
|  |      |          |       | By/At   | Activity |
|  |------|----------|-------|---------|----------|
|  | ...  | ...      | Badge | ...     | ...  [v] |
|  |------|----------|-------|---------|----------|
|  | ...  | ...      | Badge | ...     | ...  [v] |
+--------------------------------------------------+
|  Pagination: [< Prev] Page 1 of 5 [Next >]      |
+--------------------------------------------------+
```

#### Table Columns

| Column | Width | Content |
|--------|-------|---------|
| Name | flex | Workflow instance name (or template name + instance ID fragment) |
| Template | 180px | Template name, version badge |
| State | 100px | Colored badge (see Workflow State Badge Colors) |
| Started | 160px | "{username}" on line 1, "{date}" on line 2, both `text-sm` |
| Active Activity | 160px | Current activity name, or "None" if finished/failed |
| Actions | 48px | Dropdown menu button (vertical dots icon) |

#### Row Action Dropdown

| Item | Icon | Condition | Style |
|------|------|-----------|-------|
| Halt | `Pause` | State is RUNNING | Default |
| Resume | `Play` | State is HALTED | Default |
| Abort | `XCircle` | State is RUNNING or HALTED | Destructive (red text) |
| Restart | `RotateCcw` | State is FAILED | Default |

Items not matching the condition are hidden (not disabled).

#### Filter Controls

| Filter | Component | Options |
|--------|-----------|---------|
| State | Select dropdown | All, Running, Halted, Finished, Failed, Dormant |
| Template | Select dropdown | Populated from `GET /api/v1/templates` |
| Created By | Select dropdown | Populated from `GET /api/v1/users` |
| Date From | Calendar popover | Date picker |
| Date To | Calendar popover | Date picker |

Filters apply on "Search" button click. "Clear Filters" text button resets all.

### Work Queue Management Page (`/admin/queues`)

```
+--------------------------------------------------+
|  Page Title: "Administration"                    |
|  Tabs: [Workflows] [Queues] [Audit Trail]        |
+--------------------------------------------------+
|  Header: "Work Queues"   [Create Queue] button   |
+--------------------------------------------------+
|  +--[Queue Card]----+ +--[Queue Card]----+       |
|  | Queue Name       | | Queue Name       |       |
|  | Description...   | | Description...   |       |
|  | Members: 5   [...] | Members: 3   [...] |     |
|  +------------------+ +------------------+       |
|                                                  |
|  +--[Queue Card]----+                            |
|  | Queue Name       |                            |
|  | Description...   |                            |
|  | Members: 0   [...] |                          |
|  +------------------+                            |
+--------------------------------------------------+
```

#### Queue Card Layout

- Card component, grid layout (2-3 columns depending on viewport)
- Card header: queue name (`text-lg font-semibold`)
- Card body: description text (`text-sm text-muted-foreground`), max 2 lines with truncation
- Card footer: "Members: {count}" badge, overflow menu (three dots)
- Click card to open queue detail (inline expand or navigate to `/admin/queues/:id`)
- Overflow menu: "Edit", "Delete" (destructive)

#### Queue Detail View (expanded or inline)

```
+--------------------------------------------------+
|  Back arrow + Queue Name          [Edit] [Delete] |
+--------------------------------------------------+
|  Description: "Shared pool for..."               |
|  Created: 2026-04-01                             |
+--------------------------------------------------+
|  Members ({count})              [Add Member]      |
|  +----------------------------------------------+|
|  | Avatar  Username     Email         [Remove]  ||
|  | Avatar  Username     Email         [Remove]  ||
|  | Avatar  Username     Email         [Remove]  ||
|  +----------------------------------------------+|
+--------------------------------------------------+
```

- "Add Member" opens a command (search) popover to find and add users
- Each member row: avatar initial, username, email, "Remove" text button
- "Delete" button triggers AlertDialog confirmation

#### Create/Edit Queue Dialog

- Dialog component
- Fields: Name (input, required), Description (textarea, optional)
- Buttons: "Cancel" (ghost), "Create Queue" / "Save Changes" (primary)

### Audit Trail Query Page (`/admin/audit`)

```
+--------------------------------------------------+
|  Page Title: "Administration"                    |
|  Tabs: [Workflows] [Queues] [Audit Trail]        |
+--------------------------------------------------+
|  Filter Bar:                                     |
|  [User ▼] [Action Type ▼]                       |
|  [Workflow ID] [Document ID]                     |
|  [Date From] [Date To]  [Search]                 |
+--------------------------------------------------+
|  Table:                                          |
|  | Timestamp | User | Action | Entity | Details  |
|  |-----------|------|--------|--------|---------|
|  | ...       | ...  | Badge  | ...    | {...}   |
+--------------------------------------------------+
|  Pagination: [< Prev] Page 1 of 20 [Next >]     |
+--------------------------------------------------+
```

#### Table Columns

| Column | Width | Content |
|--------|-------|---------|
| Timestamp | 180px | ISO format, `text-sm font-mono` |
| User | 140px | Username |
| Action | 160px | Action type as badge (`outline` variant) |
| Entity | 200px | "{entity_type}: {entity_id_fragment}" |
| Details | flex | JSON details truncated to single line, expandable on click |

#### Details Expansion

Clicking a row expands inline to show the full JSON `details` field formatted as a code block with `text-sm font-mono bg-muted p-4 rounded-md`. Click again to collapse.

#### Filter Controls

| Filter | Component | Options |
|--------|-----------|---------|
| User | Select dropdown | Populated from `GET /api/v1/users` |
| Action Type | Select dropdown | All, work_item_created, work_item_completed, work_item_rejected, work_item_delegated, workflow_started, workflow_halted, workflow_resumed, workflow_aborted, workflow_restarted, document_uploaded, lifecycle_transition, acl_changed |
| Workflow ID | Text input | UUID paste field |
| Document ID | Text input | UUID paste field |
| Date From | Calendar popover | Date picker |
| Date To | Calendar popover | Date picker |

## 7. Interaction Contracts

### Availability Toggle Flow

1. User navigates to `/settings`
2. Page loads current availability from `GET /api/v1/users/me` (or from auth store user object)
3. Switch shows current `is_available` state
4. User toggles switch OFF: delegate picker fades in (150ms transition)
5. User searches for delegate in command picker, selects a user
6. User clicks "Save"
7. PUT `/api/v1/users/me/availability` with `{ is_available: false, delegate_id: "..." }`
8. Success: toast "Availability updated. New tasks will route to {delegate_name}."
9. User toggles switch ON: delegate picker fades out
10. User clicks "Save"
11. PUT with `{ is_available: true, delegate_id: null }`
12. Success: toast "You are now available for new tasks."

### Workflow Halt Flow

1. Admin clicks vertical dots on a RUNNING workflow row
2. Dropdown shows "Halt", "Abort" options
3. Admin clicks "Halt"
4. POST `/api/v1/workflows/{id}/halt`
5. Success: row state badge transitions to HALTED (amber), toast "Workflow halted."
6. Dropdown now shows "Resume", "Abort" instead

### Workflow Abort Flow

1. Admin clicks "Abort" from dropdown
2. AlertDialog opens with confirmation message
3. Admin clicks "Abort Workflow" (destructive button)
4. POST `/api/v1/workflows/{id}/abort`
5. Success: row state badge transitions to FAILED (red), toast "Workflow aborted."
6. AlertDialog closes
7. Dropdown now shows "Restart" only

### Workflow Restart Flow

1. Admin clicks "Restart" on a FAILED workflow
2. AlertDialog opens explaining state will be reset
3. Admin clicks "Restart"
4. POST `/api/v1/workflows/{id}/restart`
5. Success: row state badge transitions to DORMANT, toast "Workflow reset. It can now be started again."

### Queue Creation Flow

1. Admin clicks "Create Queue"
2. Dialog opens with name and description fields
3. Admin fills fields, clicks "Create Queue"
4. POST `/api/v1/queues/`
5. Success: dialog closes, new queue card appears in grid, toast "Queue '{name}' created."
6. Failure (duplicate name): toast with error message, dialog stays open

### Queue Member Management Flow

1. Admin clicks a queue card to expand/open detail
2. Current members listed in table
3. Admin clicks "Add Member", command popover opens
4. Admin searches by username, selects user
5. POST `/api/v1/queues/{id}/members` with `{ user_id: "..." }`
6. Success: member appears in list, toast "Member added."
7. Admin clicks "Remove" on a member row
8. DELETE `/api/v1/queues/{id}/members/{user_id}`
9. Member removed from list immediately (optimistic), toast "Member removed."

### Audit Query Flow

1. Admin selects filters (any combination)
2. Admin clicks "Search"
3. Table shows loading skeleton (5 rows)
4. GET `/api/v1/audit/?...query_params`
5. Results populate table with pagination
6. Admin clicks a row to expand details JSON
7. Admin clicks "Clear Filters" to reset, table re-fetches without filters

## 8. Loading & Skeleton States

### Workflow Table Loading

- 5 skeleton rows, each: 48px height, animated shimmer
- Each row: 4 shimmer bars at column widths (30%, 20%, 10%, 20%)

### Queue Cards Loading

- 3 skeleton cards in 2-column grid
- Each card: 120px height, title shimmer (50% width), body shimmer (80% width), footer shimmer (30% width)

### Audit Table Loading

- 5 skeleton rows matching audit table column layout

### Settings Page Loading

- Card skeleton with switch placeholder and input placeholder

### Action Button Loading

- When admin action (halt/resume/abort/restart) is in progress:
  - Dropdown closes
  - Row shows subtle loading shimmer on the state badge cell
  - Action completes: badge updates, shimmer stops

## 9. Responsive Behavior

Admin pages are desktop-first. Minimum supported viewport: 1024px.

| Breakpoint | Behavior |
|------------|----------|
| >= 1280px | Full layout: data tables render all columns, queue cards in 3-column grid |
| 1024-1279px | Tables hide "Active Activity" column, queue cards in 2-column grid |
| < 1024px | Warning banner: "Admin pages require a larger screen" with link to templates |

Settings page (user availability) works at all widths down to 375px (mobile-friendly).

## 10. Accessibility

- All table headers use `<th scope="col">` with descriptive text
- Data tables use `role="grid"` with keyboard arrow navigation
- Filter labels are associated with their inputs via `htmlFor`/`id`
- Switch component has `aria-label="Toggle availability for new tasks"`
- Workflow action dropdown items have `aria-label` with full action description (e.g., "Halt workflow {name}")
- State badges use `aria-label` with full state name (not relying on color alone)
- AlertDialog focus traps correctly, ESC closes, focus returns to trigger element
- Color is never the sole indicator: state badges include text labels alongside color
- Expandable audit rows use `aria-expanded` attribute
- Minimum contrast ratio: 4.5:1 for all text (badge text on colored backgrounds verified)
- Tab navigation between admin sections uses `aria-selected` on active tab

## 11. State Management

### Zustand Stores

| Store | State | Purpose |
|-------|-------|---------|
| `useAuthStore` | `token`, `user`, `isAuthenticated` | Existing — extended with `is_available`, `delegate_id` on user object |

No new Zustand stores needed. All admin pages are server-state driven via TanStack Query.

### TanStack Query Keys

| Key | Endpoint | Stale Time |
|-----|----------|------------|
| `["workflows", filters]` | GET `/api/v1/workflows/?...` | 10 seconds |
| `["queues"]` | GET `/api/v1/queues/` | 30 seconds |
| `["queues", id]` | GET `/api/v1/queues/{id}` | 30 seconds |
| `["audit", filters]` | GET `/api/v1/audit/?...` | 0 (always fresh) |
| `["users"]` | GET `/api/v1/users` | 5 minutes (existing) |
| `["templates"]` | GET `/api/v1/templates` | 30 seconds (existing) |

### Mutations

| Key | Endpoint | Invalidates |
|-----|----------|------------|
| `haltWorkflow` | POST `/api/v1/workflows/{id}/halt` | `["workflows"]` |
| `resumeWorkflow` | POST `/api/v1/workflows/{id}/resume` | `["workflows"]` |
| `abortWorkflow` | POST `/api/v1/workflows/{id}/abort` | `["workflows"]` |
| `restartWorkflow` | POST `/api/v1/workflows/{id}/restart` | `["workflows"]` |
| `createQueue` | POST `/api/v1/queues/` | `["queues"]` |
| `updateQueue` | PUT `/api/v1/queues/{id}` | `["queues", id]` |
| `deleteQueue` | DELETE `/api/v1/queues/{id}` | `["queues"]` |
| `addQueueMember` | POST `/api/v1/queues/{id}/members` | `["queues", id]` |
| `removeQueueMember` | DELETE `/api/v1/queues/{id}/members/{uid}` | `["queues", id]` |
| `updateAvailability` | PUT `/api/v1/users/me/availability` | `["users", "me"]` |

## 12. Pagination Contract

All paginated endpoints use the existing `EnvelopeResponse` with `PaginationMeta` pattern.

### URL Query Parameters

| Parameter | Type | Default |
|-----------|------|---------|
| `skip` | int | 0 |
| `limit` | int | 20 |

### Pagination UI

- Bottom of table: "Showing {from}-{to} of {total}" text
- "Previous" / "Next" buttons, disabled at boundaries
- No page number buttons (simple prev/next navigation)

---

*Generated: 2026-04-04*
*Source: CONTEXT.md (D-01 through D-11), REQUIREMENTS.md (USER-05, INBOX-08, QUEUE-01 through QUEUE-04, MGMT-01 through MGMT-05, AUDIT-05), Phase 08 UI-SPEC (design system inheritance), existing codebase (AppShell, components/ui/)*
