---
status: draft
phase: 11
phase_name: dashboards-query-interface-validation
design_system: shadcn/ui (v4 CLI, Tailwind CSS 4, Radix UI)
created: 2026-04-04
---

# UI-SPEC: Phase 11 — Dashboards, Query Interface & Validation

## 1. Design System

**Tool:** shadcn/ui v4 with Tailwind CSS 4
**Preset:** Default (New York style) — inherited from Phase 08
**Icons:** Lucide React (ships with shadcn/ui)
**Font:** Inter via `@fontsource/inter`
**Charts:** Recharts 2.x (`recharts@^2.15.0`)
**Tables:** @tanstack/react-table 8.21.x

### shadcn Components Required

| Component | Usage | Status |
|-----------|-------|--------|
| `button` | Filter actions, template dropdown trigger | Exists |
| `input` | UUID filter fields, metadata search inputs | Exists |
| `card` | KPI summary cards, chart containers | Exists |
| `badge` | Workflow state badges, SLA status indicators | Exists |
| `dialog` | Entity detail views (workflow detail, document detail) | Exists |
| `skeleton` | Loading states for KPI cards, charts, and query tables | Exists |
| `dropdown-menu` | Workflow row actions in query results | Exists |
| `table` | Query result tables (all three tabs) | Exists (Phase 10) |
| `select` | Template filter dropdown on dashboard, state/priority filters on query | Exists (Phase 10) |
| `label` | Form labels for query filter fields | Exists (Phase 10) |
| `separator` | Section dividers between KPI row and chart area | Exists (Phase 10) |
| `popover` | Date range picker containers in query filters | Exists (Phase 10) |
| `calendar` | Date range selection in query filters | Exists (Phase 10) |
| `tabs` | Query interface tabs (Workflows / Work Items / Documents) | Exists (Phase 10) |
| `scroll-area` | Scrollable detail views, long query results | Exists (Phase 08) |
| `tooltip` | KPI card metric explanations, chart bar hover details | Exists (Phase 08) |
| `sonner` (toast) | SSE connection status, query error feedback | Exists |
| `command` | User picker for performer/assignee filters | Exists (Phase 08) |

### New Dependencies to Install

| Library | Install Command | Purpose |
|---------|----------------|---------|
| `recharts@^2.15.0` | `cd frontend && npm install recharts@^2.15.0` | Dashboard charts (BarChart for bottleneck/workload, gauge-like for SLA) |
| `@tanstack/react-table@^8.21.0` | `cd frontend && npm install @tanstack/react-table@^8.21.0` | Sortable, paginated query result tables |

### Third-Party Registries

None. All components from shadcn/ui official registry only.

## 2. Spacing

**Base unit:** 4px (inherited from Phase 08)
**Scale:** 4, 8, 16, 24, 32, 48, 64

| Token | Value | Usage |
|-------|-------|-------|
| `gap-1` | 4px | Icon-to-text within KPI cards, badge internal spacing |
| `gap-2` | 8px | Between filter controls, between KPI card label and value |
| `gap-3` | 12px | Between KPI cards in the top row |
| `gap-4` | 16px | Between chart containers, between filter rows, form field spacing |
| `gap-6` | 24px | Between major page sections (KPI row to chart area, chart area to SLA section) |
| `gap-8` | 32px | Page container outer padding |
| `p-4` | 16px | KPI card inner padding, chart container padding |
| `p-6` | 24px | Page section padding, query filter panel padding |
| `p-8` | 32px | Page container padding (matches existing TemplateListPage) |

### Touch/Click Targets

- Filter dropdowns: 36px height (shadcn default)
- Table row action buttons: minimum 36px height
- Template filter dropdown on dashboard: 36px height
- Tab triggers: 40px height (shadcn tabs default)

### Layout Dimensions

| Element | Width | Notes |
|---------|-------|-------|
| Dashboard page max-width | 1200px | Centered container with `mx-auto` |
| KPI card | Flex 1/5 (5 cards in row) | Min-width 180px, wrap on narrow viewports |
| Chart container | 50% of row (2-column layout) | Each chart in a Card component |
| SLA section | 100% of container | Full width below the chart row |
| Query page max-width | 1200px | Centered container with `mx-auto` |
| Filter panel | 100% of container | Wraps on narrow viewports |
| Query result table | 100% of container | Horizontal scroll if needed |
| Detail dialog | 640px max-width | For workflow/document detail views |

