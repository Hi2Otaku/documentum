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
import { Input } from "../ui/input";
import { terminateWorkflow } from "../../api/workflows";

interface TerminateDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workflowId: string;
}

export function TerminateDialog({
  open,
  onOpenChange,
  workflowId,
}: TerminateDialogProps) {
  const [terminateInput, setTerminateInput] = useState("");
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: () => terminateWorkflow(workflowId),
    onSuccess: () => {
      onOpenChange(false);
      queryClient.invalidateQueries({ queryKey: ["workflows"] });
      queryClient.invalidateQueries({ queryKey: ["workflows", workflowId] });
      toast("Workflow terminated");
    },
    onError: (error: Error) => {
      toast(`Action failed: ${error.message}`);
    },
  });

  function handleOpenChange(nextOpen: boolean) {
    if (!nextOpen) {
      setTerminateInput("");
    }
    onOpenChange(nextOpen);
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Terminate Workflow</DialogTitle>
          <DialogDescription>
            This cannot be undone. All pending work items will be cancelled.
          </DialogDescription>
        </DialogHeader>
        <div className="py-4">
          <Input
            placeholder="Type TERMINATE to confirm"
            value={terminateInput}
            onChange={(e) => setTerminateInput(e.target.value)}
          />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => handleOpenChange(false)}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            disabled={terminateInput !== "TERMINATE" || mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            Terminate
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
