---
status: draft
phase: 08
phase_name: visual-workflow-designer
design_system: shadcn/ui (v4 CLI, Tailwind CSS 4, Radix UI)
created: 2026-04-04
---

# UI-SPEC: Phase 08 — Visual Workflow Designer

## 1. Design System

**Tool:** shadcn/ui v4 with Tailwind CSS 4
**Preset:** Default (New York style)
**Icons:** Lucide React (ships with shadcn/ui)
**Initialization:** `npx shadcn@latest init` in `frontend/` directory during project setup

### shadcn Components Required

| Component | Usage |
|-----------|-------|
| `button` | Toolbar actions, save, validate, install, login |
| `input` | Form fields in properties panel, login form |
| `label` | Form labels in properties panel |
| `select` | Performer type dropdown, variable type dropdown, flow type |
| `tabs` | Properties panel tabs (Template Info, Variables) |
| `card` | Template list items |
| `badge` | Template state indicators (Draft, Active), node config hints |
| `dialog` | Delete confirmation, install confirmation |
| `separator` | Panel section dividers |
| `scroll-area` | Properties panel scrollable content, template list |
| `tooltip` | Toolbar button labels, node action hints |
| `sonner` (toast) | Save success/error, install success, validation result |
| `dropdown-menu` | Right-click context menu on nodes/edges |
| `alert` | Validation error panel items |
| `skeleton` | Loading states for template list, canvas |
| `sidebar` | Left palette sidebar (collapsible) |
| `navigation-menu` | Top nav bar |
| `command` | User/group picker search in performer assignment |

### Third-Party Registries

None. All components from shadcn/ui official registry only.

## 2. Spacing

**Base unit:** 4px
**Scale:** 4, 8, 16, 24, 32, 48, 64

| Token | Value | Usage |
|-------|-------|-------|
| `gap-1` | 4px | Inline icon-to-text spacing |
| `gap-2` | 8px | Between form fields within a group, badge padding, between toolbar buttons |
| `gap-4` | 16px | Section spacing within properties panel |
| `gap-6` | 24px | Between major panel sections |
| `gap-8` | 32px | Page-level content padding |
| `p-4` | 16px | Panel inner padding (left sidebar, right properties) |
| `p-6` | 24px | Card padding in template list |
| `p-8` | 32px | Page container padding |

### Touch/Click Targets

- Toolbar buttons: minimum 36px height
- Sidebar palette items (draggable nodes): 44px height for drag affordance
- Properties panel form inputs: 36px height (shadcn default)
- Node handles (React Flow connection points): 12px diameter with 24px invisible hit area

### Layout Dimensions

| Element | Width | Notes |
|---------|-------|-------|
| Left sidebar (palette) — expanded | 220px | Collapsible |
| Left sidebar (palette) — collapsed | 48px | Icons only |
| Right sidebar (properties panel) | 320px | Fixed when open, hidden when no selection AND template tabs closed |
| Top toolbar | 100% width, 48px height | Fixed top within designer |
| Bottom error panel | 100% width, 200px max-height | Collapsible, scrollable |
| Minimap | 200px x 150px | Bottom-right corner of canvas |

## 3. Typography

**Font family:** `Inter` via `@fontsource/inter` (shadcn default)
**Fallback:** `system-ui, -apple-system, sans-serif`

### Scale (4 sizes)

| Token | Size | Weight | Line Height | Usage |
|-------|------|--------|-------------|-------|
| `text-sm` | 14px | 400 (regular) | 1.43 (20px) | Form labels, table cells, node config hints, badge text, helper text |
| `text-base` | 16px | 400 (regular) | 1.5 (24px) | Body text, form inputs, properties panel content, template list descriptions |
| `text-lg` | 18px | 600 (semibold) | 1.33 (24px) | Panel headings ("Properties", "Variables"), section titles |
| `text-xl` | 20px | 600 (semibold) | 1.3 (26px) | Page titles ("Workflow Templates"), template name in editor |