## 3. Typography

Inherited from Phase 08/10. No changes.

**Font family:** `Inter` via `@fontsource/inter`
**Fallback:** `system-ui, -apple-system, sans-serif`

### Scale (4 sizes)

| Token | Size | Weight | Line Height | Usage |
|-------|------|--------|-------------|-------|
| `text-sm` | 14px | 400 (regular) | 1.43 (20px) | KPI card labels, table cell text, filter labels, chart axis labels, metadata text |
| `text-base` | 16px | 400 (regular) | 1.5 (24px) | Form inputs, dialog body text, chart tooltips, query result descriptions |
| `text-lg` | 18px | 600 (semibold) | 1.33 (24px) | Section headings ("Bottleneck Activities", "Workload by User"), chart titles |
| `text-xl` | 20px | 600 (semibold) | 1.3 (26px) | Page title ("Dashboard", "Query") |

### KPI Card Value Typography

| Token | Size | Weight | Line Height | Usage |
|-------|------|--------|-------------|-------|
| `text-3xl` | 30px | 700 (bold) | 1.2 (36px) | KPI count values (running: 12, halted: 3, etc.) |

This is the one exception to the 2-weight rule: KPI card numeric values use `font-bold` (700) for visual emphasis as large dashboard numbers. All other text uses 400 or 600 only.

### Weights

| Weight | Token | Usage |
|--------|-------|-------|
| 400 | `font-normal` | Body text, table cells, filter labels, chart labels |
| 600 | `font-semibold` | Page titles, section headings, table headers, button labels, KPI card labels |
| 700 | `font-bold` | KPI card numeric values only |

## 4. Color

Inherited from Phase 08/10. Uses shadcn/ui CSS custom properties defined in `frontend/src/index.css`.

### 60/30/10 Distribution

| Role | Proportion | Token | Usage |
|------|-----------|-------|-------|
| Dominant surface | 60% | `--background` / `--card` | Page background, table background, dialog background, chart background |
| Secondary | 30% | `--muted` / `--accent` | KPI card backgrounds, filter bar area, table header row, chart grid lines |
| Accent | 10% | `--primary` | Template filter dropdown active state, active tab indicator, "Search" button, primary chart bar color |

### Accent Reserved For (this phase, exhaustive)

1. "Search" button on query filter panel
2. Active tab indicator in query tabs (Workflows / Work Items / Documents)
3. Template dropdown active selection on dashboard
4. Primary bar color in Recharts charts (`hsl(var(--primary))` mapped to `oklch(0.205 0 0)`)
5. SSE connection status dot when connected

### Dashboard KPI Card Colors

| Metric | Card Border Accent | Value Color | Icon (Lucide) |
|--------|-------------------|-------------|---------------|
| Running | `border-l-4 border-green-500` | `text-green-600` | `Play` |
| Halted | `border-l-4 border-amber-500` | `text-amber-600` | `Pause` |
| Finished | `border-l-4 border-blue-500` | `text-blue-600` | `CheckCircle` |
| Failed | `border-l-4 border-red-500` | `text-red-600` | `XCircle` |
| Avg Completion | `border-l-4 border-primary` | `text-foreground` | `Clock` |

Each KPI card has a 4px left border in its semantic color. The large numeric value uses the corresponding text color. The label below uses `text-muted-foreground`.

### Chart Colors

| Chart | Bar Color | Purpose |
|-------|-----------|---------|
| Bottleneck Activities | `hsl(var(--primary))` (dark gray/black) | Single-color horizontal bar chart, activity with longest duration at top |
| Workload by User | Three-color grouped bars: `#3b82f6` (blue, assigned), `#22c55e` (green, completed), `#f59e0b` (amber, pending) | Grouped bar chart per user |
| SLA Compliance | `#22c55e` (green, on-time), `#ef4444` (red, overdue) | Stacked or side-by-side bar showing compliance vs violation per activity |

### Workflow State Badge Colors (reused from Phase 10)

| State | Background | Text |
|-------|------------|------|
| RUNNING | `bg-green-100` | `text-green-700` |
| HALTED | `bg-amber-100` | `text-amber-700` |
| FINISHED | `bg-blue-100` | `text-blue-700` |
| FAILED | `bg-red-100` | `text-red-700` |
| DORMANT | `bg-secondary` | `text-secondary-foreground` |

