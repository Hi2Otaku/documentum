# Phase 8: Visual Workflow Designer - Research

**Researched:** 2026-04-04
**Domain:** React frontend with visual node-based workflow designer
**Confidence:** HIGH

## Summary

Phase 8 creates the entire frontend application from scratch -- a React 19 + TypeScript + Vite project with a visual workflow designer built on React Flow (@xyflow/react v12). The frontend integrates with the existing FastAPI backend (17 template endpoints, auth, user/group APIs) via REST calls with JWT authentication.

The core technical challenge is the three-panel designer layout: a draggable node palette (left), a React Flow canvas (center), and a context-sensitive properties panel (right). The drag-and-drop, custom node/edge rendering, auto-layout, undo/redo, and save/load serialization are the primary implementation concerns. All libraries in the stack are mature with well-documented patterns.

**Primary recommendation:** Use @xyflow/react v12 with custom node types (4) and custom edge types (3), dagre for auto-layout, Zustand for canvas/UI state, TanStack Query for server state, and shadcn/ui v4 for all UI components. The login endpoint uses OAuth2PasswordRequestForm (form-data, not JSON) -- the API client must handle this.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-01: Drag-from-sidebar palette for adding nodes. Left sidebar with draggable node types (Start, End, Manual, Auto). Collapsible to icons-only or hidden.
- D-02: Distinct shapes per node type -- Start = green circle, Manual = blue rounded rectangle, Auto = orange hexagon, End = red filled circle.
- D-03: Color-coded edge styles -- Normal = solid dark gray, Reject = dashed red, Conditional = dotted blue with diamond.
- D-04: Canvas features: minimap, snap-to-grid, auto-layout button (dagre/elkjs), undo/redo (Ctrl+Z/Y).
- D-05: Delete via keyboard (Delete/Backspace) AND right-click context menu.
- D-06: Multi-select via rubber-band and Shift+click. Group move/delete.
- D-07: Edge drawing via drag-from-handle-to-handle (React Flow built-in).
- D-08: Nodes display name + key config hints on canvas (performer name, trigger type).
- D-09: Right sidebar properties panel. Opens on selection. Same panel for nodes and edges.
- D-10: Performer assignment form with type dropdown and dynamic second field.
- D-11: Process variables managed in dedicated tab (template-level settings).
- D-12: When no selection, properties panel shows template-level settings with tabs.
- D-13: Manual save via Ctrl+S or toolbar button. Unsaved changes indicator.
- D-14: Validation errors as inline markers + collapsible error panel. Clickable to pan to problem node.
- D-15: Template list/browser page with name, state, version, last modified.
- D-16: "Validate & Install" one-click button in toolbar.
- D-17: Frontend in `frontend/` directory (monorepo).
- D-18: Minimal app shell -- login, template list, designer canvas. Simple top nav.
- D-19: Routes: `/login`, `/templates`, `/templates/:id/edit`.
- D-20: Login calling existing `/api/v1/auth/login`. JWT for auth. Protected routes redirect to login.
- D-21: Frontend added to Docker Compose as dev service running Vite.

### Claude's Discretion
- Loading skeleton and spinner designs
- Exact spacing, typography, color palette (within shadcn/ui defaults)
- React Flow configuration details (edge routing algorithm, handle positions)
- API client structure (axios vs fetch, error handling patterns)
- Zustand store organization
- Auto-layout algorithm choice (dagre vs elkjs)
- CORS origin configuration details
- Undo/redo implementation approach (command pattern vs state snapshots)

