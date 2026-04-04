import { useNavigate } from 'react-router';
import {
  ArrowLeft,
  Save,
  ShieldCheck,
  Undo2,
  Redo2,
  LayoutGrid,
  Loader2,
} from 'lucide-react';
import { useDesignerStore } from '../../stores/designerStore';
import { getLayoutedElements } from '../../hooks/useAutoLayout';

interface ToolbarProps {
  templateName: string;
  onSave: () => void;
  onValidateInstall: () => void;
  saving: boolean;
  validating: boolean;
}

export function Toolbar({
  templateName,
  onSave,
  onValidateInstall,
  saving,
  validating,
}: ToolbarProps) {
  const navigate = useNavigate();
  const isDirty = useDesignerStore((s) => s.isDirty);
  const undoStack = useDesignerStore((s) => s.undoStack);
  const redoStack = useDesignerStore((s) => s.redoStack);
  const nodes = useDesignerStore((s) => s.nodes);
  const edges = useDesignerStore((s) => s.edges);

  const handleBack = () => {
    if (isDirty) {
      const confirmed = window.confirm(
        'You have unsaved changes. Are you sure you want to leave?',
      );
      if (!confirmed) return;
    }
    navigate('/templates');
  };

  const handleUndo = () => {
    useDesignerStore.getState().undo();
  };

  const handleRedo = () => {
    useDesignerStore.getState().redo();
  };

  const handleAutoLayout = () => {
    const { nodes: layoutedNodes, edges: layoutedEdges } =
      getLayoutedElements(nodes, edges);
    useDesignerStore.getState().pushSnapshot();
    useDesignerStore.setState({
      nodes: layoutedNodes,
      edges: layoutedEdges,
      isDirty: true,
    });
  };

  return (
    <div className="h-12 border-b flex items-center justify-between px-4 shrink-0 bg-background">
      {/* Left section */}
      <div className="flex items-center gap-3">
        <button
          onClick={handleBack}
          className="p-1.5 rounded hover:bg-muted transition-colors"
          aria-label="Back to templates"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>

        <span className="text-lg font-semibold">{templateName}</span>

        {isDirty && (
          <span
            className="w-2 h-2 rounded-full bg-amber-500"
            title="Unsaved changes"
          />
        )}
      </div>

      {/* Right section */}
      <div className="flex items-center gap-2">
        {/* Save */}
        <button
          onClick={onSave}
          disabled={saving}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded text-sm font-medium border hover:bg-muted transition-colors disabled:opacity-50"
          aria-label="Save Template"
        >
          {saving ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Save className="w-4 h-4" />
          )}
          Save Template
        </button>

        {/* Validate & Install */}
        <button
          onClick={onValidateInstall}
          disabled={validating}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
          aria-label="Validate and Install"
        >
          {validating ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <ShieldCheck className="w-4 h-4" />
          )}
          Validate & Install
        </button>

        {/* Undo */}
        <button
          onClick={handleUndo}
          disabled={undoStack.length === 0}
          className="p-1.5 rounded hover:bg-muted transition-colors disabled:opacity-30"
          aria-label="Undo"
          title="Undo"
        >
          <Undo2 className="w-4 h-4" />
        </button>

        {/* Redo */}
        <button
          onClick={handleRedo}
          disabled={redoStack.length === 0}
          className="p-1.5 rounded hover:bg-muted transition-colors disabled:opacity-30"
          aria-label="Redo"
          title="Redo"
        >
          <Redo2 className="w-4 h-4" />
        </button>

        {/* Auto-layout */}
        <button
          onClick={handleAutoLayout}
          className="p-1.5 rounded hover:bg-muted transition-colors"
          aria-label="Auto-arrange nodes"
          title="Auto-arrange nodes"
        >
          <LayoutGrid className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
