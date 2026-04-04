---
phase: "08"
plan: "03"
subsystem: frontend/visual-designer
tags: [react-flow, custom-nodes, custom-edges, zustand, dagre, undo-redo]
dependency_graph:
  requires: [react-frontend, xyflow-react, designer-types]
  provides: [custom-node-components, custom-edge-components, designer-store, auto-layout]
  affects: [designer-canvas-page]
tech_stack:
  added: [lucide-react, dagrejs-dagre]
  patterns: [custom-react-flow-nodes, zustand-undo-redo, dagre-auto-layout, clip-path-hexagon]
key_files:
  created:
    - frontend/src/types/designer.ts
    - frontend/src/components/edges/ConditionalEdge.tsx
    - frontend/src/stores/designerStore.ts
    - frontend/src/hooks/useAutoLayout.ts
  modified:
    - frontend/src/components/nodes/StartNode.tsx
    - frontend/src/components/nodes/EndNode.tsx
    - frontend/src/components/nodes/ManualNode.tsx
    - frontend/src/components/nodes/AutoNode.tsx
    - frontend/src/components/edges/NormalEdge.tsx
    - frontend/src/components/edges/RejectEdge.tsx
    - frontend/src/components/edges/index.ts
    - frontend/src/components/nodes/index.ts
    - frontend/src/pages/DesignerPage.tsx
    - frontend/package.json
decisions:
  - designer.ts types created with name field (not label) per UI-SPEC; backendId added for backward compatibility with existing DesignerPage
  - Node index registers both old keys (start/end/manual/auto) and new keys (startNode/endNode/manualNode/autoNode) for compatibility
  - Auto-layout hook is a pure function (getLayoutedElements) not a React hook, keeping it simple and testable
metrics:
  duration: 5min
  completed: "2026-04-04T07:00:00Z"
---

# Phase 08 Plan 03: Custom Nodes, Edges, Designer Store & Auto-Layout Summary

Four distinct React Flow node components (green circle Start, blue rectangle Manual, orange hexagon Auto, red circle End) with Lucide icons, three edge types (solid gray Normal, dashed red Reject, dotted blue Conditional) using getSmoothStepPath, plus a full-featured Zustand designer store with 50-entry undo/redo and dagre left-to-right auto-layout.

## What Was Built

### Task 1: Custom Node Components (4 types) and Edge Components (3 types)

- **StartNode**: Green circle (60px, bg-green-500) with Play icon from lucide-react, source Handle at Position.Right, label below showing data.name, selected ring via ring-primary
- **EndNode**: Red circle (60px, bg-red-500) with Square icon, target Handle at Position.Left, label below, selected ring
- **ManualNode**: Blue rounded rectangle (min-w-160px, bg-blue-500) showing name (font-semibold) and performer hint (performerType: performerId or "No performer"), both handles
- **AutoNode**: Orange hexagon via CSS clip-path on inner div (bg-orange-500), outer wrapper carries selection ring, shows name and method hint ("Method: X" or "No method"), both handles
- **NormalEdge**: Solid line, stroke #374151 (gray-700), strokeWidth 2, getSmoothStepPath, markerEnd arrowclosed, optional displayLabel in white pill
- **RejectEdge**: Dashed line (strokeDasharray "8 4"), stroke #ef4444 (red-500), label defaults to "Reject" with red text/border
- **ConditionalEdge**: Dotted line (strokeDasharray "2 4"), stroke #3b82f6 (blue-500), label shows displayLabel or truncated conditionExpression (20 chars + "...")
- Created designer.ts types file with ActivityNodeData (name, activityType, performerType, etc.) and FlowEdgeData (flowType, conditionExpression, displayLabel)
- Updated DesignerPage to import from designer.ts types and use name instead of label
- **Commit:** 428c8a5

### Task 2: Designer Zustand Store and Auto-Layout Hook

- **Designer Store** (frontend/src/stores/designerStore.ts):
  - State: nodes, edges, selectedNodeId, selectedEdgeId, isDirty, undoStack, redoStack, templateId
  - Node/edge mutation actions: setNodes, setEdges, onNodesChange (applyNodeChanges), onEdgesChange (applyEdgeChanges)
  - CRUD actions: addNode, addEdge, deleteElements, updateNodeData, updateEdgeData -- all push snapshot before mutating
  - Selection: setSelectedNode, setSelectedEdge, clearSelection
  - Undo/redo: pushSnapshot (structuredClone, 50 max), undo (pop undo -> push redo), redo (pop redo -> push undo)
  - Lifecycle: setClean, reset, loadTemplate (sets state, clears history)
- **Auto-Layout Hook** (frontend/src/hooks/useAutoLayout.ts):
  - getLayoutedElements function using @dagrejs/dagre
  - Graph config: rankdir LR, nodesep 50, ranksep 80
  - Node dimensions: 60x60 for start/end, 172x64 for manual/auto
  - Centers nodes by subtracting half width/height from dagre positions
- Updated DesignerPage to use new store path and API (setSelectedNode, setClean)
- **Commit:** 5cebd5c

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added backendId to designer.ts ActivityNodeData and FlowEdgeData**
- **Found during:** Task 1
- **Issue:** DesignerPage accesses node.data.backendId which was in the old workflow.ts type but not in the new designer.ts type. TypeScript build failed.
- **Fix:** Added optional backendId field to both ActivityNodeData and FlowEdgeData in designer.ts
- **Files modified:** frontend/src/types/designer.ts

**2. [Rule 3 - Blocking] Updated DesignerPage imports and API calls for new store**
- **Found during:** Task 2
- **Issue:** DesignerPage imported from old store path (store/designerStore) and used old API (selectNode, markDirty, markClean) that no longer exist in new store
- **Fix:** Updated import path to stores/designerStore, replaced selectNode with setSelectedNode, markClean with setClean, markDirty with direct setState
- **Files modified:** frontend/src/pages/DesignerPage.tsx

**3. [Rule 3 - Blocking] Removed unused ActivityNodeData import from useAutoLayout.ts**
- **Found during:** Task 2 verification
- **Issue:** TypeScript noUnusedLocals strict mode rejected unused import
- **Fix:** Removed the import
- **Files modified:** frontend/src/hooks/useAutoLayout.ts

## Known Stubs

None -- all components are fully implemented with correct shapes, colors, and functionality.

## Verification

- `npm run build` completes successfully (462KB JS, 31KB CSS)
- `npx tsc --noEmit` passes with zero errors
- All 4 node components export named functions (StartNode, EndNode, ManualNode, AutoNode)
- All 3 edge components use getSmoothStepPath
- Designer store has undo/redo with pushSnapshot (50 max)
- Auto-layout uses dagre with LR direction

## Self-Check: PASSED