### Deferred Ideas (OUT OF SCOPE)
None.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DESIGN-01 | Web-based drag-and-drop canvas for designing workflow templates (React Flow) | React Flow v12 custom nodes, drag-and-drop from sidebar pattern, nodeTypes/edgeTypes registration |
| DESIGN-02 | User can drag activity nodes (Manual, Auto, Start, End) onto the canvas | HTML5 drag-and-drop API with screenToFlowPosition for coordinate conversion; 4 custom node components |
| DESIGN-03 | User can draw flow connections (Normal Flow, Reject Flow) between activities | React Flow built-in handle-to-handle connection; 3 custom edge types with distinct styling |
| DESIGN-04 | User can configure activity properties (performer, trigger, conditions) via side panel | Right sidebar with conditional form fields; TanStack Query for user/group picker data |
| DESIGN-05 | User can define process variables via the designer | Template-level Variables tab in properties panel; CRUD via `/api/v1/templates/{id}/variables` |
| DESIGN-06 | Designer validates the template and shows errors before installation | POST `/api/v1/templates/{id}/validate` returns ValidationResult; map entity_id to canvas nodes for visual markers |
| DESIGN-07 | Designer saves/loads templates to/from the backend API | Serialize React Flow nodes/edges to API format (activities, flows); deserialize API response back to nodes/edges |

</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Tech stack locked:** React 19, TypeScript 5, Vite 6, @xyflow/react 12, shadcn/ui v4, Tailwind CSS 4, TanStack Query 5, Zustand 5, React Router 7
- **Backend:** FastAPI at localhost:8000 with CORS already configured (allow_origins=["*"])
- **Testing:** Vitest for frontend tests, Playwright for E2E
- **Linting:** Ruff for Python (backend only); frontend linting TBD (ESLint likely)
- **Docker Compose:** All services containerized, single `docker compose up`

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 19.2.4 | UI framework | Project requirement; dominant ecosystem |
| TypeScript | 6.0.2 | Type safety | Non-negotiable for complex workflow UI |
| Vite | 8.0.3 | Build tool | Fast dev server, HMR, standard React SPA toolchain |
| @xyflow/react | 12.10.2 | Visual workflow canvas | De facto standard for node-based UIs in React |
| shadcn/ui | 4.1.2 (CLI) | UI components | Copy-paste Radix + Tailwind components, full code ownership |
| Tailwind CSS | 4.2.2 | Utility CSS | shadcn/ui dependency, rapid styling |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @tanstack/react-query | 5.96.2 | Server state | All API data fetching (templates, users, groups) |
| zustand | 5.0.12 | Client state | Canvas state (nodes/edges/selection/dirty/undo), auth token, UI panel visibility |
| react-router | 7.14.0 | Routing | 3 routes: /login, /templates, /templates/:id/edit |
| @dagrejs/dagre | 3.0.0 | Auto-layout | Arrange nodes in left-to-right directed graph |
| sonner | 2.0.7 | Toast notifications | Save success/error, validation results, install feedback |
| @fontsource/inter | latest | Typography | shadcn/ui default font |
| lucide-react | (with shadcn) | Icons | Toolbar, palette, node icons |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| dagre | elkjs (0.11.1) | Elkjs produces better layouts for complex graphs but is heavier (WASM), slower. Dagre is simpler, faster, sufficient for workflow trees |
| fetch (native) | axios | Fetch is zero-dependency, works with TypeScript generics. Axios adds interceptors but not needed with TanStack Query |
| State snapshots (undo) | Command pattern | State snapshots are simpler to implement with Zustand; command pattern is more memory-efficient but overkill here |

**Installation:**
```bash
# In frontend/ directory
npm create vite@latest . -- --template react-ts
npm install @xyflow/react @tanstack/react-query zustand react-router sonner @dagrejs/dagre @fontsource/inter
npm install -D tailwindcss @tailwindcss/vite
npx shadcn@latest init
```

## Architecture Patterns

### Recommended Project Structure

