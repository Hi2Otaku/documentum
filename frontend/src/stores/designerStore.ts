import {
  type Node,
  type Edge,
  type NodeChange,
  type EdgeChange,
  applyNodeChanges,
  applyEdgeChanges,
} from '@xyflow/react';
import { create } from 'zustand';
import type { ActivityNodeData, FlowEdgeData } from '../types/designer';

const MAX_UNDO_STACK = 50;

interface Snapshot {
  nodes: Node[];
  edges: Edge[];
}

interface DesignerState {
  nodes: Node[];
  edges: Edge[];
  selectedNodeId: string | null;
  selectedEdgeId: string | null;
  isDirty: boolean;
  undoStack: Snapshot[];
  redoStack: Snapshot[];
  templateId: string | null;

  setNodes: (nodes: Node[]) => void;
  setEdges: (edges: Edge[]) => void;
  onNodesChange: (changes: NodeChange[]) => void;
  onEdgesChange: (changes: EdgeChange[]) => void;
  addNode: (node: Node) => void;
  addEdge: (edge: Edge) => void;
  deleteElements: (nodeIds: string[], edgeIds: string[]) => void;
  updateNodeData: (nodeId: string, data: Partial<ActivityNodeData>) => void;
  updateEdgeData: (edgeId: string, data: Partial<FlowEdgeData>) => void;
  setSelectedNode: (id: string | null) => void;
  setSelectedEdge: (id: string | null) => void;
  clearSelection: () => void;
  pushSnapshot: () => void;
  undo: () => void;
  redo: () => void;
  setClean: () => void;
  reset: () => void;
  loadTemplate: (templateId: string, nodes: Node[], edges: Edge[]) => void;
}

export const useDesignerStore = create<DesignerState>((set, get) => ({
  nodes: [],
  edges: [],
  selectedNodeId: null,
  selectedEdgeId: null,
  isDirty: false,
  undoStack: [],
  redoStack: [],
  templateId: null,

  setNodes: (nodes) => set({ nodes }),

  setEdges: (edges) => set({ edges }),

  onNodesChange: (changes) =>
    set((state) => ({
      nodes: applyNodeChanges(changes, state.nodes),
      isDirty: true,
    })),

  onEdgesChange: (changes) =>
    set((state) => ({
      edges: applyEdgeChanges(changes, state.edges),
      isDirty: true,
    })),

  addNode: (node) => {
    get().pushSnapshot();
    set((state) => ({
      nodes: [...state.nodes, node],
      isDirty: true,
    }));
  },

  addEdge: (edge) => {
    get().pushSnapshot();
    set((state) => ({
      edges: [...state.edges, edge],
      isDirty: true,
    }));
  },

  deleteElements: (nodeIds, edgeIds) => {
    get().pushSnapshot();
    const nodeIdSet = new Set(nodeIds);
    const edgeIdSet = new Set(edgeIds);
    set((state) => ({
      nodes: state.nodes.filter((n) => !nodeIdSet.has(n.id)),
      edges: state.edges.filter((e) => !edgeIdSet.has(e.id)),
      isDirty: true,
    }));
  },

  updateNodeData: (nodeId, data) => {
    get().pushSnapshot();
    set((state) => ({
      nodes: state.nodes.map((n) =>
        n.id === nodeId ? { ...n, data: { ...n.data, ...data } } : n,
      ),
      isDirty: true,
    }));
  },

  updateEdgeData: (edgeId, data) => {
    get().pushSnapshot();
    set((state) => ({
      edges: state.edges.map((e) =>
        e.id === edgeId ? { ...e, data: { ...e.data, ...data } } : e,
      ),
      isDirty: true,
    }));
  },

  setSelectedNode: (id) =>
    set({ selectedNodeId: id, selectedEdgeId: null }),

  setSelectedEdge: (id) =>
    set({ selectedEdgeId: id, selectedNodeId: null }),

  clearSelection: () =>
    set({ selectedNodeId: null, selectedEdgeId: null }),

  pushSnapshot: () =>
    set((state) => {
      const snapshot: Snapshot = {
        nodes: structuredClone(state.nodes),
        edges: structuredClone(state.edges),
      };
      const undoStack = [...state.undoStack, snapshot];
      if (undoStack.length > MAX_UNDO_STACK) {
        undoStack.shift();
      }
      return { undoStack, redoStack: [] };
    }),

  undo: () =>
    set((state) => {
      if (state.undoStack.length === 0) return state;
      const undoStack = [...state.undoStack];
      const snapshot = undoStack.pop()!;
      const redoStack = [
        ...state.redoStack,
        { nodes: structuredClone(state.nodes), edges: structuredClone(state.edges) },
      ];
      return {
        undoStack,
        redoStack,
        nodes: snapshot.nodes,
        edges: snapshot.edges,
      };
    }),

  redo: () =>
    set((state) => {
      if (state.redoStack.length === 0) return state;
      const redoStack = [...state.redoStack];
      const snapshot = redoStack.pop()!;
      const undoStack = [
        ...state.undoStack,
        { nodes: structuredClone(state.nodes), edges: structuredClone(state.edges) },
      ];
      return {
        undoStack,
        redoStack,
        nodes: snapshot.nodes,
        edges: snapshot.edges,
      };
    }),

  setClean: () => set({ isDirty: false }),

  reset: () =>
    set({
      nodes: [],
      edges: [],
      selectedNodeId: null,
      selectedEdgeId: null,
      isDirty: false,
      undoStack: [],
      redoStack: [],
      templateId: null,
    }),

  loadTemplate: (templateId, nodes, edges) =>
    set({
      templateId,
      nodes,
      edges,
      undoStack: [],
      redoStack: [],
      isDirty: false,
      selectedNodeId: null,
      selectedEdgeId: null,
    }),
}));
