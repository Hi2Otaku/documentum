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
import { completeWorkItem, addComment } from "../../api/inbox";

interface CompleteDialogProps {
  workItemId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CompleteDialog({
  workItemId,
  open,
  onOpenChange,
}: CompleteDialogProps) {
  const [comment, setComment] = useState("");
  const queryClient = useQueryClient();

  const completeMutation = useMutation({
    mutationFn: async () => {
      if (comment.trim()) {
        await addComment(workItemId, comment.trim());
      }
      return completeWorkItem(workItemId, {
        output_variables: {},
        selected_path: null,
        next_performer_id: null,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["inbox"] });
      toast.success("Task completed");
      setComment("");
      onOpenChange(false);
    },
    onError: (error: Error) => {
      toast.error("Action failed: " + error.message);
    },
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Complete Task</DialogTitle>
          <DialogDescription>
            Mark this task as complete. You can optionally add a comment.
          </DialogDescription>
        </DialogHeader>
        <Textarea
          placeholder="Add a comment (optional)"
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          rows={3}
        />
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            variant="default"
            disabled={completeMutation.isPending}
            onClick={() => completeMutation.mutate()}
          >
            {completeMutation.isPending ? "Completing..." : "Complete"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