```
frontend/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── components.json              # shadcn/ui config
├── src/
│   ├── main.tsx                 # Entry point, providers
│   ├── App.tsx                  # Router setup
│   ├── api/
│   │   ├── client.ts            # Base fetch wrapper with JWT, envelope unwrap
│   │   ├── templates.ts         # Template API functions
│   │   ├── auth.ts              # Login API (form-data POST)
│   │   └── users.ts             # Users/groups API
│   ├── components/
│   │   ├── ui/                  # shadcn/ui generated components
│   │   ├── layout/
│   │   │   ├── AppShell.tsx     # Nav bar + outlet
│   │   │   └── ProtectedRoute.tsx
│   │   ├── designer/
│   │   │   ├── Canvas.tsx       # ReactFlow wrapper + event handlers
│   │   │   ├── Toolbar.tsx      # Save, validate, undo/redo buttons
│   │   │   ├── NodePalette.tsx  # Left sidebar draggable items
│   │   │   ├── PropertiesPanel.tsx  # Right sidebar
│   │   │   ├── ErrorPanel.tsx   # Bottom validation errors
│   │   │   └── ContextMenu.tsx  # Right-click menu
│   │   ├── nodes/
│   │   │   ├── StartNode.tsx
│   │   │   ├── ManualNode.tsx
│   │   │   ├── AutoNode.tsx
│   │   │   └── EndNode.tsx
│   │   └── edges/
│   │       ├── NormalEdge.tsx
│   │       ├── RejectEdge.tsx
│   │       └── ConditionalEdge.tsx
│   ├── hooks/
│   │   ├── useAutoLayout.ts     # Dagre layout function
│   │   └── useKeyboardShortcuts.ts
│   ├── stores/
│   │   ├── designerStore.ts     # Nodes, edges, selection, dirty, undo/redo
│   │   ├── authStore.ts         # Token, user, isAuthenticated
│   │   └── uiStore.ts           # Panel visibility
│   ├── lib/
│   │   ├── utils.ts             # shadcn cn() helper
│   │   └── serialization.ts     # API <-> React Flow data mapping
│   ├── pages/
│   │   ├── LoginPage.tsx
│   │   ├── TemplateListPage.tsx
│   │   └── DesignerPage.tsx
│   └── types/
│       ├── api.ts               # API response types matching backend schemas
│       └── designer.ts          # Custom node/edge data types
└── Dockerfile                   # (optional) for Docker Compose dev service
```

### Pattern 1: API Client with Envelope Unwrap

**What:** All backend responses are wrapped in `EnvelopeResponse { data, meta, errors }`. The API client must unwrap this.
**When to use:** Every API call.
**Example:**
```typescript
// Source: Backend schema analysis (src/app/schemas/common.py)
const API_BASE = '/api/v1';

async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  token?: string
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options.headers as Record<string, string>) || {}),
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || body.errors?.[0]?.message || res.statusText);
  }
  const envelope = await res.json();
  return envelope.data as T;
}
```

### Pattern 2: Login with OAuth2 Form Data

**What:** The `/api/v1/auth/login` endpoint uses `OAuth2PasswordRequestForm` which expects `application/x-www-form-urlencoded`, not JSON.
**When to use:** Login only.
**Critical detail:** This is a common gotcha -- the backend uses FastAPI's `Depends(OAuth2PasswordRequestForm)` which reads `username` and `password` from form data.
**Example:**
```typescript
// Source: src/app/routers/auth.py line 13
async function login(username: string, password: string): Promise<string> {
  const body = new URLSearchParams({ username, password });
  const res = await fetch('/api/v1/auth/login', {
    method: 'POST',
    body,
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
  if (!res.ok) throw new Error('Invalid username or password.');
  const envelope = await res.json();
  return envelope.data.access_token;
}
```

### Pattern 3: React Flow Node/Edge Type Registration

**What:** Custom node and edge types must be defined outside the component to prevent re-renders.
**When to use:** Canvas component setup.
**Example:**
```typescript
// Source: https://reactflow.dev/learn/customization/custom-nodes
import { StartNode } from '../nodes/StartNode';
import { ManualNode } from '../nodes/ManualNode';
import { AutoNode } from '../nodes/AutoNode';
import { EndNode } from '../nodes/EndNode';

// MUST be outside component to avoid re-render loops
const nodeTypes = {
  startNode: StartNode,
  manualNode: ManualNode,
  autoNode: AutoNode,
  endNode: EndNode,
};

const edgeTypes = {
  normalEdge: NormalEdge,
  rejectEdge: RejectEdge,
  conditionalEdge: ConditionalEdge,
};
```