### Weights (2 only)

| Weight | Token | Usage |
|--------|-------|-------|
| 400 | `font-normal` | Body text, form content, descriptions |
| 600 | `font-semibold` | Headings, panel titles, button labels, active nav items |

## 4. Color

Uses shadcn/ui CSS custom properties (HSL-based). All colors reference the theme tokens, not raw hex.

### 60/30/10 Distribution

| Role | Proportion | Token | Usage |
|------|-----------|-------|-------|
| Dominant surface | 60% | `--background` / `--card` | Canvas background, page background, panel backgrounds |
| Secondary | 30% | `--muted` / `--accent` | Sidebar backgrounds, toolbar background, template list cards, hover states |
| Accent | 10% | `--primary` | Primary CTA buttons (Save Template, Install), active nav indicator, selected node ring |

### Accent Reserved For (exhaustive list)

1. "Save Template" button (primary variant)
2. "Validate & Install" button (primary variant)
3. "Login" button on login page
4. Active navigation item underline/indicator
5. Selected node/edge highlight ring on canvas
6. "New Template" button on template list page

### Node Colors (canvas-specific, outside 60/30/10)

These are semantic colors for the workflow canvas nodes and edges, defined as Tailwind custom utilities or inline styles on React Flow nodes.

| Element | Color | Hex | Tailwind Class | Notes |
|---------|-------|-----|----------------|-------|
| Start node | Green | `#22c55e` | `bg-green-500` | Circle shape, white icon inside |
| Start node border | Dark green | `#16a34a` | `border-green-600` | 2px solid |
| Manual node | Blue | `#3b82f6` | `bg-blue-500` | Rounded rectangle, white text |
| Manual node border | Dark blue | `#2563eb` | `border-blue-600` | 2px solid |
| Auto node | Orange | `#f97316` | `bg-orange-500` | Hexagon shape, white text |
| Auto node border | Dark orange | `#ea580c` | `border-orange-600` | 2px solid |
| End node | Red | `#ef4444` | `bg-red-500` | Filled circle, white icon inside |
| End node border | Dark red | `#dc2626` | `border-red-600` | 2px solid |
| Normal flow edge | Dark gray | `#374151` | `stroke-gray-700` | Solid line, arrow marker |
| Reject flow edge | Red | `#ef4444` | `stroke-red-500` | Dashed line (`strokeDasharray: "8 4"`), arrow marker |
| Conditional flow edge | Blue | `#3b82f6` | `stroke-blue-500` | Dotted line (`strokeDasharray: "2 4"`), diamond marker |
| Selected element ring | Primary | `--primary` | `ring-primary` | 2px ring offset around selected node |
| Invalid node indicator | Destructive | `--destructive` | `ring-destructive` | Red ring + error badge on node |

### Semantic Colors

| Role | Token | Usage |
|------|-------|-------|
| Destructive | `--destructive` | Delete buttons, validation error borders, reject flow edges |
| Success | `#22c55e` / `text-green-600` | Validation passed indicator, "Installed" badge |
| Warning | `#f59e0b` / `text-amber-500` | Unsaved changes indicator dot |

## 5. Copywriting

### Primary CTAs

| Context | Label | Notes |
|---------|-------|-------|
| Save template | "Save Template" | Toolbar button with floppy disk icon. Keyboard shortcut: Ctrl+S |
| Validate and install | "Validate & Install" | Toolbar button. Runs validation first, installs if clean |
| Create new template | "New Template" | Template list page, primary button |
| Login | "Sign In" | Login page submit button |
| Add node from palette | No button — drag-and-drop only | Palette items are draggable, not clickable |

### Empty States

