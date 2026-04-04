import { useEffect, useRef } from 'react';
import { useReactFlow } from '@xyflow/react';
import { Trash2, MousePointer, LayoutGrid, Maximize } from 'lucide-react';
import { useDesignerStore } from '../../stores/designerStore';
import { getLayoutedElements } from '../../hooks/useAutoLayout';

interface ContextMenuProps {
  position: { x: number; y: number } | null;
  target: { type: 'node' | 'edge' | 'pane'; id?: string } | null;
  onClose: () => void;
}

export function ContextMenu({ position, target, onClose }: ContextMenuProps) {
  const { fitView } = useReactFlow();
  const menuRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    if (!position) return;
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as HTMLElement)) {
        onClose();
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [position, onClose]);

  // Close on Escape
  useEffect(() => {
    if (!position) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [position, onClose]);

  if (!position || !target) return null;

  const handleDelete = () => {
    if (target.type === 'node' && target.id) {
      useDesignerStore.getState().deleteElements([target.id], []);
    } else if (target.type === 'edge' && target.id) {
      useDesignerStore.getState().deleteElements([], [target.id]);
    }
    onClose();
  };

  const handleSelectAll = () => {
    const { nodes, edges } = useDesignerStore.getState();
    useDesignerStore.setState({
      nodes: nodes.map((n) => ({ ...n, selected: true })),
      edges: edges.map((e) => ({ ...e, selected: true })),
    });
    onClose();
  };

  const handleAutoLayout = () => {
    const { nodes, edges } = useDesignerStore.getState();
    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(nodes, edges);
    useDesignerStore.getState().pushSnapshot();
    useDesignerStore.setState({
      nodes: layoutedNodes,
      edges: layoutedEdges,
      isDirty: true,
    });
    onClose();
  };

  const handleFitView = () => {
    fitView({ duration: 300 });
    onClose();
  };

  return (
    <div
      ref={menuRef}
      className="fixed z-50 min-w-[160px] rounded-md border bg-popover p-1 text-popover-foreground shadow-md"
      style={{ left: position.x, top: position.y }}
    >
      {(target.type === 'node' || target.type === 'edge') && (
        <button
          onClick={handleDelete}
          className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm text-red-600 hover:bg-muted transition-colors"
        >
          <Trash2 className="w-4 h-4" />
          Delete
        </button>
      )}

      {target.type === 'pane' && (
        <>
          <button
            onClick={handleSelectAll}
            className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm hover:bg-muted transition-colors"
          >
            <MousePointer className="w-4 h-4" />
            Select All
          </button>
          <button
            onClick={handleAutoLayout}
            className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm hover:bg-muted transition-colors"
          >
            <LayoutGrid className="w-4 h-4" />
            Auto-Layout
          </button>
          <button
            onClick={handleFitView}
            className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm hover:bg-muted transition-colors"
          >
            <Maximize className="w-4 h-4" />
            Fit View
          </button>
        </>
      )}
    </div>
  );
}