### Pattern 4: Drag-and-Drop from Sidebar to Canvas

**What:** HTML5 Drag and Drop API to create nodes from the palette sidebar.
**When to use:** Node creation from palette.
**Example:**
```typescript
// Source: https://reactflow.dev/examples/interaction/drag-and-drop
// In NodePalette: set drag data
const onDragStart = (event: DragEvent, nodeType: string) => {
  event.dataTransfer.setData('application/reactflow', nodeType);
  event.dataTransfer.effectAllowed = 'move';
};

// In Canvas: handle drop
const { screenToFlowPosition } = useReactFlow();

const onDrop = useCallback((event: DragEvent) => {
  event.preventDefault();
  const type = event.dataTransfer.getData('application/reactflow');
  if (!type) return;

  const position = screenToFlowPosition({
    x: event.clientX,
    y: event.clientY,
  });

  const newNode = {
    id: crypto.randomUUID(),
    type,
    position,
    data: { name: `New ${type}`, ... },
  };
  // Add to Zustand store
}, [screenToFlowPosition]);
```

### Pattern 5: Undo/Redo with State Snapshots

**What:** Store snapshots of nodes/edges arrays in undo/redo stacks in Zustand.
**When to use:** Every mutation (add/delete/move node, add/delete edge, property change).
**Example:**
```typescript
interface DesignerState {
  nodes: Node[];
  edges: Edge[];
  undoStack: Array<{ nodes: Node[]; edges: Edge[] }>;
  redoStack: Array<{ nodes: Node[]; edges: Edge[] }>;
  isDirty: boolean;

  pushSnapshot: () => void;  // Save current state before mutation
  undo: () => void;
  redo: () => void;
}
```

### Pattern 6: Data Serialization (Canvas <-> API)

**What:** Convert between React Flow node/edge format and backend API schemas.
**When to use:** Load template (API -> canvas) and save template (canvas -> API).
**Critical details:**
- ActivityTemplateResponse has `position_x` and `position_y` (separate floats, nullable)
- React Flow nodes use `position: { x, y }`
- Activity `id` is UUID in API, string in React Flow
- FlowTemplate uses `source_activity_id`/`target_activity_id`, React Flow uses `source`/`target`
- condition_expression can be string or dict in the API

### Anti-Patterns to Avoid

- **Defining nodeTypes/edgeTypes inside component:** Causes infinite re-render loops in React Flow. Always define at module level.
- **Using controlled nodes without onNodesChange:** React Flow needs the change handler to update node positions on drag. Without it, nodes appear frozen.
- **Forgetting ReactFlowProvider:** `useReactFlow()` hooks (screenToFlowPosition, fitView) require the component to be inside `<ReactFlowProvider>`. Wrap the parent, not the ReactFlow component itself.
- **Serializing full React Flow state to API:** Only send the data properties (name, performer, etc.) and position, not React Flow internal props (selected, dragging, measured).
- **Sending JSON to the login endpoint:** Backend uses OAuth2PasswordRequestForm which expects form-data (application/x-www-form-urlencoded).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Node-based canvas | Custom SVG/Canvas rendering | @xyflow/react | Thousands of edge cases (zoom, pan, selection, handles, performance) |
| Graph auto-layout | Custom layout algorithm | @dagrejs/dagre | Directed graph layout is a solved problem; dagre handles rank assignment and crossing minimization |
| UI components | Custom button/input/dialog/tabs | shadcn/ui | Accessible, consistent, tested components out of the box |
| Server state cache | Manual fetch + useState | @tanstack/react-query | Handles caching, deduplication, background refetch, loading/error states |
| Form-data encoding | Manual string concatenation | URLSearchParams | Handles encoding edge cases properly |
| Unique IDs | Auto-increment counter | crypto.randomUUID() | UUIDs match backend ID format, no collision risk |
| Smooth step edges | Custom SVG path math | getSmoothStepPath from @xyflow/react | Built-in path calculation handles all edge routing |

## Common Pitfalls