| Context | Heading | Body | Action |
|---------|---------|------|--------|
| Template list (no templates) | "No workflow templates" | "Create your first workflow template to get started." | "New Template" button |
| Canvas (new template) | No heading — blank canvas | Centered ghost text: "Drag activities from the left panel to start designing" | None (instructional text only) |
| Properties panel (no selection) | Shows template-level tabs | Template Info tab and Variables tab visible | None |
| Validation errors (none found) | "Validation Passed" | "Template is valid and ready for installation." | "Install" button enabled |

### Error States

| Context | Message | Action |
|---------|---------|--------|
| Login failed | "Invalid username or password." | Focus returns to username field |
| Save failed (network) | Toast: "Failed to save template. Check your connection and try again." | Toast with "Retry" action button |
| Save failed (conflict) | Toast: "Template was modified by another user. Reload to see changes." | Toast with "Reload" action button |
| Validation failed | Error panel: "{N} issue(s) found" with list of clickable errors | Each error clickable to pan to problem node |
| Template load failed | Full-page: "Could not load template" / "The template may have been deleted or you may not have access." | "Back to Templates" link |
| API unreachable | Toast: "Cannot reach server. Check that the backend is running." | Automatic retry after 5 seconds |

### Validation Error Messages (from backend, displayed in error panel)

These map from `ValidationErrorDetail.code` values. Display `message` field from API response directly. Each item shows:
- Error icon (red circle-x)
- Message text
- Click action: pan canvas to `entity_id` node and flash its border

### Destructive Actions

| Action | Trigger | Confirmation |
|--------|---------|-------------|
| Delete node(s) | Delete/Backspace key or context menu "Delete" | No confirmation for single node. Multi-select delete (3+ nodes): dialog "Delete {N} elements? This cannot be undone." with "Cancel" / "Delete" buttons |
| Delete template | Template list context action | Dialog: "Delete template '{name}'? This cannot be undone. Running workflow instances will not be affected." with "Cancel" / "Delete" buttons |
| Discard unsaved changes (navigate away) | Browser navigation or "Back" with unsaved changes | Browser `beforeunload` prompt + custom dialog: "You have unsaved changes. Discard and leave?" with "Stay" / "Discard" buttons |

## 6. Component Inventory

### Pages (3 total)

| Route | Page | Layout |
|-------|------|--------|
| `/login` | Login Page | Centered card, no nav bar |
| `/templates` | Template List Page | App shell with nav bar |
| `/templates/:id/edit` | Designer Canvas Page | App shell with nav bar, three-panel layout |

### Login Page

- Centered card (max-width 400px) with app logo/name at top
- Username input, password input, "Sign In" button
- Error message below form on failed login
- No "register" — admin creates accounts

### Template List Page

- Page title: "Workflow Templates"
- "New Template" primary button in header
- Grid or list of template cards showing: name, state badge (Draft/Active), version number, last modified date
- Click card to navigate to `/templates/:id/edit`
- Each card has overflow menu (three dots) with: "Delete" option
- Skeleton cards (3) while loading

### Designer Canvas Page (3-panel layout)

```
+--------------------------------------------------+
|  Top Toolbar (48px)                               |
|  [<-] Template Name  [Save Template] [Validate..] |
+--------+----------------------------+-------------+
| Left   |                            | Right       |
| Palette|    React Flow Canvas       | Properties  |
| 220px  |    (flex-1)                | Panel 320px |
|        |                            |             |
|        |                            |             |
|        |                            |             |
+--------+----------------------------+-------------+
|  Error Panel (collapsible, 200px max)             |
+--------------------------------------------------+
```

#### Top Toolbar

- Back arrow button (navigates to `/templates`)
- Template name (editable inline or via properties)
- Unsaved changes indicator: amber dot next to name
- Spacer
- "Save Template" button (secondary variant, floppy disk icon)
- "Validate & Install" button (primary variant, shield-check icon)
- Undo button (arrow-left icon, disabled when nothing to undo)
- Redo button (arrow-right icon, disabled when nothing to redo)
- Auto-layout button (layout-grid icon, tooltip "Auto-arrange nodes")

