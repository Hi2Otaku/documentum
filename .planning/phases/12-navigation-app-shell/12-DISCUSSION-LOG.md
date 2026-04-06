# Phase 12: Navigation & App Shell - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-06
**Phase:** 12-navigation-app-shell
**Areas discussed:** Sidebar layout, User menu design, Role-based visibility

---

## Sidebar Layout

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed sidebar + no top bar | Full left sidebar, replace top bar entirely | |
| Collapsible sidebar | Toggle between icon+text and icon-only | ✓ |
| Sidebar + slim top bar | Left sidebar for nav + slim top bar for breadcrumbs | |

**User's choice:** Collapsible sidebar
**Notes:** Preview-based selection, user chose the expand/collapse toggle pattern

---

### Sidebar Default State

| Option | Description | Selected |
|--------|-------------|----------|
| Expanded by default | New users see full labels | |
| Collapsed by default | Clean, minimal start | ✓ |
| You decide | Claude picks | |

**User's choice:** Collapsed by default
**Notes:** More space for workflow designer

---

### Toggle Mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Toggle button in sidebar | Hamburger/chevron button | |
| Hover to expand | Expand on mouse hover | |
| Both | Toggle button to lock + hover-to-peek | ✓ |

**User's choice:** Both
**Notes:** None

---

### Branding

| Option | Description | Selected |
|--------|-------------|----------|
| "Documentum" text | Simple text, truncates to "D" | |
| Icon + text | Workflow icon next to "Documentum" | ✓ |
| You decide | Claude picks | |

**User's choice:** Icon + text
**Notes:** None

---

### Icons

| Option | Description | Selected |
|--------|-------------|----------|
| Lucide icons | Consistent with shadcn/ui | ✓ |
| You decide | Claude picks | |

**User's choice:** Lucide icons
**Notes:** None

---

### Section Grouping

| Option | Description | Selected |
|--------|-------------|----------|
| No grouping | Flat list of 6 links | |
| Group by role | Main vs Admin with divider | ✓ |
| You decide | Claude decides | |

**User's choice:** Group by role
**Notes:** None

---

### Color Scheme

| Option | Description | Selected |
|--------|-------------|----------|
| Dark sidebar | Dark bg with light text | |
| Light sidebar | Same light theme as content | |
| You decide | Claude picks | ✓ |

**User's choice:** You decide (Claude's discretion)
**Notes:** None

---

### Active Page Indicator

| Option | Description | Selected |
|--------|-------------|----------|
| Background highlight | Filled background color | |
| Left border accent | Colored left border bar | |
| Both | Left accent + subtle background | ✓ |

**User's choice:** Both
**Notes:** None

---

## User Menu Design

### Placement

| Option | Description | Selected |
|--------|-------------|----------|
| Bottom of sidebar | Pinned to bottom | |
| Top of sidebar | Under logo | ✓ |
| You decide | Claude picks | |

**User's choice:** Top of sidebar
**Notes:** None

---

### Availability Toggle

| Option | Description | Selected |
|--------|-------------|----------|
| Status dot + dropdown | Green/red dot, dropdown to toggle | ✓ |
| Toggle switch in menu | Labeled toggle in dropdown | |
| You decide | Claude picks | |

**User's choice:** Status dot + dropdown
**Notes:** None

---

## Role-Based Visibility

### Unauthorized Access

| Option | Description | Selected |
|--------|-------------|----------|
| Redirect to inbox | Silent redirect for non-admins | ✓ |
| Show 403 page | Access denied message | |
| You decide | Claude picks | |

**User's choice:** Redirect to inbox
**Notes:** None

---

### Admin Indicator

| Option | Description | Selected |
|--------|-------------|----------|
| No indicator | Status only affects visibility | |
| Subtle badge | Small "Admin" badge next to username | ✓ |
| You decide | Claude decides | |

**User's choice:** Subtle badge
**Notes:** None

---

## Claude's Discretion

- Sidebar color scheme
- Exact Lucide icon choices per nav item
- Hover-to-peek animation timing
- Mobile/responsive sidebar behavior

## Deferred Ideas

None
