# Phase 15: Workflow Operations - Research

**Researched:** 2026-04-06
**Domain:** React frontend -- workflow lifecycle UI (start wizard, instance monitoring, progress graph, admin controls)
**Confidence:** HIGH

## Summary

Phase 15 is a frontend-only phase that builds the Workflows page -- the final page for v1.1. All backend APIs already exist and are well-documented. The phase involves four distinct UI concerns: (1) a multi-step wizard dialog for starting workflows, (2) a split-pane instance list with filtering and pagination, (3) admin action controls (halt/resume/terminate), and (4) a read-only React Flow progress graph showing activity states.

The technical risk is low. Every pattern needed has been established in prior phases (split-pane layout from InboxPage/DocumentsPage, TanStack Table from InboxTable/DocumentTable, TanStack Query mutations, shadcn dialogs, React Flow from the designer). The one novel element is rendering React Flow nodes with dynamic state-colored borders in read-only mode, which requires wrapping existing node components. Two new shadcn components (Checkbox, Switch) must be installed.

**Primary recommendation:** Structure this as 3-4 plans: (1) API module + types, (2) split-pane layout with table and detail panel, (3) start workflow wizard, (4) progress graph. The wizard and progress graph are the most complex and should be separate plans.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Multi-step dialog wizard: Step 1 (select template) -> Step 2 (attach documents) -> Step 3 (set variables) -> Step 4 (review & launch).
- **D-02:** Step navigation with Next/Back buttons. Launch button on final step.
- **D-03:** Document attachment step reuses the document picker pattern -- list available documents with checkboxes.
- **D-04:** Variables step renders input fields based on the template's process variables (type-appropriate: text, number, boolean toggle).
- **D-05:** Split-pane layout (consistent with Inbox/Documents) -- instance table on left, detail panel on right.
- **D-06:** Regular users see only workflows they started. Admins see all instances (use admin list endpoint).
- **D-07:** Table columns: workflow name, template name, state badge, started by, started date. Filterable by template, state, date range.
- **D-08:** Read-only React Flow graph embedded in the detail panel. Reuse existing node components from the designer (StartNode, ManualNode, AutoNode, EndNode) in read-only mode.
- **D-09:** Activity state colors: Green = completed, Blue = active/in-progress, Gray = pending/dormant. Applied as border or background color on nodes.
- **D-10:** Graph supports zoom/pan but no editing. Auto-layout using dagre (already used in the designer).
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

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| WF-01 | User can start a workflow by selecting a template, attaching documents, setting initial variables, and launching | StartWorkflowDialog wizard (D-01 to D-04). API: `POST /api/workflows` with WorkflowStartRequest. Templates from `GET /api/v1/templates/`, documents from `GET /api/documents/`, variables from template detail. |
| WF-02 | User can view running workflow instances in a filterable, paginated list with state indicators | WorkflowTable with TanStack Table. Regular users: `GET /api/workflows` (all instances, filter client-side by supervisor_id). Admins: `GET /api/workflows/admin/list` with server-side filters. |
| WF-03 | Admin can halt, resume, or terminate a workflow instance from the UI | AdminActionBar in detail panel. Endpoints: `POST /api/workflows/{id}/halt`, `/resume`, `/abort`. Terminate uses double-confirmation dialog. |
| WF-04 | User can view a workflow's progress on a read-only React Flow graph showing the current position | WorkflowProgressGraph. Requires two API calls: workflow detail (for activity instance states) + template detail (for graph structure). Dagre auto-layout. State-colored node borders. |
</phase_requirements>

## Standard Stack

### Core (Already Installed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| @xyflow/react | 12.10.x | Read-only progress graph | Already in use for workflow designer. Reuse node/edge components. |
| @tanstack/react-query | 5.96.x | Server state management | All API fetching and cache invalidation. Established pattern. |
| @tanstack/react-table | 8.21.x | Workflow instance table | Headless table with sorting, pagination. Established pattern from InboxTable. |
| @dagrejs/dagre | 3.x | Auto-layout for progress graph | Already used by useAutoLayout hook. |
| shadcn/ui | (copy-paste) | UI components | All needed components except Checkbox and Switch are already installed. |
| sonner | (installed) | Toast notifications | For start/halt/resume/terminate confirmations. |
| zustand | 5.x | Auth store | Only for reading `userId` and `isSuperuser`. No new stores needed. |

### New Components to Install

