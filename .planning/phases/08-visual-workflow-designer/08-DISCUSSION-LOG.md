# Phase 8: Visual Workflow Designer - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-04
**Phase:** 08-visual-workflow-designer
**Areas discussed:** Canvas & node interaction, Properties panel & forms, Template save/load & validation UX, App shell & project setup

---

## Canvas & Node Interaction

### How should users add activity nodes to the canvas?

| Option | Description | Selected |
|--------|-------------|----------|
| Drag from sidebar palette | Left sidebar with draggable node types. Familiar pattern from Figma, draw.io. Always visible. | ✓ |
| Top toolbar with click-to-place | Toolbar buttons at top. Click type, then click canvas to place. | |
| Right-click context menu | Right-click on canvas for menu. Minimalist, power-user friendly. | |

**User's choice:** Drag from sidebar palette
**Notes:** None

### How should different node types look on the canvas?

| Option | Description | Selected |
|--------|-------------|----------|
| Distinct shapes per type | Start=circle, End=filled circle, Manual=rounded rect, Auto=hexagon. Color-coded. | ✓ |
| Uniform cards with icon badges | Same-shaped cards with small icon/badge indicating type. | |

**User's choice:** Distinct shapes per type
**Notes:** None

### How should flow connections (edges) be styled?

| Option | Description | Selected |
|--------|-------------|----------|
| Color-coded edges | Normal=solid dark, Reject=dashed red, Conditional=dotted blue with diamond. | ✓ |
| Labels only | All edges look the same with text labels. | |

**User's choice:** Color-coded edges
**Notes:** None

### Which canvas features should be included?

| Option | Description | Selected |
|--------|-------------|----------|
| Minimap | Small overview in corner. | ✓ |
| Snap-to-grid | Nodes snap to alignment grid. | ✓ |
| Auto-layout button | One-click auto-arrange using dagre/elkjs. | ✓ |
| Undo/redo | Ctrl+Z / Ctrl+Y for canvas operations. | ✓ |

**User's choice:** All four features selected
**Notes:** Multi-select question — user selected all options

### How should users delete nodes and edges?

| Option | Description | Selected |
|--------|-------------|----------|
| Select + Delete/Backspace key | Standard keyboard delete pattern. | |
| Right-click context menu | Safer, less accidental deletion. | |
| Both | Support both keyboard and context menu. | ✓ |

**User's choice:** Both
**Notes:** None

### Multi-select and group operations?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — rubber-band + Shift-click | Drag selection rectangle, Shift+click toggle. Group move/delete. | ✓ |
| Single select only | One node at a time. | |

**User's choice:** Yes — rubber-band + Shift-click
**Notes:** None

### How should connecting nodes work?

| Option | Description | Selected |
|--------|-------------|----------|
| Drag from handle to handle | React Flow's built-in source/target handle pattern. | ✓ |
| Select two nodes then click 'Connect' | More explicit but slower. | |

**User's choice:** Drag from handle to handle
**Notes:** None

### Palette sidebar collapsible or always visible?

| Option | Description | Selected |
|--------|-------------|----------|
| Collapsible | Toggle button to collapse/hide. Maximizes canvas space. | ✓ |
| Always visible | Stays open at all times. | |

**User's choice:** Collapsible
**Notes:** None

### Should nodes show config summary on canvas?

| Option | Description | Selected |
|--------|-------------|----------|
| Name + type badge only | Clean, readable. Full config in panel. | |
| Name + key config hints | Shows performer, trigger type on node. More info at a glance. | ✓ |

**User's choice:** Name + key config hints
**Notes:** None

---

## Properties Panel & Forms

### Where should the properties panel appear?

| Option | Description | Selected |
|--------|-------------|----------|
| Right sidebar | Fixed-width panel slides in from right. Standard pattern. | ✓ |
| Bottom drawer | Wider horizontal space but reduces canvas height. | |
| Modal dialog | Double-click opens modal. Clean canvas but breaks flow. | |

**User's choice:** Right sidebar
**Notes:** None

