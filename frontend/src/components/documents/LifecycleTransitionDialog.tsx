import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowRight } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "../ui/dialog";
import { Button } from "../ui/button";
import { LifecycleStateBadge } from "./LifecycleStateBadge";
import { transitionLifecycle } from "../../api/documents";

interface LifecycleTransitionDialogProps {
  documentId: string;
  currentState: string;
  targetState: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function LifecycleTransitionDialog({
  documentId,
  currentState,
  targetState,
  open,
  onOpenChange,
}: LifecycleTransitionDialogProps) {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: () => transitionLifecycle(documentId, targetState),
    onSuccess: () => {
      onOpenChange(false);
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({
        queryKey: ["documents", documentId],
      });
      toast.success("State changed to " + targetState);
    },
    onError: (error: Error) => {
      toast.error("Action failed: " + error.message);
    },
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Change Lifecycle State</DialogTitle>
          <DialogDescription>
            Confirm the lifecycle state transition for this document.
          </DialogDescription>
        </DialogHeader>

        <div className="flex items-center gap-3 py-4">
          <span className="text-sm text-muted-foreground">Current:</span>
          <LifecycleStateBadge state={currentState} />
          <ArrowRight size={16} className="text-muted-foreground" />
          <span className="text-sm text-muted-foreground">New:</span>
          <LifecycleStateBadge state={targetState} />
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Keep Current State
          </Button>
          <Button
            disabled={mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            {mutation.isPending ? "Transitioning..." : "Confirm Transition"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
