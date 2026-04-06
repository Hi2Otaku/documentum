import { useQuery } from "@tanstack/react-query";
import { Download } from "lucide-react";
import { Skeleton } from "../ui/skeleton";
import { Button } from "../ui/button";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "../ui/tooltip";
import {
  fetchVersions,
  downloadVersionUrl,
  type DocumentVersionResponse,
} from "../../api/documents";

function authHeaders(): HeadersInit {
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

interface VersionHistoryListProps {
  documentId: string;
}

export function VersionHistoryList({ documentId }: VersionHistoryListProps) {
  const { data: versions, isLoading } = useQuery({
    queryKey: ["documents", documentId, "versions"],
    queryFn: () => fetchVersions(documentId),
    enabled: !!documentId,
  });

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-12 w-full" />
      </div>
    );
  }

  if (!versions || versions.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">No versions available.</p>
    );
  }

  const sorted = [...versions].sort(
    (a, b) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );

  async function handleDownload(
    versionId: string,
    filename: string,
  ) {
    const res = await fetch(downloadVersionUrl(documentId, versionId), {
      headers: authHeaders(),
    });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div>
      {sorted.map((v: DocumentVersionResponse, idx: number) => (
        <div
          key={v.id}
          className={`flex items-center gap-3 py-2 ${idx < sorted.length - 1 ? "border-b" : ""}`}
        >
          <div className="flex-1 min-w-0">
            <div className="text-sm font-semibold">v{v.version_label}</div>
            <div className="text-xs text-muted-foreground">
              {new Date(v.created_at).toLocaleDateString()} by{" "}
              {v.created_by ?? "Unknown"}
            </div>
            <div className="text-xs text-muted-foreground font-mono">
              {v.content_hash.slice(0, 8)}
            </div>
          </div>
          <span className="text-xs text-muted-foreground whitespace-nowrap">
            {formatSize(v.content_size)}
          </span>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={() => handleDownload(v.id, v.filename)}
              >
                <Download size={16} />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Download this version</TooltipContent>
          </Tooltip>
        </div>
      ))}
    </div>
  );
}