### Pitfall 1: ReactFlow Container Needs Explicit Dimensions
**What goes wrong:** Canvas renders as 0px height, nothing visible.
**Why it happens:** ReactFlow uses its parent container dimensions. If parent has no explicit height, it collapses.
**How to avoid:** Set the canvas container to `h-full` or explicit height, and ensure all ancestors have height set (common pattern: `h-screen` on root, `flex-1` on canvas area).
**Warning signs:** Empty space where canvas should be; React Flow renders but no nodes visible.

### Pitfall 2: Save Requires Multiple API Calls
**What goes wrong:** Naive "save" tries to PUT the entire template graph in one call, but the API has separate endpoints for template metadata, activities, flows, and variables.
**Why it happens:** The backend CRUD is entity-based, not graph-based.
**How to avoid:** Implement a diff-based save: compare current canvas state with last-saved state, then issue create/update/delete calls for each changed entity. Or use a simpler approach: on first save of a new template, POST all entities; on subsequent saves, PUT changed entities only.
**Warning signs:** 409 conflicts, orphaned entities, position data not persisting.

### Pitfall 3: Vite Proxy for API Calls
**What goes wrong:** CORS errors or wrong base URL in dev vs Docker.
**Why it happens:** Frontend runs on port 5173 (Vite), backend on port 8000. Even though CORS is configured as `allow_origins=["*"]`, using a Vite proxy is cleaner.
**How to avoid:** Configure Vite proxy in `vite.config.ts`:
```typescript
server: {
  proxy: {
    '/api': 'http://localhost:8000'
  }
}
```
In Docker Compose, the proxy target becomes the service name: `http://api:8000`.
**Warning signs:** Network errors in browser console, CORS headers missing.

### Pitfall 4: Position Data on Activities
**What goes wrong:** Nodes load at (0,0) after save/reload, losing user's arrangement.
**Why it happens:** Forgetting to send `position_x` and `position_y` when creating/updating activities.
**How to avoid:** Always include position data in activity create/update calls. The backend schema accepts nullable `position_x: float | None` and `position_y: float | None`.
**Warning signs:** All nodes stacked at top-left after reload.

### Pitfall 5: Stale Token After Expiry
**What goes wrong:** API calls silently fail with 401 after token expires.
**Why it happens:** JWT has expiration, no refresh token mechanism in current backend.
**How to avoid:** Intercept 401 responses in the API client, clear auth store, redirect to login. Show toast "Session expired, please log in again."
**Warning signs:** Random failures after being idle.

### Pitfall 6: React Flow Node ID Must Be String
**What goes wrong:** TypeScript errors or nodes not rendering.
**Why it happens:** Backend returns UUID objects, React Flow requires string IDs.
**How to avoid:** Always convert: `id: String(activity.id)` when mapping API response to nodes.
**Warning signs:** TypeScript type mismatch errors, nodes not selectable.

## Code Examples

### Custom Node Component (ManualNode)

```typescript
// Source: React Flow custom nodes docs + UI-SPEC
import { Handle, Position, type NodeProps, type Node } from '@xyflow/react';

type ManualNodeData = {
  name: string;
  performerType?: string;
  performerId?: string;
  description?: string;
};

type ManualNodeType = Node<ManualNodeData, 'manualNode'>;

export function ManualNode({ data, selected }: NodeProps<ManualNodeType>) {
  const hint = data.performerType
    ? `${data.performerType}: ${data.performerId || '...'}`
    : 'No performer';

  return (
    <>
      <Handle type="target" position={Position.Left} />
      <div
        className={`min-w-[160px] min-h-[64px] rounded-lg bg-blue-500 border-2 border-blue-600 
          px-3 py-2 text-white ${selected ? 'ring-2 ring-primary ring-offset-2' : ''}`}
      >
        <div className="font-semibold text-sm truncate">{data.name}</div>
        <div className="text-sm opacity-70 truncate">{hint}</div>
      </div>
      <Handle type="source" position={Position.Right} />
    </>
  );
}
```

