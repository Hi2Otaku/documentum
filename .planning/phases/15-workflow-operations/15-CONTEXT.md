# Phase 15: Workflow Operations - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the Workflows page where users start new workflows via a multi-step wizard, monitor running instances in a split-pane layout, view visual progress on a read-only React Flow graph, and admins can halt/resume/terminate instances. This is the final phase of v1.1.

</domain>

<decisions>
## Implementation Decisions

### Start Workflow Wizard
- **D-01:** Multi-step dialog wizard: Step 1 (select template) → Step 2 (attach documents) → Step 3 (set variables) → Step 4 (review & launch).
- **D-02:** Step navigation with Next/Back buttons. Launch button on final step.
- **D-03:** Document attachment step reuses the document picker pattern — list available documents with checkboxes.
- **D-04:** Variables step renders input fields based on the template's process variables (type-appropriate: text, number, boolean toggle).

### Instance Monitoring
- **D-05:** Split-pane layout (consistent with Inbox/Documents) — instance table on left, detail panel on right.
- **D-06:** Regular users see only workflows they started. Admins see all instances (use admin list endpoint).
- **D-07:** Table columns: workflow name, template name, state badge, started by, started date. Filterable by template, state, date range.

### Visual Progress Graph
- **D-08:** Read-only React Flow graph embedded in the detail panel. Reuse existing node components from the designer (StartNode, ManualNode, AutoNode, EndNode) in read-only mode.
- **D-09:** Activity state colors: Green = completed, Blue = active/in-progress, Gray = pending/dormant. Applied as border or background color on nodes.
- **D-10:** Graph supports zoom/pan but no editing. Auto-layout using dagre (already used in the designer).

### Admin Controls
- **D-11:** Admin action buttons (Halt, Resume, Terminate) appear in the detail panel header only. Not visible to non-admin users.
- **D-12:** Terminate requires a double-confirmation dialog with destructive styling: "This cannot be undone. All pending work items will be cancelled."
- **D-13:** Halt and Resume are single-click with toast confirmation (reversible actions, no dialog needed).

### Claude's Discretion
- Empty state for no workflow instances
- Detail panel when no instance selected
- Loading skeleton pattern
- Start Workflow button placement (toolbar or FAB)
- React Flow graph height in the detail panel
- State badge colors for workflow states (RUNNING, HALTED, FINISHED, FAILED, DORMANT)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Backend APIs
- `src/app/routers/workflows.py` — Workflow endpoints (start, list, admin list, detail, halt, resume, terminate, variables)
- `src/app/schemas/workflow.py` — WorkflowStartRequest, WorkflowInstanceResponse, etc.
- `src/app/services/engine_service.py` — start_workflow, advance logic
- `src/app/routers/templates.py` — Template list for wizard step 1

### Frontend — React Flow (existing)
- `frontend/src/components/nodes/` — StartNode, ManualNode, AutoNode, EndNode (reuse in read-only mode)
- `frontend/src/components/edges/` — NormalEdge, ConditionalEdge, RejectEdge
- `frontend/src/hooks/useAutoLayout.ts` — dagre auto-layout hook
- `frontend/src/stores/designerStore.ts` — Existing React Flow store (reference, don't reuse — create read-only variant)

### Frontend Patterns
- `frontend/src/pages/InboxPage.tsx` — Split-pane layout pattern
- `frontend/src/pages/DocumentsPage.tsx` — Split-pane with table + detail
- `frontend/src/pages/WorkflowsPage.tsx` — Placeholder to replace
- `frontend/src/api/documents.ts` — API module pattern
- `frontend/src/components/inbox/InboxTable.tsx` — TanStack Table pattern

### UI Components Available
- All shadcn components from prior phases
- React Flow (@xyflow/react) already installed
- sonner for toasts

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- React Flow node components (StartNode, ManualNode, AutoNode, EndNode) — adapt for read-only progress view
- dagre auto-layout hook — reuse for progress graph
- Split-pane layout from InboxPage/DocumentsPage
- TanStack Table pattern from InboxTable/DocumentTable
- sonner toasts, shadcn dialogs, badge components

### Established Patterns
- TanStack Query for data fetching
- shadcn Dialog for multi-step wizard
- State badges with color coding
- Admin-only visibility via authStore.isSuperuser

### Integration Points
- WorkflowsPage.tsx at /workflows (already routed)
- authStore provides userId (for "my instances" filter) and isSuperuser (for admin controls)
- Templates API for wizard step 1
- Documents API for wizard step 2 (document attachment)

</code_context>

<specifics>
## Specific Ideas

- The React Flow progress graph should reuse the exact same node components from the designer but strip out all editing interactions (no drag, no handles, no right-click menu). Just visual display with state-colored borders.
- The multi-step wizard should be a single shadcn Dialog with internal step state — not separate dialogs per step.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 15-workflow-operations*
*Context gathered: 2026-04-06*
