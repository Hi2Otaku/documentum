import { Play, User, Zap, Square, GitBranch, ChevronLeft, ChevronRight } from 'lucide-react';
import { useUiStore } from '../../stores/uiStore';

interface PaletteItem {
  nodeType: string;
  label: string;
  icon: React.ReactNode;
  accentColor: string;
}

const PALETTE_ITEMS: PaletteItem[] = [
  {
    nodeType: 'startNode',
    label: 'Start',
    icon: <Play className="w-4 h-4" />,
    accentColor: 'border-l-green-500',
  },
  {
    nodeType: 'manualNode',
    label: 'Manual',
    icon: <User className="w-4 h-4" />,
    accentColor: 'border-l-blue-500',
  },
  {
    nodeType: 'autoNode',
    label: 'Auto',
    icon: <Zap className="w-4 h-4" />,
    accentColor: 'border-l-orange-500',
  },
  {
    nodeType: 'subWorkflowNode',
    label: 'Sub-Workflow',
    icon: <GitBranch className="w-4 h-4" />,
    accentColor: 'border-l-purple-500',
  },
  {
    nodeType: 'endNode',
    label: 'End',
    icon: <Square className="w-4 h-4" />,
    accentColor: 'border-l-red-500',
  },
];

export function NodePalette() {
  const leftSidebarCollapsed = useUiStore((s) => s.leftSidebarCollapsed);
  const toggleLeftSidebar = useUiStore((s) => s.toggleLeftSidebar);

  const handleDragStart = (event: React.DragEvent, nodeType: string) => {
    event.dataTransfer.setData('application/reactflow', nodeType);
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <aside
      className={`${
        leftSidebarCollapsed ? 'w-12' : 'w-[220px]'
      } border-r bg-background flex flex-col transition-all duration-200 shrink-0`}
    >
      {/* Toggle button */}
      <button
        onClick={toggleLeftSidebar}
        className="flex items-center justify-center h-10 border-b hover:bg-muted transition-colors"
        aria-label={leftSidebarCollapsed ? 'Expand palette' : 'Collapse palette'}
      >
        {leftSidebarCollapsed ? (
          <ChevronRight className="w-4 h-4" />
        ) : (
          <ChevronLeft className="w-4 h-4" />
        )}
      </button>

      {/* Section header */}
      {!leftSidebarCollapsed && (
        <div className="px-3 pt-3 pb-2">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase">
            Activities
          </h2>
        </div>
      )}

      {/* Palette items */}
      <div className="flex flex-col gap-1 px-2">
        {PALETTE_ITEMS.map((item) => (
          <div
            key={item.nodeType}
            role="button"
            draggable={true}
            onDragStart={(e) => handleDragStart(e, item.nodeType)}
            aria-label={`Drag to add ${item.label} activity`}
            className={`flex items-center gap-2 h-11 rounded cursor-grab active:cursor-grabbing
              border-l-4 ${item.accentColor} bg-muted/50 hover:bg-muted transition-colors
              ${leftSidebarCollapsed ? 'justify-center px-1' : 'px-3'}
            `}
            title={leftSidebarCollapsed ? item.label : undefined}
          >
            {item.icon}
            {!leftSidebarCollapsed && (
              <span className="text-sm font-medium">{item.label}</span>
            )}
          </div>
        ))}
      </div>
    </aside>
  );
}
