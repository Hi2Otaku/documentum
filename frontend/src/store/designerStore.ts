import { create } from 'zustand';

interface DesignerState {
  /** Currently selected node ID */
  selectedNodeId: string | null;
  /** Whether the properties panel is visible */
  panelOpen: boolean;
  /** Whether there are unsaved changes */
  dirty: boolean;

  selectNode: (id: string | null) => void;
  togglePanel: (open?: boolean) => void;
  markDirty: () => void;
  markClean: () => void;
}

export const useDesignerStore = create<DesignerState>((set) => ({
  selectedNodeId: null,
  panelOpen: false,
  dirty: false,

  selectNode: (id) =>
    set({ selectedNodeId: id, panelOpen: id !== null }),

  togglePanel: (open) =>
    set((s) => ({ panelOpen: open ?? !s.panelOpen })),

  markDirty: () => set({ dirty: true }),
  markClean: () => set({ dirty: false }),
}));
