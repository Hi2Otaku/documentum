import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Button } from "../ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "../ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import { CheckInDialog } from "./CheckInDialog";
import { LifecycleTransitionDialog } from "./LifecycleTransitionDialog";
import {
  checkoutDocument,
  cancelCheckout,
  type DocumentResponse,
} from "../../api/documents";

const LIFECYCLE_TRANSITIONS: Record<string, string[]> = {
  draft: ["review"],
  review: ["approved", "draft"],
  approved: ["archived"],
  archived: [],
};

interface DocumentActionsProps {
  document: DocumentResponse;
  currentUserId: string;
}

export function DocumentActions({
  document: doc,
  currentUserId,
}: DocumentActionsProps) {
  const queryClient = useQueryClient();
  const [checkInOpen, setCheckInOpen] = useState(false);
  const [cancelCheckoutOpen, setCancelCheckoutOpen] = useState(false);
  const [lifecycleTarget, setLifecycleTarget] = useState<string | null>(null);

  const checkoutMutation = useMutation({
    mutationFn: () => checkoutDocument(doc.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["documents", doc.id] });
      toast.success("Document checked out");
    },
    onError: (error: Error) => {
      toast.error("Action failed: " + error.message);
    },
  });

  const cancelCheckoutMutation = useMutation({
    mutationFn: () => cancelCheckout(doc.id),
    onSuccess: () => {
      setCancelCheckoutOpen(false);
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["documents", doc.id] });
      toast.success("Checkout cancelled");
    },
    onError: (error: Error) => {
      toast.error("Action failed: " + error.message);
    },
  });

  const isLockedBySelf = doc.locked_by === currentUserId;
  const isLockedByOther = doc.locked_by !== null && !isLockedBySelf;
  const isUnlocked = doc.locked_by === null;

  const lifecycleKey = (doc.lifecycle_state ?? "draft").toLowerCase();
  const validTransitions = LIFECYCLE_TRANSITIONS[lifecycleKey] ?? [];

  return (
    <div className="space-y-3">
      {/* Checkout / Checkin buttons */}
      <div className="flex gap-2">
        {isUnlocked && (
          <Button
            disabled={checkoutMutation.isPending}
            onClick={() => checkoutMutation.mutate()}
          >
            {checkoutMutation.isPending ? "Checking out..." : "Check Out"}
          </Button>
        )}

        {isLockedBySelf && (
          <>
            <Button onClick={() => setCheckInOpen(true)}>Check In</Button>
            <Button
              variant="outline"
              className="text-destructive hover:text-destructive"
              onClick={() => setCancelCheckoutOpen(true)}
            >
              Cancel Checkout
            </Button>
          </>
        )}

        {isLockedByOther && (
          <span className="text-sm text-muted-foreground py-2">
            Document is checked out by another user.
          </span>
        )}
      </div>

      {/* Lifecycle transition */}
      {validTransitions.length > 0 && (
        <Select
          value=""
          onValueChange={(value) => setLifecycleTarget(value)}
        >
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="Transition to..." />
          </SelectTrigger>
          <SelectContent>
            {validTransitions.map((state) => (
              <SelectItem key={state} value={state}>
                {state.charAt(0).toUpperCase() + state.slice(1)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}

      {/* Dialogs */}
      <CheckInDialog
        documentId={doc.id}
        open={checkInOpen}
        onOpenChange={setCheckInOpen}
      />

      <Dialog open={cancelCheckoutOpen} onOpenChange={setCancelCheckoutOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cancel Checkout</DialogTitle>
            <DialogDescription>
              Your lock will be released and no new version will be created. Are
              you sure?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setCancelCheckoutOpen(false)}
            >
              Keep Lock
            </Button>
            <Button
              variant="destructive"
              disabled={cancelCheckoutMutation.isPending}
              onClick={() => cancelCheckoutMutation.mutate()}
            >
              {cancelCheckoutMutation.isPending
                ? "Releasing..."
                : "Release Lock"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {lifecycleTarget && (
        <LifecycleTransitionDialog
          documentId={doc.id}
          currentState={lifecycleKey}
          targetState={lifecycleTarget}
          open={!!lifecycleTarget}
          onOpenChange={(open) => {
            if (!open) setLifecycleTarget(null);
          }}
        />
      )}
    </div>
  );
}
