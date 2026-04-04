---
phase: "08"
plan: "01"
subsystem: frontend/visual-designer
tags: [react, react-flow, vite, tailwind, drag-and-drop, workflow-designer]
dependency_graph:
  requires: [backend-template-api]
  provides: [react-frontend, workflow-canvas, custom-nodes, custom-edges, template-save-load]
  affects: []
tech_stack:
  added: [react-19, vite-8, xyflow-react, tailwindcss-4, tanstack-react-query-5, zustand-5, react-router-7, typescript-5]
  patterns: [custom-react-flow-nodes, zustand-ui-state, api-client-pattern, drag-and-drop-palette]
key_files:
  created:
    - frontend/src/pages/DesignerPage.tsx
    - frontend/src/pages/TemplateListPage.tsx
    - frontend/src/components/nodes/StartNode.tsx
    - frontend/src/components/nodes/EndNode.tsx
    - frontend/src/components/nodes/ManualNode.tsx
    - frontend/src/components/nodes/AutoNode.tsx
    - frontend/src/components/edges/NormalEdge.tsx
    - frontend/src/components/edges/RejectEdge.tsx
    - frontend/src/api/templates.ts
    - frontend/src/store/designerStore.ts
    - frontend/src/types/workflow.ts
    - frontend/src/main.tsx
    - frontend/vite.config.ts
  modified: []
decisions:
  - React Flow custom nodes use extends Record<string, unknown> for type compatibility
  - Save flow deletes and recreates all flows (simpler than diffing)
  - Vite proxy forwards /api to localhost:8000 for dev
  - Single commit for all 3 tasks due to tight coupling
metrics:
  duration: 5min
  completed: "2026-04-04T04:38:42Z"
---

# Phase 08 Plan 01: React Frontend Setup & Workflow Canvas Summary

React + Vite + TypeScript frontend with React Flow drag-and-drop workflow designer, custom activity nodes (Start/End/Manual/Auto), custom flow edges (Normal/Reject), template list page, and full save/load to backend API.

## What Was Built

### Task 1: React + Vite Project Initialization
- Scaffolded Vite 8 + React 19 + TypeScript 5 project in `frontend/`
- Installed @xyflow/react 12.x, @tanstack/react-query 5, zustand 5, react-router 7
- Configured Tailwind CSS 4 via @tailwindcss/vite plugin
- Configured Vite dev server proxy: `/api` -> `http://localhost:8000`
- Set up React Router with routes: `/templates` (list), `/designer/:id` (canvas)
- **Commit:** 29d8bd2

### Task 2: Custom Node & Edge Types
- Created 4 custom React Flow node components:
  - **StartNode**: Green circle with source handle
  - **EndNode**: Red circle with target handle
  - **ManualNode**: Blue card with performer info display
  - **AutoNode**: Purple card with method name display
- Created 2 custom edge types:
  - **NormalEdge**: Solid blue line with arrow marker
  - **RejectEdge**: Dashed red line with arrow marker
- Created Zustand store for designer state (selectedNodeId, panelOpen, dirty)
- Created TypeScript types mirroring all backend schemas
- **Commit:** 29d8bd2 (combined with Task 1)

### Task 3: Workflow Designer Canvas
- Created DesignerPage with full React Flow canvas integration
- Implemented sidebar palette with draggable activity types
- Implemented onDrop handler to create new nodes from palette drag
- Implemented edge creation via handle connection
- Created API client module with full template CRUD
- Implemented save: converts React Flow state to backend API calls (create/update activities, recreate flows)
- Implemented load: fetches template detail, converts to React Flow nodes/edges
- Added toolbar with Save, Validate, Install buttons wired to backend endpoints
- Added validation error display in sidebar
- Created TemplateListPage with template creation and navigation to designer
- **Commit:** 29d8bd2 (combined with Task 1)

## Deviations from Plan

None -- plan executed as written. All three tasks were committed together because they are tightly coupled (types, API client, nodes, edges, and canvas are interdependent).

## Decisions Made

1. **Record<string, unknown> extension**: React Flow 12.x requires node/edge data types to extend `Record<string, unknown>`. Added index signature to ActivityNodeData and FlowEdgeData interfaces.
2. **Flow save strategy**: Save operation deletes all existing flows and recreates them rather than diffing, which is simpler and avoids edge ID tracking complexity.
3. **Combined commit**: All 3 tasks committed as single atomic unit since the node components, edge components, types, API client, and canvas page are all interdependent.

## Known Stubs

None -- all components are fully wired to the backend API.

## Verification

- `npm run build` succeeds with zero TypeScript errors
- Production build output: 458KB JS (145KB gzipped), 32KB CSS (7KB gzipped)
- All 4 node types and 2 edge types are registered with React Flow
- Template list page queries backend API
- Designer page loads template data and renders on React Flow canvas
- Drag-and-drop palette creates new nodes on canvas
- Save button persists canvas state to backend API

## Self-Check: PASSED
