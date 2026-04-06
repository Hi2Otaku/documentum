import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Button } from "../ui/button";
import { Pause, Play, Trash2 } from "lucide-react";
import { haltWorkflow, resumeWorkflow } from "../../api/workflows";
import { useAuthStore } from "../../stores/authStore";

interface AdminActionBarProps {
  workflowId: string;
  workflowState: string;
  onTerminateClick: () => void;
}

export function AdminActionBar({
  workflowId,
  workflowState,
  onTerminateClick,
}: AdminActionBarProps) {
  const isSuperuser = useAuthStore((s) => s.isSuperuser);
  const queryClient = useQueryClient();

  const haltMutation = useMutation({
    mutationFn: () => haltWorkflow(workflowId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workflows"] });
      queryClient.invalidateQueries({ queryKey: ["workflows", workflowId] });
      toast("Workflow halted");
    },
    onError: (error: Error) => {
      toast(`Action failed: ${error.message}`);
    },
  });

  const resumeMutation = useMutation({
    mutationFn: () => resumeWorkflow(workflowId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workflows"] });
      queryClient.invalidateQueries({ queryKey: ["workflows", workflowId] });
      toast("Workflow resumed");
    },
    onError: (error: Error) => {
      toast(`Action failed: ${error.message}`);
    },
  });

  if (!isSuperuser) return null;

  return (
    <div className="flex items-center gap-2">
      {workflowState === "running" && (
        <Button
          variant="outline"
          size="sm"
          onClick={() => haltMutation.mutate()}
          disabled={haltMutation.isPending}
        >
          <Pause className="w-4 h-4 mr-2" />
          Halt
        </Button>
      )}
      {workflowState === "halted" && (
        <Button
          variant="outline"
          size="sm"
          onClick={() => resumeMutation.mutate()}
          disabled={resumeMutation.isPending}
        >
          <Play className="w-4 h-4 mr-2" />
          Resume
        </Button>
      )}
      {(workflowState === "running" || workflowState === "halted") && (
        <Button variant="destructive" size="sm" onClick={onTerminateClick}>
          <Trash2 className="w-4 h-4 mr-2" />
          Terminate
        </Button>
      )}
    </div>
  );
}