#### Left Sidebar (Node Palette)

- Collapsible (toggle button at top)
- Section header: "Activities"
- Draggable items with icon + label:
  - Play icon + "Start" (green accent)
  - User icon + "Manual" (blue accent)
  - Zap icon + "Auto" (orange accent)
  - Square icon + "End" (red accent)
- Each item: 44px height, icon left, label right
- Collapsed mode: icons only, 48px width, tooltip on hover
- Drag cursor: `grabbing`; drop on canvas creates node

#### Right Sidebar (Properties Panel)

**When node selected:**
- Section: "Activity Properties"
- Name input field
- Activity type (read-only badge)
- Description textarea
- Performer assignment section (Manual nodes only):
  - Type dropdown: Supervisor, User, Group, Sequential, Runtime Selection
  - Dynamic second field based on type:
    - User: searchable user picker (`command` component)
    - Group: searchable group picker (`command` component)
    - Sequential: ordered list with drag-to-reorder, add/remove buttons
    - Supervisor/Runtime: no second field needed
- Trigger type dropdown: AND-join, OR-join (nodes with 2+ incoming flows only)
- Routing type dropdown: Conditional, Performer Chosen, Broadcast (nodes with 2+ outgoing flows only)
- Method name input (Auto nodes only)

**When edge selected:**
- Section: "Flow Properties"
- Flow type dropdown: Normal, Reject
- Label input field
- Condition expression textarea (shown when parent node has conditional routing)

**When nothing selected:**
- Tabs: "Template" | "Variables"
- Template tab: Name input, Description textarea
- Variables tab:
  - List of existing variables with name, type badge, delete button
  - "Add Variable" button
  - Variable form: name input, type select (string/int/boolean/date), default value input

#### Bottom Error Panel

- Collapsed by default (only header visible: "Errors (0)")
- Expands on validation with errors
- Header: "Errors ({count})" with collapse/expand chevron
- Scrollable list of error items:
  - Red circle-x icon + error message text
  - Click anywhere on row to pan canvas to the problem node
- When validation passes: green check icon + "Validation passed" in header

#### Canvas (React Flow)

- Background: dot grid pattern (`--muted` color dots)
- Zoom controls: bottom-left (zoom in, zoom out, fit view)
- Minimap: bottom-right corner, 200x150px
- Snap-to-grid: 20px grid
- Connection line style: animated dashed while dragging
- Default edge routing: `smoothstep` (built-in React Flow edge type)

### Custom React Flow Node Components (4 types)

#### StartNode
- Shape: circle, 60px diameter
- Background: `bg-green-500`, border: 2px `border-green-600`
- Content: Play icon (Lucide `play`), white, centered
- Label below circle: node name, `text-sm`
- Single source handle at right (or bottom)

#### EndNode
- Shape: filled circle, 60px diameter
- Background: `bg-red-500`, border: 2px `border-red-600`
- Content: Square icon (Lucide `square`), white, centered
- Label below circle: node name, `text-sm`
- Single target handle at left (or top)

#### ManualNode
- Shape: rounded rectangle, min-width 160px, min-height 64px
- Background: `bg-blue-500`, border: 2px `border-blue-600`, `rounded-lg`
- Content: white text, name top line (`font-semibold text-sm`), config hint bottom line (`text-sm opacity-70`), e.g. "Assigned to: John" or "Group: Reviewers"
- Target handle at left, source handle at right

#### AutoNode
- Shape: hexagon (CSS clip-path), min-width 160px, min-height 64px
- Background: `bg-orange-500`, border: 2px `border-orange-600`
- Content: white text, name top line (`font-semibold text-sm`), method hint bottom line (`text-sm opacity-70`), e.g. "Method: send_email"
- Target handle at left, source handle at right

### Custom Edge Components (3 types)