### Work Item State Badge Colors (reused from Phase 10)

| State | Background | Text |
|-------|------------|------|
| AVAILABLE | `bg-green-100` | `text-green-700` |
| ACQUIRED | `bg-blue-100` | `text-blue-700` |
| SUSPENDED | `bg-amber-100` | `text-amber-700` |
| COMPLETED | `bg-gray-100` | `text-gray-700` |
| REJECTED | `bg-red-100` | `text-red-700` |

### Document Lifecycle Badge Colors

| State | Background | Text |
|-------|------------|------|
| DRAFT | `bg-gray-100` | `text-gray-700` |
| REVIEW | `bg-amber-100` | `text-amber-700` |
| APPROVED | `bg-green-100` | `text-green-700` |
| ARCHIVED | `bg-blue-100` | `text-blue-700` |

### Semantic Colors

| Role | Token | Usage |
|------|-------|-------|
| Destructive | `--destructive` | Failed state badges, overdue SLA bars |
| Success | `text-green-600` / `bg-green-100` | Running badge, on-time SLA, completed count |
| Warning | `text-amber-600` / `bg-amber-100` | Halted badge, pending work items |

### SSE Connection Indicator

| Status | Visual |
|--------|--------|
| Connected | Green dot (6px circle `bg-green-500`) + "Live" text in `text-sm text-muted-foreground` |
| Reconnecting | Amber dot (6px circle `bg-amber-500`) + "Reconnecting..." text |
| Disconnected | Red dot (6px circle `bg-red-500`) + "Offline" text |

Placed in the top-right corner of the dashboard page header, next to the template filter dropdown.

## 5. Copywriting

### Primary CTAs

| Context | Label | Icon (Lucide) | Notes |
|---------|-------|---------------|-------|
| Query filter submit | "Search" | `Search` | Primary button on each query tab |
| Clear query filters | "Clear Filters" | none | Ghost/link button, resets all filter fields |
| Dashboard template filter | Select dropdown with "All Templates" as default | `Filter` | No button needed, changes trigger immediate update |
| View entity detail | Row click (no button) | none | Clickable rows in query results navigate to detail views |

### Empty States

| Context | Heading | Body | Action |
|---------|---------|------|--------|
| Dashboard (no workflows exist) | "No workflow data" | "Start a workflow from an installed template to see metrics here." | "Go to Templates" link button |
| Dashboard (no data for selected template) | "No data for this template" | "No workflow instances have been started from this template yet." | "Show All Templates" ghost button |
| Query: Workflows (no results) | "No workflows found" | "No workflow instances match your filters. Try adjusting the search criteria." | "Clear Filters" ghost button |
| Query: Workflows (none exist) | "No workflows yet" | "Workflow instances will appear here once users start workflows from installed templates." | None |
| Query: Work Items (no results) | "No work items found" | "No work items match your filters. Try widening the date range or changing filters." | "Clear Filters" ghost button |
| Query: Documents (no results) | "No documents found" | "No documents match your filters. Try different metadata or lifecycle state criteria." | "Clear Filters" ghost button |
| Query: Documents (none exist) | "No documents yet" | "Documents will appear here once users upload files to the repository." | None |

### Error States

| Context | Message | Action |
|---------|---------|--------|
| Dashboard metrics load failed | Toast: "Failed to load dashboard metrics. Check your connection and try again." | Toast with "Retry" action button |
| SSE connection lost | Connection indicator changes to "Reconnecting..." (amber). Browser EventSource auto-reconnects. If >30s disconnected, show toast: "Live updates disconnected. Dashboard data may be stale." | "Refresh" link in toast |
| Query request failed | Toast: "Query failed. The server returned an error." | None (auto-dismiss 5s) |
| Query timeout (>10s) | Inline message above table: "This query is taking longer than expected. Results may be limited by date range." | None |
| Detail view load failed | Dialog body shows: "Failed to load details. Check your connection and try again." with "Retry" button | "Retry" button refetches |

### Destructive Actions

No destructive actions in this phase. The dashboard and query interface are read-only views. Workflow management actions (halt/resume/abort) remain in the Phase 10 admin page. The query interface provides navigation links to those actions but does not duplicate them.

