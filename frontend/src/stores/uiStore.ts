import { create } from 'zustand';

interface UiState {
  leftSidebarCollapsed: boolean;
  rightPanelOpen: boolean;
  errorPanelExpanded: boolean;
  toggleLeftSidebar: () => void;
  setRightPanelOpen: (open: boolean) => void;
  setErrorPanelExpanded: (expanded: boolean) => void;
}

export const useUiStore = create<UiState>((set) => ({
  leftSidebarCollapsed: false,
  rightPanelOpen: true,
  errorPanelExpanded: false,

  toggleLeftSidebar: () =>
    set((state) => ({ leftSidebarCollapsed: !state.leftSidebarCollapsed })),

  setRightPanelOpen: (open) => set({ rightPanelOpen: open }),

  setErrorPanelExpanded: (expanded) => set({ errorPanelExpanded: expanded }),
}));
