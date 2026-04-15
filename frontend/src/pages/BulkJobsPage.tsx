import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Layers } from "lucide-react";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "../components/ui/table";
import { BulkJobDialog } from "../components/documents/BulkJobDialog";
import { fetchBulkJobs, bulkKeys } from "../api/bulk";

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800 border-yellow-200",
  running: "bg-blue-100 text-blue-800 border-blue-200",
  completed: "bg-green-100 text-green-800 border-green-200",
  failed: "bg-red-100 text-red-800 border-red-200",
};

const TYPE_COLORS: Record<string, string> = {
  update: "bg-blue-50 text-blue-700 border-blue-200",
  delete: "bg-red-50 text-red-700 border-red-200",
  lifecycle: "bg-purple-50 text-purple-700 border-purple-200",
};

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

export function BulkJobsPage() {
  const [page, setPage] = useState(1);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: bulkKeys.list(page),
    queryFn: () => fetchBulkJobs(page),
  });

  const jobs = data?.data ?? [];
  const totalPages = data?.meta?.total_pages ?? 1;

  return (
    <div className="flex flex-col h-full">
      {/* Page header */}
      <div className="flex items-center gap-2 px-6 py-4 border-b">
        <Layers className="h-5 w-5 text-muted-foreground" />
        <h1 className="text-lg font-semibold">Bulk Operations</h1>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <span className="text-sm text-muted-foreground">Loading jobs...</span>
          </div>
        ) : jobs.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-center">
            <Layers className="h-10 w-10 text-muted-foreground mb-3" />
            <h3 className="text-base font-medium">No bulk operations yet</h3>
            <p className="text-sm text-muted-foreground mt-1">
              Select documents in the Browse page to start a bulk operation.
            </p>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="h-10 bg-secondary">
                <TableHead>Job Type</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Total</TableHead>
                <TableHead className="text-right">Succeeded</TableHead>
                <TableHead className="text-right">Failed</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Completed</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {jobs.map((job) => (
                <TableRow
                  key={job.id}
                  className="cursor-pointer hover:bg-accent/50"
                  onClick={() => setSelectedJobId(job.id)}
                >
                  <TableCell>
                    <Badge
                      variant="outline"
                      className={TYPE_COLORS[job.job_type] ?? ""}
                    >
                      {job.job_type}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant="outline"
                      className={STATUS_COLORS[job.status] ?? ""}
                    >
                      {job.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">{job.total_count}</TableCell>
                  <TableCell className="text-right">{job.success_count}</TableCell>
                  <TableCell className="text-right">{job.failure_count}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {formatRelativeTime(job.created_at)}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {job.completed_at ? formatRelativeTime(job.completed_at) : "-"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="h-12 flex items-center justify-between px-4 border-t shrink-0">
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

      {/* Job detail dialog */}
      <BulkJobDialog
        jobId={selectedJobId}
        open={!!selectedJobId}
        onClose={() => setSelectedJobId(null)}
      />
    </div>
  );
}