### Custom Edge Component (RejectEdge)

```typescript
// Source: React Flow custom edges docs + UI-SPEC
import {
  BaseEdge,
  EdgeLabelRenderer,
  getSmoothStepPath,
  type EdgeProps,
} from '@xyflow/react';

export function RejectEdge({
  id,
  sourceX, sourceY,
  targetX, targetY,
  sourcePosition, targetPosition,
  data,
  selected,
}: EdgeProps) {
  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX, sourceY,
    targetX, targetY,
    sourcePosition, targetPosition,
  });

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        style={{
          stroke: '#ef4444',
          strokeWidth: 2,
          strokeDasharray: '8 4',
        }}
        markerEnd="url(#arrow-red)"
      />
      <EdgeLabelRenderer>
        <div
          className="absolute bg-white px-2 py-0.5 rounded text-sm text-red-500 border border-red-200 pointer-events-all"
          style={{
            transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
          }}
        >
          {data?.displayLabel || 'Reject'}
        </div>
      </EdgeLabelRenderer>
    </>
  );
}
```

### Dagre Auto-Layout Hook

```typescript
// Source: https://reactflow.dev/examples/layout/dagre
import dagre from '@dagrejs/dagre';
import type { Node, Edge } from '@xyflow/react';

const NODE_WIDTH = 172;
const NODE_HEIGHT = 64;

export function getLayoutedElements(
  nodes: Node[],
  edges: Edge[],
  direction: 'LR' | 'TB' = 'LR'
) {
  const g = new dagre.graphlib.Graph().setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: direction, nodesep: 50, ranksep: 80 });

  nodes.forEach((node) => {
    const width = node.type === 'startNode' || node.type === 'endNode' ? 60 : NODE_WIDTH;
    const height = node.type === 'startNode' || node.type === 'endNode' ? 60 : NODE_HEIGHT;
    g.setNode(node.id, { width, height });
  });

  edges.forEach((edge) => {
    g.setEdge(edge.source, edge.target);
  });

  dagre.layout(g);

  const layoutedNodes = nodes.map((node) => {
    const { x, y, width, height } = g.node(node.id);
    return {
      ...node,
      position: { x: x - width / 2, y: y - height / 2 },
    };
  });

  return { nodes: layoutedNodes, edges };
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| react-flow-renderer (v10) | @xyflow/react (v12) | 2024 | Package renamed; import paths changed from `reactflow` to `@xyflow/react` |
| Create React App | Vite | 2023-2024 | CRA deprecated; Vite is the standard React SPA tool |
| shadcn/ui v0 (manual) | shadcn CLI v4 | 2025 | CLI handles init, add, diff; Tailwind CSS v4 support |
| Redux + RTK Query | Zustand + TanStack Query | 2024-2025 | Lighter weight, better separation of server/client state |
| passlib + python-jose | pwdlib + PyJWT | Phase 01 decision | Backend already uses updated auth libraries |

**Deprecated/outdated:**
- `reactflow` npm package: Use `@xyflow/react` instead (v12+)
- `useNodesState`/`useEdgesState`: Still works in v12 but projects with external state (like Zustand) should use controlled mode with `onNodesChange`/`onEdgesChange`
- Create React App: Fully deprecated, do not use

## Open Questions

1. **Save strategy: full sync vs incremental**
   - What we know: Backend has individual CRUD endpoints per entity (activities, flows, variables). No bulk update endpoint.
   - What's unclear: Whether to diff and patch, or delete-all-and-recreate on save.
   - Recommendation: Use incremental approach -- track which entities are new (POST), modified (PUT), or deleted (DELETE) by comparing current canvas state with the loaded state snapshot. This avoids unnecessary API calls and preserves entity IDs (important since flows reference activity IDs).

2. **Hexagon shape for Auto nodes**
   - What we know: CSS clip-path can create hexagons. React Flow wraps custom nodes in a div.
   - What's unclear: Whether clip-path interacts well with React Flow's selection ring and handle positioning.
   - Recommendation: Use clip-path for the inner visual element, keep the outer wrapper as a standard rectangle for React Flow hit detection. Apply selection ring to the outer wrapper.

3. **Docker Compose frontend service**
   - What we know: Need to add a `frontend` service to docker-compose.yml.
   - What's unclear: Whether to use a custom Dockerfile with node image or just mount and run.
   - Recommendation: Use `node:20-alpine` image with volume mount of `frontend/` and command `npm run dev -- --host 0.0.0.0`. Port 5173 exposed. Depends on `api` service. Vite proxy configured to target `http://api:8000`.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | Frontend build/dev | Yes | 25.8.0 | -- |
