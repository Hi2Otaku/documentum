import { Button } from "../ui/button";
import type { VirtualDocumentChildResponse } from "../../api/virtualDocuments";

interface VirtualDocumentChildrenListProps {
  children: VirtualDocumentChildResponse[];
  virtualDocId: string;
  onReorder: (childIds: string[]) => void;
  onRemove: (childId: string) => void;
}

export function VirtualDocumentChildrenList({
  children,
  virtualDocId: _virtualDocId,
  onReorder,
  onRemove,
}: VirtualDocumentChildrenListProps) {
  if (children.length === 0) {
    return (
      <div className="py-6 text-center text-sm text-muted-foreground">
        No children added yet. Add documents to this virtual document.
      </div>
    );
  }

  const sorted = [...children].sort((a, b) => a.order_index - b.order_index);

  function moveUp(index: number) {
    if (index <= 0) return;
    const ids = sorted.map((c) => c.id);
    [ids[index - 1], ids[index]] = [ids[index], ids[index - 1]];
    onReorder(ids);
  }

  function moveDown(index: number) {
    if (index >= sorted.length - 1) return;
    const ids = sorted.map((c) => c.id);
    [ids[index], ids[index + 1]] = [ids[index + 1], ids[index]];
    onReorder(ids);
  }

  return (
    <div className="space-y-0">
      {sorted.map((child, index) => (
        <div
          key={child.id}
          className="flex items-center gap-2 px-2 py-2 border-b last:border-b-0"
        >
          <span className="text-xs text-muted-foreground w-6 text-center shrink-0">
            {index + 1}
          </span>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">
              {child.child_title ?? "Untitled"}
            </p>
            {child.child_filename && (
              <p className="text-xs text-muted-foreground truncate">
                {child.child_filename}
              </p>
            )}
          </div>
          <div className="flex items-center gap-1 shrink-0">
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              disabled={index === 0}
              onClick={() => moveUp(index)}
              title="Move up"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="m18 15-6-6-6 6" />
              </svg>
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              disabled={index === sorted.length - 1}
              onClick={() => moveDown(index)}
              title="Move down"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="m6 9 6 6 6-6" />
              </svg>
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 text-destructive hover:text-destructive"
              onClick={() => onRemove(child.id)}
              title="Remove"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M18 6 6 18" />
                <path d="m6 6 12 12" />
              </svg>
            </Button>
          </div>
        </div>
      ))}
    </div>
  );
}