## 6. Component Inventory

### New Pages (2 total)

| Route | Page | Layout |
|-------|------|--------|
| `/dashboard` | BAM Dashboard Page | App shell with nav bar |
| `/query` | Admin Query Interface Page | App shell with nav bar |

### Modified Components (1)

| Component | Change |
|-----------|--------|
| `AppShell` header nav | Add "Dashboard" and "Query" links |

### Navigation Changes

The AppShell header nav expands to include dashboard and query:

```
[Workflow Designer]  Templates  |  Dashboard  |  Query  |  Admin  |  Settings    [Logout]
```

- "Dashboard" links to `/dashboard` (visible to admin users)
- "Query" links to `/query` (visible to admin users)
- "Templates", "Admin", "Settings" remain unchanged from Phase 10

### Dashboard Page (`/dashboard`)

```
+------------------------------------------------------------------+
|  Page Title: "Dashboard"         [SSE: * Live]  [All Templates v] |
+------------------------------------------------------------------+
|                                                                   |
|  +--------+ +--------+ +--------+ +--------+ +-----------+       |
|  | Running| | Halted | |Finished| | Failed | | Avg Time  |       |
|  |   12   | |    3   | |   47   | |    2   | |  4.2 hrs  |       |
|  +--------+ +--------+ +--------+ +--------+ +-----------+       |
|                                                                   |
+------------------------------------------------------------------+
|                                                                   |
|  +--[Bottleneck Activities]---+ +--[Workload by User]----------+ |
|  | (horizontal bar chart)     | | (grouped vertical bar chart) | |
|  | Director Approval  ====   | |  User1  [|||]                 | |
|  | Legal Review       ===    | |  User2  [|||]                 | |
|  | Financial Review   ==     | |  User3  [|||]                 | |
|  | Draft Contract     =      | |                               | |
|  +----------------------------+ +-------------------------------+ |
|                                                                   |
+------------------------------------------------------------------+
|                                                                   |
|  +--[SLA Compliance]-------------------------------------------+ |
|  | (bar chart: green = on-time, red = overdue per activity)    | |
|  | Activity A  [============|===]                              | |
|  | Activity B  [========|=======]                              | |
|  +-------------------------------------------------------------+ |
|                                                                   |
+------------------------------------------------------------------+
```

#### KPI Cards Row

- 5 cards in a flex row with `gap-3`
- Each card: `Card` component with `border-l-4` in semantic color
- Card content: Lucide icon (16px, muted color) + label (`text-sm text-muted-foreground`) on top, large number (`text-3xl font-bold`) below
- KPI counts (running/halted/finished/failed) are live via SSE
- Average completion time shows hours with 1 decimal place (e.g., "4.2 hrs")
- Average completion time is from pre-aggregated data, refreshed on page load + SSE pushes

#### Template Filter Dropdown

- `Select` component positioned in the page header row, right-aligned
- Default option: "All Templates"
- Options populated from `GET /api/v1/templates` (active templates only)
- Selecting a template triggers: SSE reconnection with new template_id, chart data refetch
- All KPIs and charts update to reflect the selected template

#### Bottleneck Chart (left column)

- Recharts `BarChart` with `layout="vertical"`
- Horizontal bars showing average duration in hours per activity
- Sorted descending (longest at top)
- `XAxis` type="number" with label "Avg Hours"
- `YAxis` type="category" with activity names, width 120px
- Bar color: `hsl(var(--primary))`
- Tooltip shows exact hours on hover
- Max 10 activities displayed; if more, show top 10 with note "Showing top 10 of {N}"
- Data from pre-aggregated metrics table

#### Workload Chart (right column)

- Recharts `BarChart` with vertical orientation (default)
- Grouped bars per user: blue (assigned), green (completed), amber (pending)
- `XAxis` type="category" with usernames
- `YAxis` type="number" with label "Tasks"
- Legend below chart showing color mapping
- Tooltip shows breakdown on hover
- Max 15 users displayed; if more, show top 15 by total tasks
- Data from pre-aggregated metrics table

#### SLA Compliance Section (full width)