| Component | Install Command | Purpose |
|-----------|----------------|---------|
| Checkbox | `npx shadcn@latest add checkbox` | Document attachment step (D-03) |
| Switch | `npx shadcn@latest add switch` | Boolean variable toggle (D-04) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Multi-step dialog | Separate full pages | Dialog keeps context, avoids route changes. D-01 locks this as a dialog. |
| Client-side filtering (regular users) | Backend API change | Out of scope per REQUIREMENTS. Client-side is acceptable for MVP. |
| Wrapping node components | Creating new progress-specific nodes | More code duplication. Wrapping preserves visual consistency with designer. |

## Architecture Patterns

### Recommended File Structure

```
frontend/src/
  api/
    workflows.ts           # New: workflow API module (list, detail, start, halt, resume, abort)
  components/
    workflows/
      WorkflowTable.tsx           # TanStack Table for instances
      WorkflowDetailPanel.tsx     # Right-side detail panel with tabs
      WorkflowStateBadge.tsx      # State badge with color coding
      WorkflowEmptyState.tsx      # Empty state when no instances
      WorkflowVariablesList.tsx   # Variables display in detail panel
      StartWorkflowDialog.tsx     # Multi-step wizard dialog
      WizardStepIndicator.tsx     # Step dots + labels
      TemplatePickerStep.tsx      # Step 1: template selection
      DocumentAttachStep.tsx      # Step 2: document attachment
      VariablesStep.tsx           # Step 3: variable inputs
      ReviewStep.tsx              # Step 4: summary + launch
      WorkflowProgressGraph.tsx   # Read-only React Flow graph
      AdminActionBar.tsx          # Halt/Resume/Terminate buttons
      TerminateDialog.tsx         # Double-confirmation destructive dialog
  pages/
    WorkflowsPage.tsx        # Replace existing placeholder
```

### Pattern 1: API Module (Duplicated Per Module)

Per project convention (Phase 14 decision), each page gets its own API module with duplicated `authHeaders()`, `apiFetch()`, and `apiMutate()` helpers.

```typescript
// frontend/src/api/workflows.ts
function authHeaders(): HeadersInit {
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function apiFetch<T>(url: string): Promise<T> { /* same as documents.ts */ }
async function apiMutate<T>(url: string, method: "POST" | "PUT", body?: unknown): Promise<T> { /* same */ }

// Response types defined inline (not shared)
export interface WorkflowInstanceResponse {
  id: string;
  process_template_id: string;
  state: string;
  supervisor_id: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface WorkflowAdminListResponse extends WorkflowInstanceResponse {
  template_name: string | null;
  started_by_username: string | null;
  active_activity_name: string | null;
}

export interface WorkflowDetailResponse extends WorkflowInstanceResponse {
  activity_instances: ActivityInstanceResponse[];
  work_items: WorkItemResponse[];
  process_variables: ProcessVariableResponse[];
}
```

### Pattern 2: Split-Pane Layout (Established)

Direct reuse of InboxPage/DocumentsPage layout pattern:

```typescript
// Same structure as InboxPage.tsx and DocumentsPage.tsx
<div className="flex h-[calc(100vh-theme(spacing.16))]">
  {/* Left: table */}
  <div className="flex-1 min-w-[400px] flex flex-col overflow-hidden">
    <WorkflowTable ... />
  </div>
  {/* Right: detail */}
  <div className="w-[420px] border-l overflow-y-auto hidden lg:block">
    <WorkflowDetailPanel workflowId={selectedWorkflowId} />
  </div>
</div>
```

### Pattern 3: Admin vs Regular User Endpoint Selection

```typescript
// In WorkflowsPage.tsx
const isSuperuser = useAuthStore((s) => s.isSuperuser);
const userId = useAuthStore((s) => s.userId);

const { data } = useQuery({
  queryKey: ["workflows", { page: currentPage, state: stateFilter, templateId: templateFilter }],
  queryFn: () =>
    isSuperuser
      ? fetchWorkflowsAdmin({ skip, limit, state, template_id })
      : fetchWorkflows({ skip, limit }),
});

// For regular users, client-side filter by supervisor_id
const workflows = isSuperuser
  ? data?.data ?? []
  : (data?.data ?? []).filter((w) => w.supervisor_id === userId);
```

### Pattern 4: Progress Graph Data Merging

The progress graph requires merging two data sources:

