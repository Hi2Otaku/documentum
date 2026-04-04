import { useEffect } from 'react';
import { useDesignerStore } from '../stores/designerStore';

interface KeyboardShortcutOptions {
  onSave: () => void;
}

export function useKeyboardShortcuts({ onSave }: KeyboardShortcutOptions) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const isMod = e.ctrlKey || e.metaKey;
      const activeTag = document.activeElement?.tagName?.toLowerCase();
      const isInput = activeTag === 'input' || activeTag === 'textarea' || activeTag === 'select';

      // Ctrl+S / Cmd+S: Save
      if (isMod && e.key === 's') {
        e.preventDefault();
        onSave();
        return;
      }

      // Ctrl+Shift+Z / Cmd+Shift+Z: Redo
      if (isMod && e.shiftKey && e.key === 'Z') {
        e.preventDefault();
        useDesignerStore.getState().redo();
        return;
      }

      // Ctrl+Z / Cmd+Z: Undo
      if (isMod && !e.shiftKey && e.key === 'z') {
        e.preventDefault();
        useDesignerStore.getState().undo();
        return;
      }

      // Ctrl+Y / Cmd+Y: Redo
      if (isMod && e.key === 'y') {
        e.preventDefault();
        useDesignerStore.getState().redo();
        return;
      }

      // Ctrl+A / Cmd+A: Select all (only when not in input)
      if (isMod && e.key === 'a' && !isInput) {
        e.preventDefault();
        const { nodes, edges } = useDesignerStore.getState();
        useDesignerStore.setState({
          nodes: nodes.map((n) => ({ ...n, selected: true })),
          edges: edges.map((e) => ({ ...e, selected: true })),
        });
        return;
      }

      // Delete / Backspace: Delete selected elements (only when not in input)
      if ((e.key === 'Delete' || e.key === 'Backspace') && !isInput) {
        const { nodes, edges } = useDesignerStore.getState();
        const selectedNodeIds = nodes.filter((n) => n.selected).map((n) => n.id);
        const selectedEdgeIds = edges.filter((e) => e.selected).map((e) => e.id);
        if (selectedNodeIds.length > 0 || selectedEdgeIds.length > 0) {
          useDesignerStore.getState().deleteElements(selectedNodeIds, selectedEdgeIds);
        }
        return;
      }

      // Escape: Clear selection
      if (e.key === 'Escape') {
        useDesignerStore.getState().clearSelection();
        return;
      }
    };

    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [onSave]);
}
