# Phase 8: Visual Workflow Designer - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can design workflow templates through a web-based drag-and-drop interface instead of raw API calls. This is the first frontend phase — it establishes the React/TypeScript/Vite project, app shell, and component patterns that future phases (10, 11) will build on.

</domain>

<decisions>
## Implementation Decisions

### Canvas & Node Interaction
- **D-01:** Drag-from-sidebar palette for adding nodes. Left sidebar with draggable node types (Start, End, Manual, Auto). Collapsible to icons-only or hidden to maximize canvas space.
- **D-02:** Distinct shapes per node type — Start = green circle, Manual = blue rounded rectangle, Auto = orange hexagon, End = red filled circle. Color-coded for instant visual recognition.
- **D-03:** Color-coded edge styles — Normal flow = solid dark gray with arrow, Reject flow = dashed red with arrow, Conditional flow = dotted blue with diamond marker.
- **D-04:** Canvas features: minimap (corner overview), snap-to-grid, auto-layout button (dagre/elkjs algorithm for left-to-right arrangement), undo/redo (Ctrl+Z / Ctrl+Y).
- **D-05:** Delete via both keyboard (Delete/Backspace key) AND right-click context menu. Both patterns supported.
- **D-06:** Multi-select via rubber-band drag selection and Shift+click toggle. Group move/delete supported.
- **D-07:** Edge drawing via drag-from-handle-to-handle (React Flow's built-in source/target handle pattern).
- **D-08:** Nodes display name + key config hints on the canvas (performer name, trigger type) — not just the activity name. Richer info at a glance.

### Properties Panel & Forms
- **D-09:** Right sidebar properties panel. Opens when a node or edge is selected. Stays open while navigating between elements. Same panel location for both nodes and edges (edge shows flow type, condition expression, label).
- **D-10:** Performer assignment form: type dropdown (Supervisor, User, Group, Sequential, Runtime) with dynamic second field that changes based on type — user picker, group picker, ordered list with reorder/remove controls. Data fetched from existing backend APIs.
- **D-11:** Process variables managed in a dedicated tab in the properties panel (shown when no node is selected — template-level settings). Add/edit/delete variables with name, type (string/int/boolean/date), and default value.
- **D-12:** When no node/edge is selected, properties panel shows template-level settings with tabs: Template info (name, description) and Variables.

### Template Save/Load & Validation UX
- **D-13:** Manual save via Ctrl+S or toolbar save button. Unsaved changes indicator (dot on title/tab). User controls when changes persist to backend.
- **D-14:** Validation errors shown as inline markers (red border/badge on invalid nodes) PLUS a collapsible error panel at bottom listing all issues. Each error is clickable to pan/zoom to the problem node. Validation runs on demand (button) and automatically before install.
- **D-15:** Template list/browser page included — shows all templates with name, state (Draft/Active), version, last modified. Click to open in canvas editor. "New template" button.
- **D-16:** "Validate & Install" button in designer toolbar. One-click: runs validation, shows errors if any, installs if clean.

### App Shell & Project Setup
- **D-17:** Frontend project lives in `frontend/` directory within this repo (monorepo approach). Backend at `src/`, frontend at `frontend/`.
- **D-18:** Minimal app shell — login page, template list page, and designer canvas page. Simple top nav bar with app name, "Templates" link, and logout button. Future phases add more nav items.
- **D-19:** Routes: `/login`, `/templates` (list), `/templates/:id/edit` (designer canvas).
- **D-20:** Login form with username/password calling existing `/api/v1/auth/login` endpoint. JWT stored for authenticated requests. Protected routes redirect to login.
- **D-21:** Frontend added to Docker Compose as a dev service running Vite dev server. Mounts `frontend/` as volume. Full stack starts with one `docker compose up`.

### Claude's Discretion
- Loading skeleton and spinner designs
- Exact spacing, typography, and color palette (within shadcn/ui defaults)
- React Flow configuration details (edge routing algorithm, handle positions)
- API client structure (axios vs fetch, error handling patterns)
- Zustand store organization
- Auto-layout algorithm choice (dagre vs elkjs)
- CORS origin configuration details
- Undo/redo implementation approach (command pattern vs state snapshots)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — DESIGN-01 through DESIGN-07 acceptance criteria

### Backend API (existing, must integrate with)
- `src/app/routers/templates.py` — 17 endpoints for template CRUD, validation, install, versioning
- `src/app/schemas/template.py` — Pydantic schemas defining API request/response shapes
- `src/app/routers/auth.py` — Login endpoint for JWT token generation
- `src/app/routers/users.py` — User listing for performer pickers
- `src/app/routers/groups.py` — Group listing for performer pickers
- `src/app/main.py` — CORS middleware already configured (line 69)
- `src/app/schemas/common.py` — EnvelopeResponse wrapper used by all API responses

### Prior Phase Context
- `.planning/phases/03-workflow-template-design-api/03-CONTEXT.md` — Template API decisions (CRUD, validation, versioning)
- `.planning/phases/05-work-items-inbox/05-CONTEXT.md` — Envelope response pattern, service layer patterns

### Tech Stack
- `CLAUDE.md` — Full technology stack specification (React 19, Vite 6, TypeScript 5, shadcn/ui, React Flow, TanStack Query, Zustand, Tailwind CSS 4)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- No frontend code exists yet — this phase creates the entire frontend project from scratch
- Backend API is mature with 17 template endpoints, auth, user/group management

### Established Patterns
- Backend uses EnvelopeResponse[T] wrapper for all API responses — frontend API client must unwrap `data` field
- JWT auth via `/api/v1/auth/login` returns access token — frontend must send as Bearer token
- Template validation endpoint returns structured `ValidationResult` with `ValidationErrorDetail` items — maps directly to canvas error markers

### Integration Points
- FastAPI backend at `localhost:8000` (Docker) with CORS already configured
- Template API: GET/POST/PUT/DELETE for templates, activities, flows, variables
- Validation: POST `/api/v1/templates/{id}/validate`
- Install: POST `/api/v1/templates/{id}/install`
- Auth: POST `/api/v1/auth/login`
- Users: GET `/api/v1/users`
- Groups: GET `/api/v1/groups`
- Docker Compose in `docker-compose.yml` — needs new `frontend` service added

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches within the decisions above.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 08-visual-workflow-designer*
*Context gathered: 2026-04-04*
