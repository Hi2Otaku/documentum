import { useState } from "react";
import { ChevronRight, Archive, Folder as FolderIcon, MoreHorizontal, Search } from "lucide-react";
import { cn } from "../../lib/utils";
import type { FolderTreeNode } from "../../api/folders";

export interface SmartFolderNode {
  id: string;
  name: string;
}

interface FolderTreeProps {
  tree: FolderTreeNode[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onContextAction?: (action: string, node: FolderTreeNode) => void;
  smartFolders?: SmartFolderNode[];
  selectedSmartFolderId?: string | null;
  onSmartFolderSelect?: (id: string) => void;
}

interface FolderTreeNodeItemProps {
  node: FolderTreeNode;
  depth: number;
  selectedId: string | null;
  onSelect: (id: string) => void;
  onContextAction?: (action: string, node: FolderTreeNode) => void;
}

function FolderTreeNodeItem({
  node,
  depth,
  selectedId,
  onSelect,
  onContextAction,
}: FolderTreeNodeItemProps) {
  const [expanded, setExpanded] = useState(node.is_cabinet);
  const [menuOpen, setMenuOpen] = useState(false);
  const hasChildren = node.children.length > 0;
  const isSelected = selectedId === node.id;

  function handleChevronClick(e: React.MouseEvent) {
    e.stopPropagation();
    setExpanded((prev) => !prev);
  }

  function handleMenuClick(e: React.MouseEvent) {
    e.stopPropagation();
    setMenuOpen((prev) => !prev);
  }

  function handleContextAction(action: string) {
    setMenuOpen(false);
    onContextAction?.(action, node);
  }

  return (
    <div>
      <div
        className={cn(
          "group flex items-center gap-1 py-1 pr-1 rounded cursor-pointer hover:bg-accent hover:text-accent-foreground relative",
          isSelected && "bg-accent text-accent-foreground",
        )}
        style={{ paddingLeft: depth * 16 + 8 }}
        onClick={() => onSelect(node.id)}
      >
        {/* Chevron toggle */}
        <span
          className={cn(
            "h-4 w-4 flex-shrink-0 transition-transform duration-150",
            hasChildren ? "opacity-100" : "opacity-0 pointer-events-none",
            expanded && "rotate-90",
          )}
          onClick={handleChevronClick}
        >
          <ChevronRight className="h-4 w-4" />
        </span>

        {/* Icon */}
        {node.is_cabinet ? (
          <Archive className="h-4 w-4 flex-shrink-0 text-amber-600" />
        ) : (
          <FolderIcon className="h-4 w-4 flex-shrink-0 text-blue-500" />
        )}

        {/* Name */}
        <span className="flex-1 text-sm truncate">{node.name}</span>

        {/* Document count badge */}
        {node.document_count > 0 && (
          <span className="text-xs text-muted-foreground px-1 rounded bg-muted">
            {node.document_count}
          </span>
        )}

        {/* Context menu trigger */}
        {onContextAction && (
          <button
            className="opacity-0 group-hover:opacity-100 h-5 w-5 flex items-center justify-center rounded hover:bg-muted flex-shrink-0"
            onClick={handleMenuClick}
            title="More actions"
          >
            <MoreHorizontal className="h-3 w-3" />
          </button>
        )}

        {/* Context menu dropdown */}
        {menuOpen && (
          <div className="absolute right-1 top-full z-50 mt-1 w-40 rounded border bg-popover shadow-md text-sm">
            <button
              className="w-full px-3 py-1.5 text-left hover:bg-accent"
              onClick={() => handleContextAction("new-subfolder")}
            >
              New Subfolder
            </button>
            <button
              className="w-full px-3 py-1.5 text-left hover:bg-accent"
              onClick={() => handleContextAction("rename")}
            >
              Rename
            </button>
            <button
              className="w-full px-3 py-1.5 text-left hover:bg-accent"
              onClick={() => handleContextAction("move")}
            >
              Move
            </button>
            <button
              className="w-full px-3 py-1.5 text-left hover:bg-accent"
              onClick={() => handleContextAction("copy")}
            >
              Copy
            </button>
            <button
              className="w-full px-3 py-1.5 text-left hover:bg-accent text-destructive"
              onClick={() => handleContextAction("delete")}
            >
              Delete
            </button>
          </div>
        )}
      </div>

      {/* Children */}
      {expanded && hasChildren && (
        <div>
          {node.children.map((child) => (
            <FolderTreeNodeItem
              key={child.id}
              node={child}
              depth={depth + 1}
              selectedId={selectedId}
              onSelect={onSelect}
              onContextAction={onContextAction}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function FolderTree({
  tree,
  selectedId,
  onSelect,
  onContextAction,
  smartFolders,
  selectedSmartFolderId,
  onSmartFolderSelect,
}: FolderTreeProps) {
  if (tree.length === 0 && (!smartFolders || smartFolders.length === 0)) {
    return (
      <p className="text-sm text-muted-foreground px-4 py-2">
        No cabinets yet. Click "New Cabinet" to create one.
      </p>
    );
  }

  return (
    <div className="py-1">
      {tree.map((node) => (
        <FolderTreeNodeItem
          key={node.id}
          node={node}
          depth={0}
          selectedId={selectedId}
          onSelect={onSelect}
          onContextAction={onContextAction}
        />
      ))}

      {/* Smart folder nodes */}
      {smartFolders && smartFolders.length > 0 && (
        <>
          <div className="mx-3 my-2 border-t" />
          <p className="px-3 pb-1 text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
            Smart Folders
          </p>
          {smartFolders.map((sf) => {
            const isSelected = selectedSmartFolderId === sf.id;
            return (
              <div
                key={sf.id}
                className={cn(
                  "flex items-center gap-1 py-1 pr-1 rounded cursor-pointer hover:bg-accent hover:text-accent-foreground",
                  isSelected && "bg-accent text-accent-foreground",
                )}
                style={{ paddingLeft: 8 }}
                onClick={() => onSmartFolderSelect?.(sf.id)}
              >
                {/* Spacer matching chevron width */}
                <span className="h-4 w-4 flex-shrink-0" />
                <Search className="h-4 w-4 flex-shrink-0 text-violet-500" />
                <span className="flex-1 text-sm truncate">{sf.name}</span>
              </div>
            );
          })}
        </>
      )}
    </div>
  );
}