- Recharts `BarChart` with `layout="vertical"`
- Stacked horizontal bars per activity: green portion (on-time), red portion (overdue)
- Only shows activities that have `expected_duration_hours` configured
- `XAxis` type="number" with label "Work Items"
- `YAxis` type="category" with activity names
- Tooltip shows: "{N} on-time ({X}%), {M} overdue ({Y}%)"
- If no activities have SLA configured: show muted text "No activities have SLA time limits configured."
- Data from pre-aggregated metrics table

### Query Page (`/query`)

```
+------------------------------------------------------------------+
|  Page Title: "Query"                                             |
|  Tabs: [Workflows] [Work Items] [Documents]                      |
+------------------------------------------------------------------+
|  Filter Bar (varies by tab):                                     |
|  [Filter 1 v] [Filter 2 v] [Date From] [Date To]                |
|  [Search]  Clear Filters                                         |
+------------------------------------------------------------------+
|  Table:                                                          |
|  | Col 1 | Col 2 | Col 3 | Col 4 | Col 5 |                     |
|  |-------|-------|-------|-------|-------|                        |
|  | ...   | ...   | Badge | ...   | ...   |  <- clickable row     |
|  |-------|-------|-------|-------|-------|                        |
|  | ...   | ...   | Badge | ...   | ...   |                       |
+------------------------------------------------------------------+
|  Showing 1-20 of 142    [< Prev]  [Next >]                      |
+------------------------------------------------------------------+
```

#### Workflows Tab Filters

| Filter | Component | Options |
|--------|-----------|---------|
| Template | Select dropdown | "All Templates" + list from `GET /api/v1/templates` |
| State | Select dropdown | All, Running, Halted, Finished, Failed, Dormant |
| Started By | Select dropdown | "All Users" + list from `GET /api/v1/users` |
| Date From | Calendar popover | Date picker |
| Date To | Calendar popover | Date picker |

#### Workflows Tab Table Columns

| Column | Width | Content |
|--------|-------|---------|
| Name | flex | Workflow instance name (template name + ID fragment) |
| Template | 180px | Template name, version number |
| State | 100px | Colored badge (see Workflow State Badge Colors) |
| Started By | 140px | Username |
| Started At | 160px | Date formatted as "MMM DD, YYYY HH:mm" |
| Active Activity | 160px | Current activity name, or "---" if finished/failed |

Clicking a row opens a detail dialog showing: workflow state timeline, list of activity instances with states, attached work items, and a link to the audit trail filtered for this workflow.

#### Work Items Tab Filters

| Filter | Component | Options |
|--------|-----------|---------|
| Assignee | Select dropdown | "All Users" + list from `GET /api/v1/users` |
| State | Select dropdown | All, Available, Acquired, Completed, Rejected, Suspended |
| Workflow | Text input | Workflow instance ID (UUID paste field) |
| Priority | Select dropdown | All, Low, Normal, High, Urgent |

#### Work Items Tab Table Columns

| Column | Width | Content |
|--------|-------|---------|
| Activity | flex | Activity template name |
| Workflow | 180px | Workflow instance name (truncated) |
| Assignee | 140px | Username |
| State | 100px | Colored badge (see Work Item State Badge Colors) |
| Priority | 80px | Priority badge |
| Created At | 160px | Date formatted as "MMM DD, YYYY HH:mm" |

Clicking a row opens a detail dialog showing: work item details, activity configuration, comments, attached documents.

#### Documents Tab Filters

| Filter | Component | Options |
|--------|-----------|---------|
| Lifecycle State | Select dropdown | All, Draft, Review, Approved, Archived |
| Metadata Key | Text input | Key name to search (e.g., "author") |
| Metadata Value | Text input | Value to match (e.g., "John") |
| Version | Text input | Version label to filter (e.g., "1.0") |

#### Documents Tab Table Columns

| Column | Width | Content |
|--------|-------|---------|
| Title | flex | Document title |
| Lifecycle State | 120px | Colored badge (see Document Lifecycle Badge Colors) |
| Current Version | 80px | Version label (e.g., "2.1") |
| Author | 140px | `created_by` username |
| Updated At | 160px | Date formatted as "MMM DD, YYYY HH:mm" |
| Size | 80px | File size formatted (e.g., "2.4 MB") |

Clicking a row opens a detail dialog showing: document metadata, version history list, lifecycle state, current lock status.

## 7. Interaction Contracts

### Dashboard Load Flow

