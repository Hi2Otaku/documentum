import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Card, CardContent } from "../ui/card";
import { Button } from "../ui/button";
import { Separator } from "../ui/separator";
import { Skeleton } from "../ui/skeleton";
import { WorkItemStateBadge } from "./WorkItemStateBadge";
import { PriorityIcon } from "./PriorityIcon";
import { CommentList } from "./CommentList";
import { CommentCompose } from "./CommentCompose";
import { CompleteDialog } from "./CompleteDialog";
import { RejectDialog } from "./RejectDialog";
import { DelegateDialog } from "./DelegateDialog";
import { fetchInboxItem, fetchComments, acquireWorkItem } from "../../api/inbox";
import { useAuthStore } from "../../stores/authStore";

interface InboxDetailPanelProps {
  workItemId: string | null;
}

export function InboxDetailPanel({ workItemId }: InboxDetailPanelProps) {
  const userId = useAuthStore((s) => s.userId);
  const queryClient = useQueryClient();
  const [completeOpen, setCompleteOpen] = useState(false);
  const [rejectOpen, setRejectOpen] = useState(false);
  const [delegateOpen, setDelegateOpen] = useState(false);

  const { data: item, isLoading: itemLoading } = useQuery({
    queryKey: ["inbox", workItemId],
    queryFn: () => fetchInboxItem(workItemId!),
    enabled: !!workItemId,
  });

  const { data: comments, isLoading: commentsLoading } = useQuery({
    queryKey: ["inbox", workItemId, "comments"],
    queryFn: () => fetchComments(workItemId!),
    enabled: !!workItemId,
  });

  const acquireMutation = useMutation({
    mutationFn: () => acquireWorkItem(workItemId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["inbox"] });
      queryClient.invalidateQueries({ queryKey: ["inbox", workItemId] });
      toast.success("Task acquired");
    },
    onError: (error: Error) => {
      toast.error("Action failed: " + error.message);
    },
  });

  // No selection state
  if (!workItemId) {
    return (
      <div className="flex flex-col items-center justify-center h-full">
        <h3 className="text-lg font-semibold">Select a work item</h3>
        <p className="text-sm text-muted-foreground mt-1">
          Click a row in the table to view its details.
        </p>
      </div>
    );
  }

  // Loading state
  if (itemLoading || !item) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-6 w-48" />
        <Card>
          <CardContent className="p-4 space-y-3">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
          </CardContent>
        </Card>
        <div className="flex gap-2">
          <Skeleton className="h-9 w-20" />
          <Skeleton className="h-9 w-20" />
          <Skeleton className="h-9 w-20" />
        </div>
      </div>
    );
  }

  const instructions = item.instructions || item.activity.instructions;

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      {/* Header */}
      <div className="p-6">
        <div className="flex items-center gap-2">
          <h2 className="text-base font-semibold">{item.activity.name}</h2>
          <WorkItemStateBadge state={item.state} />
          <PriorityIcon priority={item.priority} />
        </div>
      </div>

      {/* Workflow Context */}
      <div className="px-6 pb-4">
        <Card>
          <CardContent className="p-4 space-y-0">
            <div className="flex justify-between py-1">
              <span className="text-xs text-muted-foreground">Template</span>
              <span className="text-sm">{item.workflow.template_name}</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-xs text-muted-foreground">Workflow State</span>
              <WorkItemStateBadge state={item.workflow.state} />
            </div>
            <div className="flex justify-between py-1">
              <span className="text-xs text-muted-foreground">Assigned To</span>
              <span className="text-sm text-muted-foreground">
                {item.performer_id || "Unassigned"}
              </span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-xs text-muted-foreground">Due Date</span>
              <span className="text-sm text-muted-foreground">
                {item.due_date
                  ? new Date(item.due_date).toLocaleDateString()
                  : "No due date"}
              </span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-xs text-muted-foreground">Created</span>
              <span className="text-sm text-muted-foreground">
                {new Date(item.created_at).toLocaleString()}
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Instructions */}
      {instructions && (
        <div className="px-6 pb-4">
          <p className="text-sm">{instructions}</p>
        </div>
      )}

      {/* Actions */}
      <div className="px-6 pb-4" id="inbox-actions-slot">
        <div className="flex gap-2">
          {item.state === "available" && (
            <Button
              variant="default"
              size="sm"
              disabled={acquireMutation.isPending}
              onClick={() => acquireMutation.mutate()}
            >
              {acquireMutation.isPending ? "Acquiring..." : "Acquire"}
            </Button>
          )}
          {item.state === "acquired" && item.performer_id === userId && (
            <>
              <Button
                variant="default"
                size="sm"
                onClick={() => setCompleteOpen(true)}
              >
                Complete
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="text-destructive hover:text-destructive"
                onClick={() => setRejectOpen(true)}
              >
                Reject
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setDelegateOpen(true)}
              >
                Delegate
              </Button>
            </>
          )}
        </div>
        <CompleteDialog
          workItemId={workItemId}
          open={completeOpen}
          onOpenChange={setCompleteOpen}
        />
        <RejectDialog
          workItemId={workItemId}
          open={rejectOpen}
          onOpenChange={setRejectOpen}
        />
        <DelegateDialog
          open={delegateOpen}
          onOpenChange={setDelegateOpen}
        />
      </div>

      <Separator />

      {/* Comments */}
      <div className="p-6">
        <h3 className="text-base font-semibold mb-3">Comments</h3>
        {commentsLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
          </div>
        ) : (
          <CommentList comments={comments ?? []} />
        )}
        <div className="mt-4">
          <CommentCompose workItemId={workItemId} />
        </div>
      </div>
    </div>
  );
}
