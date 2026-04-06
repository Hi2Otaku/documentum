import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "../ui/dialog";
import { Button } from "../ui/button";
import { Textarea } from "../ui/textarea";
import { rejectWorkItem } from "../../api/inbox";

interface RejectDialogProps {
  workItemId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function RejectDialog({
  workItemId,
  open,
  onOpenChange,
}: RejectDialogProps) {
  const [reason, setReason] = useState("");
  const [showValidation, setShowValidation] = useState(false);
  const queryClient = useQueryClient();

  const rejectMutation = useMutation({
    mutationFn: () => rejectWorkItem(workItemId, reason.trim()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["inbox"] });
      toast.success("Task rejected");
      setReason("");
      setShowValidation(false);
      onOpenChange(false);
    },
    onError: (error: Error) => {
      toast.error("Action failed: " + error.message);
    },
  });

  function handleSubmit() {
    if (!reason.trim()) {
      setShowValidation(true);
      return;
    }
    rejectMutation.mutate();
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Reject Task</DialogTitle>
          <DialogDescription>
            Provide a reason for rejecting this task. The workflow will be routed
            back to the previous activity.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          <Textarea
            placeholder="Reason for rejection (required)"
            value={reason}
            onChange={(e) => {
              setReason(e.target.value);
              if (e.target.value.trim()) setShowValidation(false);
            }}
            rows={3}
          />
          {showValidation && !reason.trim() && (
            <p className="text-sm text-destructive">
              A reason is required to reject a task.
            </p>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            disabled={!reason.trim() || rejectMutation.isPending}
            onClick={handleSubmit}
          >
            {rejectMutation.isPending ? "Rejecting..." : "Reject"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
