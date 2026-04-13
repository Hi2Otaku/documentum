import type { FolderPathSegment } from "../../api/folders";

interface FolderBreadcrumbProps {
  path: FolderPathSegment[];
  onNavigate?: (folderId: string) => void;
}

export function FolderBreadcrumb({ path, onNavigate }: FolderBreadcrumbProps) {
  if (path.length === 0) return null;

  return (
    <nav className="flex items-center gap-1 text-sm text-muted-foreground flex-wrap">
      {path.map((segment, idx) => {
        const isLast = idx === path.length - 1;
        return (
          <span key={segment.id} className="flex items-center gap-1">
            {idx > 0 && <span className="text-muted-foreground/50">/</span>}
            {isLast ? (
              <span className="text-foreground font-medium">{segment.name}</span>
            ) : (
              <button
                className="hover:underline hover:text-foreground transition-colors"
                onClick={() => onNavigate?.(segment.id)}
              >
                {segment.name}
              </button>
            )}
          </span>
        );
      })}
    </nav>
  );
}