### What should happen when clicking a flow (edge)?

| Option | Description | Selected |
|--------|-------------|----------|
| Same properties panel | Edge-specific fields in the same right panel. | ✓ |
| Inline popover on the edge | Small popover near edge. Lighter weight. | |

**User's choice:** Same properties panel
**Notes:** None

### How should performer assignment form work?

| Option | Description | Selected |
|--------|-------------|----------|
| Type dropdown + dynamic field | Dropdown for type, second field changes based on type. | ✓ |
| Unified user/group search | Single search across users and groups. | |

**User's choice:** Type dropdown + dynamic field
**Notes:** None

### Where should users define process variables?

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated tab in properties panel | Template-level settings with Variables tab. | ✓ |
| Separate variables dialog | Toolbar button opens full-screen modal. | |

**User's choice:** Dedicated tab in properties panel
**Notes:** None

---

## Template Save/Load & Validation UX

### How should template saving work?

| Option | Description | Selected |
|--------|-------------|----------|
| Manual save with Ctrl+S | Explicit save, unsaved changes indicator. | ✓ |
| Auto-save with debounce | Changes auto-save after inactivity. | |
| Manual save + local auto-draft | Auto-save to localStorage, manual to backend. | |

**User's choice:** Manual save with Ctrl+S
**Notes:** None

### How should validation errors appear?

| Option | Description | Selected |
|--------|-------------|----------|
| Inline markers + error panel | Red border on invalid nodes, clickable error list at bottom. | ✓ |
| Toast notifications only | Errors as toasts that disappear. | |
| Block install with dialog | Errors only shown in modal at install time. | |

**User's choice:** Inline markers + error panel
**Notes:** None

### Should the designer include a template list page?

| Option | Description | Selected |
|--------|-------------|----------|
| Template list + canvas | List page with all templates. Click to edit. | ✓ |
| Canvas only | Templates loaded via URL or dropdown. | |

**User's choice:** Template list + canvas
**Notes:** None

### Should Install be in the designer or separate?

| Option | Description | Selected |
|--------|-------------|----------|
| In designer toolbar | "Validate & Install" button. One-click workflow. | ✓ |
| Separate from designer | Install only from list page. | |

**User's choice:** In designer toolbar
**Notes:** None

---

## App Shell & Project Setup

### Where should the frontend project live?

| Option | Description | Selected |
|--------|-------------|----------|
| frontend/ directory in this repo | Monorepo approach. One Docker Compose. | ✓ |
| Separate repo | Own git repository. | |

**User's choice:** frontend/ in this repo
**Notes:** None

### How much app shell in Phase 8?

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal — just designer pages | Login, template list, designer canvas. Simple top nav. | ✓ |
| Full navigation shell | Complete sidebar with placeholders for all sections. | |

**User's choice:** Minimal — just designer pages
**Notes:** None

### How should authentication work?

| Option | Description | Selected |
|--------|-------------|----------|
| Login form with JWT | Username/password form, JWT stored, protected routes. | ✓ |
| Dev-mode hardcoded token | Skip login, hardcode admin JWT. | |
| Token input field | Paste JWT token manually. | |

**User's choice:** Login form with JWT
**Notes:** None

### Should frontend be in Docker Compose?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — as a dev service | Vite dev server in Docker. Full stack with one command. | ✓ |
| Run separately | npm run dev outside Docker. | |
| You decide | Claude picks during implementation. | |

**User's choice:** Yes — as a dev service
**Notes:** None

---

## Claude's Discretion

- Loading skeleton and spinner designs
- Exact spacing, typography, and color palette (within shadcn/ui defaults)
- React Flow configuration details (edge routing algorithm, handle positions)
- API client structure (axios vs fetch, error handling patterns)
- Zustand store organization
- Auto-layout algorithm choice (dagre vs elkjs)
- CORS origin configuration details
- Undo/redo implementation approach (command pattern vs state snapshots)

## Deferred Ideas

None — discussion stayed within phase scope.
