import { useState, useRef, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Upload,
  Download,
  FileArchive,
  Package,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Badge } from "../components/ui/badge";
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "../components/ui/table";
import {
  importPackage,
  fetchImportExportJobs,
  downloadExport,
  importExportKeys,
} from "../api/importExport";
import type { ImportExportJobResponse } from "../api/importExport";

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800 border-yellow-200",
  running: "bg-blue-100 text-blue-800 border-blue-200",
  completed: "bg-green-100 text-green-800 border-green-200",
  failed: "bg-red-100 text-red-800 border-red-200",
};

const TYPE_COLORS: Record<string, string> = {
  export: "bg-purple-50 text-purple-700 border-purple-200",
  import: "bg-teal-50 text-teal-700 border-teal-200",
};

type ConflictStrategy = "skip" | "overwrite" | "rename";

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = Date.now();
  const diffMs = now - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHour < 24) return `${diffHour}h ago`;
  if (diffDay < 30) return `${diffDay}d ago`;
  return date.toLocaleDateString();
}

export default function ImportExportPage() {
  const queryClient = useQueryClient();

  // Import form state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [targetFolderId, setTargetFolderId] = useState("");
  const [conflictStrategy, setConflictStrategy] =
    useState<ConflictStrategy>("skip");
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Job history state
  const [page, setPage] = useState(1);
  const [expandedJobId, setExpandedJobId] = useState<string | null>(null);

  // Fetch jobs
  const { data, isLoading } = useQuery({
    queryKey: importExportKeys.list(page),
    queryFn: () => fetchImportExportJobs(page),
    refetchInterval: (query) => {
      const jobs = query.state.data?.data ?? [];
      const hasActive = jobs.some(
        (j) => j.status === "pending" || j.status === "running",
      );
      return hasActive ? 3000 : false;
    },
  });

  const jobs = data?.data ?? [];
  const totalPages = data?.meta?.total_pages ?? 1;

  // Import mutation
  const importMutation = useMutation({
    mutationFn: () => {
      if (!selectedFile) throw new Error("No file selected");
      return importPackage(
        selectedFile,
        targetFolderId || undefined,
        conflictStrategy,
      );
    },
    onSuccess: () => {
      setSelectedFile(null);
      setTargetFolderId("");
      setConflictStrategy("skip");
      if (fileInputRef.current) fileInputRef.current.value = "";
      queryClient.invalidateQueries({ queryKey: importExportKeys.all });
    },
  });

  // Download mutation
  const downloadMutation = useMutation({
    mutationFn: (jobId: string) => downloadExport(jobId),
  });

  // Drag and drop handlers
  const handleDragOver = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      if (!isDragging) setIsDragging(true);
    },
    [isDragging],
  );

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file && file.name.endsWith(".zip")) {
      setSelectedFile(file);
    }
  }, []);

  function toggleExpanded(jobId: string) {
    setExpandedJobId((prev) => (prev === jobId ? null : jobId));
  }

  return (
    <div className="flex flex-col h-full">
      {/* Page header */}
      <div className="flex items-center gap-2 px-6 py-4 border-b">
        <Package className="h-5 w-5 text-muted-foreground" />
        <h1 className="text-lg font-semibold">Import / Export</h1>
      </div>

      <div className="flex-1 overflow-auto p-6 space-y-6">
        {/* Import Section */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Upload className="h-4 w-4" />
              Import Package
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* File upload zone */}
            <div
              className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                isDragging
                  ? "border-primary bg-primary/5"
                  : "border-muted-foreground/25 hover:border-primary/50"
              }`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <FileArchive className="h-10 w-10 text-muted-foreground mx-auto mb-3" />
              {selectedFile ? (
                <p className="text-sm font-medium">{selectedFile.name}</p>
              ) : (
                <>
                  <p className="text-sm font-medium">
                    Drop a ZIP file here, or click to browse
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Accepts .zip export packages
                  </p>
                </>
              )}
              <input
                ref={fileInputRef}
                type="file"
                accept=".zip"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0] ?? null;
                  setSelectedFile(file);
                }}
              />
            </div>

            {/* Target folder */}
            <div className="space-y-2">
              <Label htmlFor="target-folder">
                Target Folder ID (optional)
              </Label>
              <Input
                id="target-folder"
                placeholder="Root (default)"
                value={targetFolderId}
                onChange={(e) => setTargetFolderId(e.target.value)}
              />
            </div>

            {/* Conflict strategy */}
            <div className="space-y-2">
              <Label>Conflict Strategy</Label>
              <div className="flex gap-4">
                {(
                  [
                    { value: "skip", label: "Skip" },
                    { value: "overwrite", label: "Overwrite" },
                    { value: "rename", label: "Rename" },
                  ] as const
                ).map((opt) => (
                  <label
                    key={opt.value}
                    className="flex items-center gap-2 cursor-pointer"
                  >
                    <input
                      type="radio"
                      name="conflict-strategy"
                      value={opt.value}
                      checked={conflictStrategy === opt.value}
                      onChange={() => setConflictStrategy(opt.value)}
                      className="accent-primary"
                    />
                    <span className="text-sm">{opt.label}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Error */}
            {importMutation.isError && (
              <p className="text-sm text-destructive">
                {(importMutation.error as Error).message}
              </p>
            )}

            {/* Submit */}
            <Button
              onClick={() => importMutation.mutate()}
              disabled={!selectedFile || importMutation.isPending}
            >
              {importMutation.isPending ? "Importing..." : "Import"}
            </Button>
          </CardContent>
        </Card>

        {/* Job History Section */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <FileArchive className="h-4 w-4" />
              Job History
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex items-center justify-center h-32">
                <span className="text-sm text-muted-foreground">
                  Loading jobs...
                </span>
              </div>
            ) : jobs.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-32 text-center">
                <Package className="h-8 w-8 text-muted-foreground mb-2" />
                <p className="text-sm text-muted-foreground">
                  No import/export jobs yet
                </p>
              </div>
            ) : (
              <>
                <Table>
                  <TableHeader>
                    <TableRow className="h-10 bg-secondary">
                      <TableHead className="w-8" />
                      <TableHead>Type</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Total</TableHead>
                      <TableHead className="text-right">Success</TableHead>
                      <TableHead className="text-right">Failed</TableHead>
                      <TableHead>Created</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {jobs.map((job) => (
                      <JobRow
                        key={job.id}
                        job={job}
                        expanded={expandedJobId === job.id}
                        onToggle={() => toggleExpanded(job.id)}
                        onDownload={() => downloadMutation.mutate(job.id)}
                        isDownloading={
                          downloadMutation.isPending &&
                          downloadMutation.variables === job.id
                        }
                      />
                    ))}
                  </TableBody>
                </Table>

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-between mt-4">
                    <span className="text-sm text-muted-foreground">
                      Page {page} of {totalPages}
                    </span>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={page === 1}
                        onClick={() => setPage((p) => p - 1)}
                      >
                        Previous
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={page >= totalPages}
                        onClick={() => setPage((p) => p + 1)}
                      >
                        Next
                      </Button>
                    </div>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// --- Job Row sub-component ---

interface JobRowProps {
  job: ImportExportJobResponse;
  expanded: boolean;
  onToggle: () => void;
  onDownload: () => void;
  isDownloading: boolean;
}

function JobRow({
  job,
  expanded,
  onToggle,
  onDownload,
  isDownloading,
}: JobRowProps) {
  return (
    <>
      <TableRow className="cursor-pointer hover:bg-accent/50" onClick={onToggle}>
        <TableCell className="w-8 px-2">
          {expanded ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          )}
        </TableCell>
        <TableCell>
          <Badge variant="outline" className={TYPE_COLORS[job.job_type] ?? ""}>
            {job.job_type}
          </Badge>
        </TableCell>
        <TableCell>
          <Badge variant="outline" className={STATUS_COLORS[job.status] ?? ""}>
            {job.status}
          </Badge>
        </TableCell>
        <TableCell className="text-right">{job.total_count}</TableCell>
        <TableCell className="text-right">{job.success_count}</TableCell>
        <TableCell className="text-right">{job.failure_count}</TableCell>
        <TableCell className="text-sm text-muted-foreground">
          {formatRelativeTime(job.created_at)}
        </TableCell>
        <TableCell onClick={(e) => e.stopPropagation()}>
          {job.job_type === "export" &&
            job.status === "completed" &&
            job.download_ready && (
              <Button
                variant="outline"
                size="sm"
                onClick={onDownload}
                disabled={isDownloading}
              >
                <Download className="h-3.5 w-3.5 mr-1" />
                {isDownloading ? "..." : "Download"}
              </Button>
            )}
        </TableCell>
      </TableRow>

      {/* Expanded details row */}
      {expanded && job.results && job.results.length > 0 && (
        <TableRow>
          <TableCell colSpan={8} className="bg-muted/30 px-8 py-3">
            <div className="space-y-1">
              <p className="text-xs font-medium text-muted-foreground mb-2">
                Item Results
              </p>
              <div className="max-h-48 overflow-auto space-y-1">
                {job.results.map((r, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-2 text-xs font-mono"
                  >
                    <Badge
                      variant="outline"
                      className={
                        r.status === "success"
                          ? "bg-green-50 text-green-700 border-green-200"
                          : "bg-red-50 text-red-700 border-red-200"
                      }
                    >
                      {r.status}
                    </Badge>
                    <span className="truncate">{r.document_id}</span>
                    {r.error && (
                      <span className="text-destructive ml-2">
                        {r.error}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </TableCell>
        </TableRow>
      )}
    </>
  );
}
