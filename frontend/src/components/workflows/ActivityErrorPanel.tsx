import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { AlertTriangle, RefreshCw, SkipForward, ChevronDown, ChevronRight } from "lucide-react";
import { Button } from "../ui/button";
import { Card, CardContent } from "../ui/card";
import { Badge } from "../ui/badge";
import { retryActivity, skipActivity } from "../../api/workflows";
import type { ActivityInstanceResponse } from "../../api/workflows";

interface ActivityErrorPanelProps {
  workflowId: string;
  activities: ActivityInstanceResponse[];
}

export function ActivityErrorPanel({ workflowId, activities }: ActivityErrorPanelProps) {
  const errorActivities = activities.filter((a) => a.state === "error");

  if (errorActivities.length === 0) return null;

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-destructive flex items-center gap-2">
        <AlertTriangle className="w-4 h-4" />
        Failed Activities ({errorActivities.length})
      </h3>
      {errorActivities.map((activity) => (
        <ErrorActivityCard
          key={activity.id}
          workflowId={workflowId}
          activity={activity}
        />
      ))}
    </div>
  );
}

function ErrorActivityCard({
  workflowId,
  activity,
}: {
  workflowId: string;
  activity: ActivityInstanceResponse;
}) {
  const [detailsOpen, setDetailsOpen] = useState(false);
  const queryClient = useQueryClient();

  const retryMutation = useMutation({
    mutationFn: () => retryActivity(workflowId, activity.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workflows"] });
      queryClient.invalidateQueries({ queryKey: ["workflows", workflowId] });
      toast("Activity requeued for retry");
    },
    onError: (error: Error) => {
      toast(`Retry failed: ${error.message}`);
    },
  });

  const skipMutation = useMutation({
    mutationFn: () => skipActivity(workflowId, activity.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workflows"] });
      queryClient.invalidateQueries({ queryKey: ["workflows", workflowId] });
      toast("Activity skipped, workflow advanced");
    },
    onError: (error: Error) => {
      toast(`Skip failed: ${error.message}`);
    },
  });

  return (
    <Card className="border-destructive/50">
      <CardContent className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-destructive" />
            <span className="text-sm font-medium">
              Activity {activity.activity_template_id.slice(0, 8)}
            </span>
            <Badge variant="destructive" className="text-xs">
              Error
            </Badge>
          </div>
          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              size="sm"
              onClick={() => retryMutation.mutate()}
              disabled={retryMutation.isPending || skipMutation.isPending}
            >
              <RefreshCw className="w-3 h-3 mr-1" />
              Retry
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => skipMutation.mutate()}
              disabled={retryMutation.isPending || skipMutation.isPending}
            >
              <SkipForward className="w-3 h-3 mr-1" />
              Skip
            </Button>
          </div>
        </div>

        {activity.error_message && (
          <p className="text-sm text-destructive bg-destructive/10 rounded p-2">
            {activity.error_message}
          </p>
        )}

        {activity.error_details && (
          <div>
            <button
              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
              onClick={() => setDetailsOpen(!detailsOpen)}
            >
              {detailsOpen ? (
                <ChevronDown className="w-3 h-3" />
              ) : (
                <ChevronRight className="w-3 h-3" />
              )}
              Error Details
            </button>
            {detailsOpen && (
              <pre className="mt-2 text-xs bg-muted rounded p-2 overflow-x-auto max-h-48 overflow-y-auto">
                {JSON.stringify(activity.error_details, null, 2)}
              </pre>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