```typescript
// 1. Workflow detail gives activity instance STATES
const { data: workflow } = useQuery({
  queryKey: ["workflows", workflowId],
  queryFn: () => fetchWorkflowDetail(workflowId),
});

// 2. Template detail gives graph STRUCTURE (activities with positions/types, flows as edges)
const { data: template } = useQuery({
  queryKey: ["templates", workflow?.process_template_id],
  queryFn: () => getTemplateDetail(workflow!.process_template_id),
  enabled: !!workflow?.process_template_id,
});

// 3. Build nodes from template activities, overlay states from workflow activity instances
const stateMap = new Map(
  workflow.activity_instances.map((ai) => [ai.activity_template_id, ai.state])
);

const nodes = template.activities.map((act) => ({
  id: act.id,
  type: act.activity_type === "start" ? "startNode" : act.activity_type === "end" ? "endNode" : act.activity_type + "Node",
  position: { x: act.position_x ?? 0, y: act.position_y ?? 0 },
  data: {
    name: act.name,
    activityType: act.activity_type,
    activityState: stateMap.get(act.id) ?? "dormant",  // overlay state
  },
}));

const edges = template.flows.map((flow) => ({
  id: flow.id,
  source: flow.source_activity_id,
  target: flow.target_activity_id,
  type: flow.flow_type === "reject" ? "rejectEdge" : "normalEdge",
}));

// 4. Apply dagre layout
const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(nodes, edges, "LR");
```

### Pattern 5: Read-Only Node Wrapping

Wrap existing node components to apply state-colored borders and hide handles:

```typescript
// In WorkflowProgressGraph.tsx -- create wrapper nodeTypes
function ProgressManualNode(props: NodeProps) {
  const state = props.data.activityState as string;
  const borderColor = STATE_BORDER_COLORS[state] ?? STATE_BORDER_COLORS.dormant;
  return (
    <div style={{ borderColor }} className="rounded-lg border-2 min-w-[160px] min-h-[64px] px-3 py-2">
      <div className="font-semibold text-sm truncate">{props.data.name}</div>
      {/* No Handles -- read-only */}
    </div>
  );
}

const STATE_BORDER_COLORS: Record<string, string> = {
  complete: "oklch(0.55 0.2 142)",   // green-600
  active: "oklch(0.55 0.19 250)",    // blue-600
  dormant: "oklch(0.8 0 0)",          // gray-300
  paused: "oklch(0.6 0.15 80)",      // amber-600
  error: "oklch(0.55 0.2 27)",       // red-600
};
```

### Anti-Patterns to Avoid

- **Reusing designerStore for progress graph:** The designer store has undo/redo, dirty tracking, and editing concerns. Create a completely separate, stateless approach for the read-only graph -- just derive nodes/edges from API data in the component.
- **Sharing API helpers across modules:** Per project convention, each API module (inbox.ts, documents.ts, workflows.ts) has its own `authHeaders()` and `apiFetch()`. Do not extract shared utilities.
- **Creating a Zustand store for wizard state:** The wizard state (current step, selections) is local to the dialog and should use `useState`. It resets when the dialog closes. No persistence needed.
- **Fetching template detail on every table render:** Only fetch template detail when the progress tab is active and a workflow is selected.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Table with sorting/pagination | Custom table logic | TanStack Table (already used) | Handles column definitions, sorting, pagination state |
| Multi-step form state | Custom step machine | Simple `useState<number>` for step index | Only 4 linear steps with back/next -- no branching logic |
| Graph layout | Custom positioning algorithm | dagre via `getLayoutedElements` (already exists) | Handles directed graph layout with proper spacing |
| Date formatting | Custom date utilities | Browser `Intl.RelativeTimeFormat` or `toLocaleDateString` | Established pattern from Phase 13/14 |
| Toast notifications | Custom notification system | sonner (already installed) | Already used across all prior phases |

## Common Pitfalls

### Pitfall 1: Regular User Pagination Gap (D-06)

**What goes wrong:** The regular `GET /api/workflows` endpoint returns ALL workflows (not filtered by user) but paginates server-side. Client-side filtering by `supervisor_id` means some pages may show fewer items than the page size, or empty pages.
**Why it happens:** The backend list_workflows service does not accept a user filter, and adding backend changes is out of scope.
**How to avoid:** Accept the limitation for v1.1. For most deployments with few concurrent users, pagination will still be usable. Document this as a known limitation. The admin endpoint is used for admins and works correctly with server-side filters.
**Warning signs:** Users see pages with fewer than 20 items or empty pages in the table.

### Pitfall 2: Activity Template ID Mismatch