| npm | Package management | Yes | 11.11.0 | -- |
| Docker | Container services | Yes | 29.2.1 | -- |
| Docker Compose | Orchestration | Yes | 5.0.2 | -- |

**Missing dependencies with no fallback:** None -- all required tools available.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Vitest 3.x (to be installed) |
| Config file | `frontend/vitest.config.ts` (Wave 0 creation) |
| Quick run command | `cd frontend && npx vitest run --reporter=verbose` |
| Full suite command | `cd frontend && npx vitest run --coverage` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DESIGN-01 | Canvas renders with ReactFlow, nodes draggable | unit | `npx vitest run src/components/designer/Canvas.test.tsx` | No -- Wave 0 |
| DESIGN-02 | Dragging palette item onto canvas creates node | unit | `npx vitest run src/components/designer/NodePalette.test.tsx` | No -- Wave 0 |
| DESIGN-03 | Edge creation between nodes with correct types | unit | `npx vitest run src/components/edges/` | No -- Wave 0 |
| DESIGN-04 | Properties panel shows correct fields per node type | unit | `npx vitest run src/components/designer/PropertiesPanel.test.tsx` | No -- Wave 0 |
| DESIGN-05 | Variables CRUD in template-level tab | unit | `npx vitest run src/components/designer/PropertiesPanel.test.tsx` | No -- Wave 0 |
| DESIGN-06 | Validation errors display on canvas and error panel | unit | `npx vitest run src/components/designer/ErrorPanel.test.tsx` | No -- Wave 0 |
| DESIGN-07 | Serialization round-trip (API -> canvas -> API) | unit | `npx vitest run src/lib/serialization.test.ts` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `cd frontend && npx vitest run --reporter=verbose`
- **Per wave merge:** `cd frontend && npx vitest run`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `frontend/vitest.config.ts` -- Vitest configuration
- [ ] `frontend/src/test/setup.ts` -- Test setup (jsdom environment)
- [ ] `frontend/src/lib/serialization.test.ts` -- Serialization round-trip tests (DESIGN-07)
- [ ] Framework install: `npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom @testing-library/user-event`

## Sources

### Primary (HIGH confidence)
- React Flow official docs (reactflow.dev) -- custom nodes, custom edges, drag-and-drop, dagre layout examples
- Backend source code analysis -- `src/app/routers/templates.py` (17 endpoints), `src/app/schemas/template.py` (request/response shapes), `src/app/routers/auth.py` (OAuth2PasswordRequestForm login)
- NPM registry -- verified all package versions (2026-04-04)
- UI-SPEC at `.planning/phases/08-visual-workflow-designer/08-UI-SPEC.md` -- component inventory, interaction contracts, data mapping

### Secondary (MEDIUM confidence)
- [React Flow dagre example](https://reactflow.dev/examples/layout/dagre) -- verified layout pattern
- [React Flow drag-and-drop example](https://reactflow.dev/examples/interaction/drag-and-drop) -- verified DnD pattern with screenToFlowPosition

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all versions verified against npm registry, project CLAUDE.md specifies exact stack
- Architecture: HIGH -- patterns verified against React Flow official docs and existing backend code
- Pitfalls: HIGH -- derived from API analysis (form-data login, separate CRUD endpoints, position fields) and React Flow documented gotchas

**Research date:** 2026-04-04
**Valid until:** 2026-05-04 (30 days -- stable ecosystem, no breaking changes expected)