#### NormalEdge
- Stroke: `#374151` (gray-700), 2px width
- Style: solid line
- Marker: arrow at target end
- Label: display_label if set, on white background pill

#### RejectEdge
- Stroke: `#ef4444` (red-500), 2px width
- Style: dashed (`strokeDasharray: "8 4"`)
- Marker: arrow at target end
- Label: "Reject" default or display_label, red text on white background pill

#### ConditionalEdge
- Stroke: `#3b82f6` (blue-500), 2px width
- Style: dotted (`strokeDasharray: "2 4"`)
- Marker: diamond at source end, arrow at target end
- Label: condition expression preview (truncated to 20 chars) or display_label

## 7. Interaction Contracts

### Drag-and-Drop (Node Creation)

1. User grabs palette item in left sidebar
2. Cursor changes to `grabbing`
3. Ghost element follows cursor over canvas
4. Drop on canvas: node appears at drop position, snapped to grid
5. Node immediately selected, properties panel opens
6. Unsaved changes indicator activates

### Edge Creation

1. User hovers over node source handle (handle glows / grows slightly)
2. User drags from source handle
3. Animated dashed connection line follows cursor
4. Hover over valid target handle: handle highlights green
5. Release on target: edge created with default type (Normal)
6. Edge selected, properties panel shows flow properties
7. Release not on target: connection cancelled, no edge created

### Node Selection

1. Click node: selected (blue ring via `--primary`), properties panel shows node props
2. Click canvas background: deselect all, properties panel shows template-level tabs
3. Shift+click: toggle node in/out of multi-selection
4. Rubber-band drag on canvas background: selects all nodes/edges in rectangle
5. Multi-select: properties panel shows "N elements selected" with bulk delete option

### Context Menu (Right-Click)

| Target | Menu Items |
|--------|-----------|
| Node | "Delete" (with red text) |
| Edge | "Delete" (with red text) |
| Canvas | "Select All", "Auto-Layout", "Fit View" |

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+S` | Save template |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` / `Ctrl+Shift+Z` | Redo |
| `Delete` / `Backspace` | Delete selected elements |
| `Ctrl+A` | Select all nodes and edges |
| `Escape` | Deselect all |

### Save Flow

1. User presses Ctrl+S or clicks "Save Template"
2. Button shows loading spinner
3. Canvas state (nodes with positions, edges, properties) serialized to API format
4. PUT request to `/api/v1/templates/{id}` + activity/flow/variable endpoints
5. Success: toast "Template saved", unsaved indicator clears
6. Failure: toast with error message and retry action

### Validate & Install Flow

1. User clicks "Validate & Install"
2. Button shows loading spinner
3. POST to `/api/v1/templates/{id}/validate`
4. If valid: POST to `/api/v1/templates/{id}/install`, toast "Template installed successfully", template state badge updates to "Active"
5. If invalid: error panel expands, invalid nodes get red ring + error badge, toast "{N} validation errors found"
6. User clicks error in panel: canvas pans/zooms to center on the problem node, node flashes border 3 times

### Template Load Flow

1. Navigate to `/templates/:id/edit`
2. Show skeleton layout (toolbar, empty sidebar placeholders, canvas loading spinner)
3. GET `/api/v1/templates/{id}/detail` (returns activities, flows, variables)
4. Map activities to React Flow nodes (using `position_x`, `position_y`)
5. Map flows to React Flow edges (using `source_activity_id`, `target_activity_id`)
6. If template has no position data: run auto-layout on load
7. Canvas renders, loading state clears

## 8. Loading & Skeleton States

### Template List Loading
- 3 skeleton cards in a column, each: 80px height, animated shimmer
- Skeleton card shows: title bar (40% width shimmer), description bar (70% width shimmer), footer bar (30% width shimmer)

### Designer Canvas Loading
- Left sidebar: 4 skeleton rectangles (44px height each)
- Canvas area: centered spinner with "Loading template..." text below
- Right sidebar: hidden until load completes

