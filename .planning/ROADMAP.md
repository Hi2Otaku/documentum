# Roadmap: Documentum Workflow Clone - v1.1 Full Frontend Experience

## Overview

This roadmap delivers the full frontend experience for the Documentum Workflow Clone in 4 phases (12-15), continuing from v1.0's Phase 11. Every backend API already exists -- this milestone makes all capabilities accessible through the web UI so users never need Swagger or curl. It starts with navigation scaffolding that connects all pages, then builds the Inbox (the primary daily-use surface), followed by Document Management and Workflow Operations. Each phase delivers a complete, usable UI feature area.

## Phases

**Phase Numbering:**
- Continues from v1.0 (Phases 1-11 complete)
- Integer phases (12, 13, 14, 15): Planned milestone work
- Decimal phases (12.1, 12.2): Urgent insertions if needed

- [x] **Phase 12: Navigation & App Shell** - Persistent sidebar, page routing, active state indicators, role-based visibility, and user menu (completed 2026-04-06)
- [x] **Phase 13: Inbox & Work Items** - Work item list with filtering, detail view, complete/reject actions, delegation, availability toggle, and work queue browsing (completed 2026-04-06)
- [x] **Phase 14: Document Management** - Document upload, browsing with filters, version history, check-in/check-out, and lifecycle state transitions (completed 2026-04-06)
- [ ] **Phase 15: Workflow Operations** - Start workflow wizard, instance list with monitoring, admin controls, and read-only React Flow progress view

## Phase Details

### Phase 12: Navigation & App Shell
**Goal**: Users can move between all application pages through a consistent sidebar, with the UI respecting role-based access
**Depends on**: Nothing (first phase of v1.1; existing pages already render independently)
**Requirements**: NAV-01, NAV-02, NAV-03, NAV-04
**Success Criteria** (what must be TRUE):
  1. User can click sidebar links to navigate between Templates, Inbox, Documents, Workflows, Dashboard, and Query pages without full page reloads
  2. The currently active page is visually highlighted in the sidebar so the user always knows where they are
  3. Non-admin users do not see Dashboard or Query links in the sidebar; admin users see all links
  4. User can see their username in a user menu, toggle their availability status, and log out -- all from any page
**Plans**: 2 plans
Plans:
- [x] 12-01-PLAN.md — Auth foundation, AdminRoute, placeholder pages, shadcn components
- [x] 12-02-PLAN.md — Sidebar UI components, AppShell rewrite, route wiring
**UI hint**: yes

### Phase 13: Inbox & Work Items
**Goal**: Users can manage their daily workflow tasks entirely from the Inbox page -- viewing, acting on, delegating, and claiming work items
**Depends on**: Phase 12 (navigation provides the app shell and routing)
**Requirements**: INB-01, INB-02, INB-03, INB-04, INB-05, INB-06
**Success Criteria** (what must be TRUE):
  1. User can view their pending work items in a paginated table with columns for task name, workflow, priority, and due date, and can filter by state
  2. User can click a work item to see its full details including activity information, parent workflow context, and comment history
  3. User can acquire an unassigned item, complete a task (advancing the workflow), or reject it back to a previous activity -- each with an optional comment
  4. User can delegate a specific work item to another user, and can set themselves as unavailable so all future tasks auto-route to their delegate
  5. User can switch to a Work Queues tab, browse shared task pools, and claim a task from a queue for themselves
**Plans**: 3 plans
Plans:
- [x] 13-01-PLAN.md — API modules, TypeScript types, shared components (badge, priority icon, empty state, textarea)
- [x] 13-02-PLAN.md — InboxPage split-pane layout, InboxTable with filtering/pagination, InboxDetailPanel with comments
- [x] 13-03-PLAN.md — Complete/Reject/Delegate dialogs, Queues tab with queue list and details
**UI hint**: yes

### Phase 14: Document Management
**Goal**: Users can manage the full document lifecycle through the UI -- uploading, browsing, versioning, locking, and transitioning states
**Depends on**: Phase 12 (navigation provides the app shell and routing)
**Requirements**: DOC-01, DOC-02, DOC-03, DOC-04, DOC-05
**Success Criteria** (what must be TRUE):
  1. User can upload a document via drag-and-drop or file picker and see it appear in the document list
  2. User can browse documents in a paginated table with filters for title, author, and lifecycle state
  3. User can open a document's version history panel and download any specific version
  4. User can check out a document (locking it from others), then check in a new version -- with the lock indicator visible to all users
  5. User can transition a document through lifecycle states (Draft, Review, Approved, Archived) with a confirmation dialog
**Plans**: 3 plans
Plans:
- [x] 14-01-PLAN.md — API module, TypeScript types, shared components (LifecycleStateBadge, LockIndicator, Progress)
- [x] 14-02-PLAN.md — DocumentsPage with drop zone upload, DocumentTable with filters/pagination, split-pane layout
- [x] 14-03-PLAN.md — DocumentDetailPanel, version history, checkout/checkin dialogs, lifecycle transitions
**UI hint**: yes

### Phase 15: Workflow Operations
**Goal**: Users can start new workflows and monitor running instances, with admins able to control workflow execution from the UI
**Depends on**: Phase 12 (navigation), Phase 14 (document attachment during workflow start)
**Requirements**: WF-01, WF-02, WF-03, WF-04
**Success Criteria** (what must be TRUE):
  1. User can start a workflow by picking a template from a list, attaching documents, setting initial variable values, and launching it
  2. User can view running workflow instances in a paginated list with filters for template, state, and date range
  3. Admin can halt, resume, or terminate a workflow instance directly from the instance list or detail view
  4. User can view a workflow's current progress on a read-only React Flow graph where completed activities are visually distinct from active and pending ones
**Plans**: 3 plans
Plans:
- [x] 15-01-PLAN.md — API module, TypeScript types, shared components (WorkflowStateBadge, EmptyState), install Checkbox/Switch
- [ ] 15-02-PLAN.md — WorkflowsPage split-pane layout, WorkflowTable with filters/pagination, WorkflowDetailPanel with admin actions
- [ ] 15-03-PLAN.md — Start Workflow wizard dialog (4 steps) and read-only React Flow progress graph
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 12 -> 13 -> 14 -> 15

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 12. Navigation & App Shell | 2/2 | Complete    | 2026-04-06 |
| 13. Inbox & Work Items | 3/3 | Complete    | 2026-04-06 |
| 14. Document Management | 3/3 | Complete    | 2026-04-06 |
| 15. Workflow Operations | 1/3 | In Progress|  |
