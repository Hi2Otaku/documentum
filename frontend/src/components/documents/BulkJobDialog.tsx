import { useQuery } from "@tanstack/react-query";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Progress } from "../ui/progress";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "../ui/dialog";
import { fetchBulkJob, bulkKeys } from "../../api/bulk";

interface BulkJobDialogProps {
  jobId: string | null;
  open: boolean;
  onClose: () => void;
}

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800 border-yellow-200",
  running: "bg-blue-100 text-blue-800 border-blue-200",
  completed: "bg-green-100 text-green-800 border-green-200",
  failed: "bg-red-100 text-red-800 border-red-200",
};

export function BulkJobDialog({ jobId, open, onClose }: BulkJobDialogProps) {
  const { data: job } = useQuery({
    queryKey: bulkKeys.detail(jobId ?? ""),
    queryFn: () => fetchBulkJob(jobId!),
    enabled: open && !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "pending" || status === "running") return 2000;
      return false;
    },
  });

  if (!job) {
    return (
      <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Bulk Job</DialogTitle>
            <DialogDescription>Loading job details...</DialogDescription>
          </DialogHeader>
          <div className="flex items-center justify-center py-8">
            <div className="text-sm text-muted-foreground">Loading...</div>
          </div>
        </DialogContent>
      </Dialog>
    );
  }

  const processed = job.success_count + job.failure_count;
  const progressPercent = job.total_count > 0
    ? Math.round((processed / job.total_count) * 100)
    : 0;

  const isFinished = job.status === "completed" || job.status === "failed";

  const failedItems = job.results?.filter((r) => r.status === "failed") ?? [];

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            Bulk {job.job_type.charAt(0).toUpperCase() + job.job_type.slice(1)} Job
          </DialogTitle>
          <DialogDescription>
            Job ID: {job.id}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Status badge */}
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">Status:</span>
            <Badge
              variant="outline"
              className={STATUS_COLORS[job.status] ?? ""}
            >
              {job.status}
            </Badge>
          </div>

          {/* Progress */}
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Progress</span>
              <span>{processed} / {job.total_count}</span>
            </div>
            <Progress value={progressPercent} className="h-2" />
          </div>

          {/* Completion stats */}
          {isFinished && (
            <div className="flex gap-4 text-sm">
              <span className="text-green-600 font-medium">
                Succeeded: {job.success_count}
              </span>
              <span className="text-red-600 font-medium">
                Failed: {job.failure_count}
              </span>
            </div>
          )}

          {/* Failed items */}
          {failedItems.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-medium text-destructive">
                Failed Items ({failedItems.length})
              </p>
              <div className="max-h-40 overflow-auto rounded border p-2 space-y-1">
                {failedItems.map((item) => (
                  <div
                    key={item.document_id}
                    className="text-xs flex justify-between gap-2"
                  >
                    <code className="text-muted-foreground truncate">
                      {item.document_id}
                    </code>
                    <span className="text-destructive shrink-0">
                      {item.error ?? "Unknown error"}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button onClick={onClose}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