1. User navigates to `/dashboard`
2. Page renders 5 skeleton KPI cards + 2 skeleton chart areas + 1 skeleton SLA section
3. Initial fetch: `GET /api/v1/dashboard/metrics` returns all KPIs and chart data
4. KPI cards populate with numbers, charts render with Recharts
5. SSE connection opens: `EventSource(/api/v1/dashboard/stream?token=xxx)`
6. Connection indicator shows green dot + "Live"
7. Every SSE `kpi_update` event updates KPI card values (running/halted/finished/failed/avg_completion)
8. Chart data refreshes on page load and when template filter changes (not on every SSE event)

### Template Filter Change Flow

1. User selects a specific template from the dropdown
2. SSE connection closes and reopens with `template_id` query parameter
3. KPI cards show loading shimmer briefly
4. New KPI data arrives via SSE within 5 seconds
5. Chart data refetches: `GET /api/v1/dashboard/metrics?template_id=xxx`
6. Charts re-render with filtered data
7. User selects "All Templates" to return to combined view

### Query Tab Switch Flow

1. User clicks a tab (e.g., "Work Items")
2. Tab content switches immediately (no page navigation)
3. Filter panel updates to show tab-specific filters
4. Previous tab's filter state is preserved in component state (not lost on switch)
5. If the new tab has not been queried yet, table shows empty state
6. If the new tab has cached results, they display immediately

### Query Search Flow

1. User fills in one or more filter fields
2. User clicks "Search"
3. Table shows 5 skeleton rows
4. `GET /api/v1/query/workflows?template_id=x&state=RUNNING&...`
5. Results populate table with pagination
6. "Showing 1-20 of {total}" appears at bottom
7. User clicks "Next" to load page 2 (skip=20)
8. User clicks "Clear Filters" to reset all fields and re-fetch without filters

### Query Row Click Flow

1. User clicks a row in the query results table
2. Detail dialog opens with loading skeleton
3. Entity detail fetched (e.g., `GET /api/v1/workflows/{id}`)
4. Dialog populates with full entity information
5. For workflow details: shows activity instances, work items, link to audit
6. User clicks "Close" or presses ESC to dismiss

### SSE Reconnection Flow

1. SSE connection drops (network issue, server restart)
2. Connection indicator changes to amber "Reconnecting..."
3. Browser EventSource API auto-reconnects with exponential backoff
4. On reconnect: indicator returns to green "Live", KPIs update
5. If disconnected >30 seconds: toast "Live updates disconnected. Dashboard data may be stale." with "Refresh" link
6. KPI cards still show last-known values (not cleared)

## 8. Loading & Skeleton States

### Dashboard KPI Cards Loading

- 5 skeleton cards in flex row
- Each card: 100px height, shimmer bar for icon area (24x24px), shimmer bar for value (60% width, 30px height), shimmer bar for label (40% width, 14px height)

### Dashboard Charts Loading

- 2 skeleton chart containers in 2-column layout
- Each container: 300px height within Card, shimmer bars mimicking bar chart (5 horizontal bars of varying width)

### Dashboard SLA Section Loading

- 1 skeleton container full width
- 200px height, shimmer bars mimicking stacked horizontal bars

### Query Table Loading

- 5 skeleton rows matching the active tab's column layout
- Each row: 48px height, animated shimmer
- Column shimmer widths proportional to column definitions

### Detail Dialog Loading

- Dialog opens immediately at target size (640px max-width)
- Content area shows 3 shimmer bars (title 40% width, body 80% width, metadata 60% width)
- Buttons disabled until content loads

### Chart Refresh Loading

- When template filter changes, charts show a subtle overlay with 50% opacity + spinner
- KPI cards show shimmer on the value area only (label stays visible)
- Duration: typically <500ms for pre-aggregated data

## 9. Responsive Behavior

Dashboard and query pages are desktop-first. Minimum supported viewport: 1024px.

| Breakpoint | Behavior |
|------------|----------|
| >= 1280px | Full layout: KPI cards in single row (5 across), charts in 2-column layout, all table columns visible |
| 1024-1279px | KPI cards wrap to 3+2 rows, charts stack vertically (single column), query tables hide lowest-priority column per tab |
| < 1024px | Warning banner: "Dashboard and query pages require a larger screen" with link to templates page |