### Save/Action Loading
- Button text replaced with spinner (16px) + "Saving..." text
- Button disabled during save
- All other toolbar buttons remain enabled

## 9. Responsive Behavior

This is a desktop-first application (workflow design requires large canvas). Minimum supported viewport: 1024px width.

| Breakpoint | Behavior |
|------------|----------|
| >= 1280px | Full layout: left sidebar expanded + canvas + right properties panel |
| 1024-1279px | Left sidebar collapsed to icons by default, right panel overlays canvas |
| < 1024px | Warning banner: "Workflow designer requires a larger screen" with link back to template list |

## 10. Accessibility

- All interactive elements have visible focus rings (shadcn default: `ring-ring`)
- Toolbar buttons have `aria-label` with action description
- Palette drag items have `role="button"` with `aria-label="Drag to add {type} activity"`
- Properties panel form fields have associated `<label>` elements
- Color is never the sole indicator: node shapes differ by type (circle, rectangle, hexagon, filled circle)
- Keyboard navigation: Tab through toolbar, properties panel fields. Canvas itself uses React Flow's built-in keyboard support
- Error panel items have `role="listitem"` with descriptive text
- Toast notifications use `role="status"` (via sonner defaults)
- Minimum contrast ratio: 4.5:1 for text on colored node backgrounds (white text on green/blue/orange/red all pass)

## 11. State Management

### Zustand Stores

| Store | State | Purpose |
|-------|-------|---------|
| `useDesignerStore` | `nodes`, `edges`, `selectedNodeId`, `selectedEdgeId`, `isDirty`, `undoStack`, `redoStack` | Canvas state, selection, undo/redo history |
| `useAuthStore` | `token`, `user`, `isAuthenticated` | JWT token and current user info |
| `uiStore` | `leftSidebarCollapsed`, `rightPanelOpen`, `errorPanelExpanded` | Panel visibility toggles |

### TanStack Query Keys

| Key | Endpoint | Stale Time |
|-----|----------|------------|
| `["templates"]` | GET `/api/v1/templates` | 30 seconds |
| `["templates", id]` | GET `/api/v1/templates/{id}` | 30 seconds |
| `["templates", id, "detail"]` | GET `/api/v1/templates/{id}/detail` | 30 seconds |
| `["users"]` | GET `/api/v1/users` | 5 minutes |
| `["groups"]` | GET `/api/v1/groups` | 5 minutes |

## 12. Data Mapping: API to Canvas

### Activity to React Flow Node

```
ActivityTemplateResponse -> Node {
  id: activity.id (string),
  type: map activity.activity_type to "startNode" | "manualNode" | "autoNode" | "endNode",
  position: { x: activity.position_x ?? 0, y: activity.position_y ?? 0 },
  data: {
    name: activity.name,
    description: activity.description,
    activityType: activity.activity_type,
    performerType: activity.performer_type,
    performerId: activity.performer_id,
    triggerType: activity.trigger_type,
    methodName: activity.method_name,
    routingType: activity.routing_type,
    performerList: activity.performer_list,
  }
}
```

### Flow to React Flow Edge

```
FlowTemplateResponse -> Edge {
  id: flow.id (string),
  source: flow.source_activity_id (string),
  target: flow.target_activity_id (string),
  type: map flow.flow_type to "normalEdge" | "rejectEdge",
       + if flow.condition_expression then "conditionalEdge",
  data: {
    flowType: flow.flow_type,
    conditionExpression: flow.condition_expression,
    displayLabel: flow.display_label,
  }
}
```

---

*Generated: 2026-04-04*
*Revised: 2026-04-04 — Fixed typography scale (removed text-xs), spacing scale (removed 12px), CTA copywriting (Save -> Save Template)*
*Source: CONTEXT.md (D-01 through D-21), REQUIREMENTS.md (DESIGN-01 through DESIGN-07), CLAUDE.md tech stack*
