import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Archive, Trash2, Plus, ShieldAlert } from "lucide-react";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import { Skeleton } from "../ui/skeleton";
import { Textarea } from "../ui/textarea";
import { Label } from "../ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "../ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import {
  fetchRetentionStatus,
  fetchRetentionPolicies,
  assignRetentionPolicy,
  removeRetentionAssignment,
  placeLegalHold,
  releaseLegalHold,
  type DocumentRetentionResponse,
  type LegalHoldResponse,
} from "../../api/retention";

interface RetentionStatusPanelProps {
  documentId: string;
}

export function RetentionStatusPanel({
  documentId,
}: RetentionStatusPanelProps) {
  const [assignDialogOpen, setAssignDialogOpen] = useState(false);
  const [holdDialogOpen, setHoldDialogOpen] = useState(false);
  const [selectedPolicyId, setSelectedPolicyId] = useState("");
  const [holdReason, setHoldReason] = useState("");
  const queryClient = useQueryClient();

  const { data: status, isLoading } = useQuery({
    queryKey: ["retention-status", documentId],
    queryFn: () => fetchRetentionStatus(documentId),
    enabled: !!documentId,
  });

  const { data: policies = [] } = useQuery({
    queryKey: ["retention-policies"],
    queryFn: fetchRetentionPolicies,
    enabled: assignDialogOpen,
  });

  const assignMutation = useMutation({
    mutationFn: () => assignRetentionPolicy(documentId, selectedPolicyId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["retention-status", documentId],
      });
      setAssignDialogOpen(false);
      setSelectedPolicyId("");
    },
  });

  const removeMutation = useMutation({
    mutationFn: (retentionId: string) =>
      removeRetentionAssignment(documentId, retentionId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["retention-status", documentId],
      });
    },
  });

  const holdMutation = useMutation({
    mutationFn: () => placeLegalHold(documentId, holdReason),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["retention-status", documentId],
      });
      setHoldDialogOpen(false);
      setHoldReason("");
    },
  });

  const releaseMutation = useMutation({
    mutationFn: (holdId: string) => releaseLegalHold(documentId, holdId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["retention-status", documentId],
      });
    },
  });

  if (isLoading) {
    return (
      <div>
        <h4 className="text-sm font-medium flex items-center gap-1 mb-2">
          <Archive className="h-4 w-4" /> Retention & Legal Holds
        </h4>
        <div className="space-y-2">
          <Skeleton className="h-6 w-32" />
          <Skeleton className="h-8 w-full" />
        </div>
      </div>
    );
  }

  if (!status) {
    return (
      <div>
        <h4 className="text-sm font-medium flex items-center gap-1 mb-2">
          <Archive className="h-4 w-4" /> Retention & Legal Holds
        </h4>
        <p className="text-sm text-muted-foreground">
          Unable to load retention status.
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-medium flex items-center gap-1">
          <Archive className="h-4 w-4" /> Retention & Legal Holds
        </h4>
      </div>

      {/* Status badges */}
      <div className="flex items-center gap-2 mb-3">
        {status.is_retained ? (
          <Badge className="bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200">
            Retained
          </Badge>
        ) : (
          <Badge variant="outline">No retention</Badge>
        )}
        {status.is_held && (
          <Badge variant="destructive">
            <ShieldAlert className="h-3 w-3 mr-1" />
            Legal Hold
          </Badge>
        )}
      </div>

      {!status.is_deletable && status.deletion_blocked_reason && (
        <p className="text-xs text-destructive mb-3">
          Deletion blocked: {status.deletion_blocked_reason}
        </p>
      )}

      {/* Active retentions */}
      {status.active_retentions.length > 0 && (
        <div className="mb-3">
          <h5 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1.5">
            Active Retentions ({status.active_retentions.length})
          </h5>
          <div className="space-y-1.5">
            {status.active_retentions.map((r: DocumentRetentionResponse) => (
              <div
                key={r.id}
                className="flex items-center justify-between text-sm border rounded-md px-3 py-2 group"
              >
                <div>
                  <span className="font-medium">
                    {r.policy_name ?? r.policy_id}
                  </span>
                  <div className="text-xs text-muted-foreground">
                    Applied: {new Date(r.applied_at).toLocaleDateString()}{" "}
                    &middot; Expires:{" "}
                    {new Date(r.expires_at).toLocaleDateString()}
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100"
                  onClick={() => removeMutation.mutate(r.id)}
                  title="Remove retention"
                >
                  <Trash2 className="h-3 w-3 text-destructive" />
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Active legal holds */}
      {status.active_holds.length > 0 && (
        <div className="mb-3">
          <h5 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1.5">
            Legal Holds ({status.active_holds.length})
          </h5>
          <div className="space-y-1.5">
            {status.active_holds.map((h: LegalHoldResponse) => (
              <div
                key={h.id}
                className="flex items-center justify-between text-sm border rounded-md px-3 py-2 group"
              >
                <div>
                  <span className="font-medium">{h.reason}</span>
                  <div className="text-xs text-muted-foreground">
                    Placed: {new Date(h.placed_at).toLocaleDateString()}
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100"
                  onClick={() => releaseMutation.mutate(h.id)}
                  title="Release legal hold"
                >
                  <Trash2 className="h-3 w-3 text-destructive" />
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Action buttons */}
      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setAssignDialogOpen(true)}
        >
          <Plus className="h-3 w-3 mr-1" /> Assign Policy
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setHoldDialogOpen(true)}
        >
          <ShieldAlert className="h-3 w-3 mr-1" /> Place Legal Hold
        </Button>
      </div>

      {/* Assign Policy Dialog */}
      <Dialog open={assignDialogOpen} onOpenChange={setAssignDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Assign Retention Policy</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Retention Policy</Label>
              <Select
                value={selectedPolicyId}
                onValueChange={setSelectedPolicyId}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a policy..." />
                </SelectTrigger>
                <SelectContent>
                  {policies.map((p) => (
                    <SelectItem key={p.id} value={p.id}>
                      {p.name} ({p.retention_period_days} days -{" "}
                      {p.disposition_action})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex justify-end gap-2">
              <Button
                variant="outline"
                onClick={() => setAssignDialogOpen(false)}
              >
                Cancel
              </Button>
              <Button
                onClick={() => assignMutation.mutate()}
                disabled={assignMutation.isPending || !selectedPolicyId}
              >
                {assignMutation.isPending ? "Assigning..." : "Assign"}
              </Button>
            </div>
            {assignMutation.isError && (
              <p className="text-sm text-destructive">
                {(assignMutation.error as Error).message}
              </p>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Place Legal Hold Dialog */}
      <Dialog open={holdDialogOpen} onOpenChange={setHoldDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Place Legal Hold</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="hold_reason">Reason</Label>
              <Textarea
                id="hold_reason"
                placeholder="Reason for placing legal hold..."
                value={holdReason}
                onChange={(e) => setHoldReason(e.target.value)}
                rows={3}
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button
                variant="outline"
                onClick={() => setHoldDialogOpen(false)}
              >
                Cancel
              </Button>
              <Button
                onClick={() => holdMutation.mutate()}
                disabled={holdMutation.isPending || !holdReason.trim()}
              >
                {holdMutation.isPending ? "Placing..." : "Place Hold"}
              </Button>
            </div>
            {holdMutation.isError && (
              <p className="text-sm text-destructive">
                {(holdMutation.error as Error).message}
              </p>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