### Column Priority (hidden first at narrow viewports)

| Tab | Hidden Column at 1024-1279px |
|-----|------------------------------|
| Workflows | "Active Activity" |
| Work Items | "Created At" |
| Documents | "Size" |

## 10. Accessibility

- All chart containers have `role="img"` with `aria-label` describing the chart purpose (e.g., "Bar chart showing average duration per activity in hours")
- KPI cards use `role="status"` with `aria-live="polite"` so screen readers announce updates from SSE
- All filter labels are associated with their inputs via `htmlFor`/`id`
- Tab navigation uses `role="tablist"` / `role="tab"` / `role="tabpanel"` with `aria-selected`
- Clickable table rows use `role="link"` with `aria-label` describing the destination (e.g., "View workflow details for Contract Approval #a1b2")
- State badges use `aria-label` with full state name (not relying on color alone)
- SSE connection indicator has `aria-live="polite"` to announce status changes
- Color is never the sole indicator: all chart bars have tooltips with numeric values, badges include text labels
- Minimum contrast ratio: 4.5:1 for all text (chart text on white background verified)
- Date pickers are keyboard navigable (shadcn Calendar handles this)
- Recharts tooltips are keyboard-accessible via tab focus on bar elements

## 11. State Management

### Zustand Stores

No new Zustand stores needed. Dashboard and query pages are server-state driven via TanStack Query + SSE hook.

### Custom Hooks

| Hook | Purpose | Returns |
|------|---------|---------|
| `useDashboardSSE(templateId?)` | SSE connection for live KPI updates | `{ metrics: KpiMetrics \| null, status: "connected" \| "reconnecting" \| "disconnected" }` |
| `useDashboardMetrics(templateId?)` | One-shot fetch for chart data on page load and filter change | TanStack Query result with `DashboardMetrics` |
| `useQueryWorkflows(filters)` | Paginated workflow query | TanStack Query result with `PaginatedResponse<WorkflowQueryResult>` |
| `useQueryWorkItems(filters)` | Paginated work item query | TanStack Query result with `PaginatedResponse<WorkItemQueryResult>` |
| `useQueryDocuments(filters)` | Paginated document query | TanStack Query result with `PaginatedResponse<DocumentQueryResult>` |

### TanStack Query Keys

| Key | Endpoint | Stale Time |
|-----|----------|------------|
| `["dashboard", "metrics", templateId]` | GET `/api/v1/dashboard/metrics?template_id=...` | 30 seconds |
| `["query", "workflows", filters]` | GET `/api/v1/query/workflows?...` | 0 (always fresh on search) |
| `["query", "work-items", filters]` | GET `/api/v1/query/work-items?...` | 0 (always fresh on search) |
| `["query", "documents", filters]` | GET `/api/v1/query/documents?...` | 0 (always fresh on search) |
| `["templates"]` | GET `/api/v1/templates` | 30 seconds (existing, used for filter dropdowns) |
| `["users"]` | GET `/api/v1/users` | 5 minutes (existing, used for filter dropdowns) |

### SSE State (component-level)

The `useDashboardSSE` hook manages EventSource lifecycle internally. It stores:
- `metrics`: latest KPI data from SSE events
- `status`: connection status enum
- Cleanup: closes EventSource on unmount or templateId change

## 12. Pagination Contract

All paginated query endpoints use the existing `EnvelopeResponse` with `PaginationMeta` pattern.

### URL Query Parameters

| Parameter | Type | Default |
|-----------|------|---------|
| `skip` | int | 0 |
| `limit` | int | 20 |

### Pagination UI

- Bottom of table: "Showing {from}-{to} of {total}" text in `text-sm text-muted-foreground`
- "Previous" / "Next" buttons (`Button` variant="outline" size="sm"), disabled at boundaries
- No page number buttons (simple prev/next navigation, consistent with Phase 10)

---

*Generated: 2026-04-04*
*Source: CONTEXT.md (D-01 through D-11), REQUIREMENTS.md (BAM-01 through BAM-05, QUERY-01 through QUERY-03, EXAMPLE-01 through EXAMPLE-03), RESEARCH.md (standard stack, architecture patterns), Phase 10 UI-SPEC (design system inheritance), existing codebase (AppShell, components/ui/, index.css tokens, TemplateListPage patterns)*