**What goes wrong:** The progress graph requires mapping `activity_instance.activity_template_id` to template activities. If the template has been modified after the workflow was started, the graph may show stale or missing nodes.
**Why it happens:** Template versioning -- a new template version creates new activity template IDs.
**How to avoid:** The workflow stores `process_template_id` referencing the exact template version it was started from. Always use this ID (not the "latest" template) to fetch the graph structure. The `GET /api/v1/templates/{id}` endpoint returns the specific version.
**Warning signs:** Nodes appear in the graph with no state coloring, or activity instances reference template IDs not found in the fetched template.

### Pitfall 3: React Flow Node Type Registration

**What goes wrong:** React Flow does not render nodes with unregistered types. If the `nodeTypes` map does not include a type returned from the template, nodes appear as default rectangles or cause errors.
**Why it happens:** The node type string must match exactly between the template data and the nodeTypes registration.
**How to avoid:** Use the existing `nodeTypes` registry from `components/nodes/index.ts` as reference. Map activity types (`start`, `end`, `manual`, `auto`) to registered node type keys (`startNode`, `endNode`, `manualNode`, `autoNode`). For the progress graph, create a separate `progressNodeTypes` map with the wrapped components.
**Warning signs:** Plain rectangles appearing in the progress graph instead of styled nodes.

### Pitfall 4: Wizard State Leaking Between Opens

**What goes wrong:** Opening the wizard after a previous use retains the previous selections (template, documents, variables).
**Why it happens:** State is not reset when the dialog closes.
**How to avoid:** Reset all wizard state in the `onOpenChange` handler when `open` becomes false. Or use a key prop on the dialog content that changes each time the dialog opens.
**Warning signs:** Step 4 (review) shows selections from a previous wizard session.

### Pitfall 5: Terminate Endpoint is /abort not /terminate

**What goes wrong:** API call to `/api/workflows/{id}/terminate` returns 404.
**Why it happens:** The backend endpoint is `POST /{workflow_id}/abort`, not `/terminate`. The UI labels it "Terminate" but the API uses "abort".
**How to avoid:** Use `POST /api/workflows/{id}/abort` in the API module. The UI-SPEC already documents this correctly.
**Warning signs:** 404 or 405 errors when clicking the Terminate button.

## Code Examples

### Verified: Backend WorkflowStartRequest Schema

```python
# Source: src/app/schemas/workflow.py (line 10-16)
class WorkflowStartRequest(BaseModel):
    template_id: uuid.UUID
    document_ids: list[uuid.UUID] = []
    performer_overrides: dict[str, str] = {}
    initial_variables: dict[str, Any] = {}
    alias_set_id: uuid.UUID | None = None
```

The `initial_variables` field is a flat dict mapping variable name to value. The frontend wizard should collect values keyed by variable name (not ID).

### Verified: Backend Admin List Endpoint Query Params

```python
# Source: src/app/routers/workflows.py (line 92-118)
# GET /api/workflows/admin/list
# Query params: skip, limit, state (str), template_id (UUID), created_by (UUID), date_from, date_to
```

### Verified: WorkflowState Enum Values

```python
# Source: src/app/models/enums.py (line 28-34)
class WorkflowState(str, enum.Enum):
    DORMANT = "dormant"
    RUNNING = "running"
    HALTED = "halted"
    FAILED = "failed"
    FINISHED = "finished"
```

### Verified: ActivityState Enum Values

```python
# Source: src/app/models/enums.py (line 46-51)
class ActivityState(str, enum.Enum):
    DORMANT = "dormant"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETE = "complete"
    ERROR = "error"
```

### Verified: React Flow Read-Only Configuration

```typescript
// Source: @xyflow/react docs -- read-only mode props
<ReactFlow
  nodes={nodes}
  edges={edges}
  nodeTypes={progressNodeTypes}
  edgeTypes={edgeTypes}
  nodesDraggable={false}
  nodesConnectable={false}
  elementsSelectable={false}
  panOnDrag={true}
  zoomOnScroll={true}
  fitView={true}
  proOptions={{ hideAttribution: true }}
>
  {/* No MiniMap, no Controls -- graph is 300px tall */}
</ReactFlow>
```

### Verified: Existing Auto-Layout Hook

```typescript
// Source: frontend/src/hooks/useAutoLayout.ts
// getLayoutedElements(nodes, edges, 'LR') -- already handles dagre layout
// NODE_DIMENSIONS defines sizes for each node type
// Import and use directly -- no modifications needed
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| React Flow v11 `reactFlowInstance` | React Flow v12 with hooks API | v12.0 (2024) | Use `useReactFlow()` hook if needed. Already on v12. |
| Separate nodeTypes per component | Shared nodeTypes map | Already established | Use `components/nodes/index.ts` for type registration |
| TanStack Query v4 `useQuery` | TanStack Query v5 `useQuery` | v5.0 (2024) | Already on v5. Use object syntax for queryKey/queryFn. |

## Open Questions

1. **Regular user workflow filtering**
   - What we know: `GET /api/workflows` returns ALL workflows. `supervisor_id` on each instance equals the user who started it. Admin endpoint has `created_by` filter.
   - What's unclear: Whether the pagination gap (client-side filtering after server-side pagination) will be acceptable in practice.
   - Recommendation: Implement as client-side filter for v1.1. If it causes UX issues, add a `supervisor_id` query param to the regular list endpoint in a future phase.

2. **Template name in regular user list**
   - What we know: `WorkflowInstanceResponse` does NOT include `template_name`. Only `process_template_id` (UUID). The admin response `WorkflowAdminListResponse` includes `template_name`.
   - What's unclear: How to show template name in the table for regular users without making N+1 queries.
   - Recommendation: Fetch the templates list once (`GET /api/v1/templates/`) and build a client-side lookup map of `template_id -> name`. This is already needed for the template filter dropdown.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Vitest (not yet configured for frontend) |
| Config file | None -- no frontend test infrastructure exists |
| Quick run command | N/A (no tests exist) |
| Full suite command | Backend: `pytest tests/ -x` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WF-01 | Start workflow wizard submits correct payload | manual | Manual browser test | N/A |
| WF-02 | Instance list renders with correct columns, filters | manual | Manual browser test | N/A |
| WF-03 | Admin actions (halt/resume/terminate) call correct endpoints | manual | Manual browser test | N/A |
| WF-04 | Progress graph renders nodes with correct state colors | manual | Manual browser test | N/A |

### Sampling Rate
- **Per task commit:** Visual verification in browser (dev server)
- **Per wave merge:** Full visual walkthrough of all 4 requirements
- **Phase gate:** All 4 success criteria verified manually in running app

### Wave 0 Gaps
- No frontend test infrastructure (Vitest not installed/configured)
- All validation is manual for this phase (consistent with prior frontend phases 12-14)

## Project Constraints (from CLAUDE.md)

- **Frontend-only:** All backend APIs already exist. No backend changes allowed per REQUIREMENTS.md out-of-scope section.
- **Tech stack locked:** React 19, TypeScript, Vite, shadcn/ui, TanStack Query/Table, Zustand, React Flow, Tailwind CSS.
- **API module pattern:** Duplicate auth helpers per module (not shared). Established in Phase 14.
- **State management:** TanStack Query for server state, component-level useState for UI state. No new Zustand stores.
- **Component library:** shadcn/ui with Radix UI primitives. Manual install (no components.json).
- **Auth pattern:** `useAuthStore` provides `userId`, `isSuperuser`, `isAvailable`.

## Sources

### Primary (HIGH confidence)
- `src/app/routers/workflows.py` -- All workflow endpoints verified (start, list, admin list, detail, halt, resume, abort)
- `src/app/schemas/workflow.py` -- Request/response schemas verified
- `src/app/models/enums.py` -- WorkflowState, ActivityState enum values verified
- `frontend/src/components/nodes/` -- Existing node components verified (StartNode, ManualNode, AutoNode, EndNode)
- `frontend/src/hooks/useAutoLayout.ts` -- dagre layout utility verified
- `frontend/src/stores/designerStore.ts` -- Designer store structure verified (confirms: do NOT reuse)
- `frontend/src/pages/InboxPage.tsx` -- Split-pane layout pattern verified
- `frontend/src/pages/DocumentsPage.tsx` -- Split-pane + filter pattern verified
- `frontend/src/api/documents.ts` -- API module pattern verified (duplicated helpers)
- `frontend/src/stores/authStore.ts` -- Auth state shape verified (userId, isSuperuser)
- `.planning/phases/15-workflow-operations/15-UI-SPEC.md` -- UI design contract verified
- `.planning/phases/15-workflow-operations/15-CONTEXT.md` -- User decisions verified

### Secondary (MEDIUM confidence)
- @xyflow/react v12 read-only mode props -- based on established usage in the codebase designer

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already installed and patterns established in prior phases
- Architecture: HIGH -- split-pane, TanStack Table, TanStack Query patterns are direct copies of Phase 13/14
- Pitfalls: HIGH -- identified from direct code reading of backend endpoints and frontend patterns

**Research date:** 2026-04-06
**Valid until:** 2026-05-06 (stable -- no external dependency changes expected)
