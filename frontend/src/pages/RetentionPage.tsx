import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Shield, Pencil, Trash2 } from "lucide-react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "../components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import {
  fetchRetentionPolicies,
  createRetentionPolicy,
  updateRetentionPolicy,
  deleteRetentionPolicy,
} from "../api/retention";
import type {
  RetentionPolicyResponse,
  RetentionPolicyCreate,
  RetentionPolicyUpdate,
} from "../api/retention";

export function RetentionPage() {
  const queryClient = useQueryClient();
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [editingPolicy, setEditingPolicy] =
    useState<RetentionPolicyResponse | null>(null);

  const { data: policies = [], isLoading } = useQuery({
    queryKey: ["retention-policies"],
    queryFn: () => fetchRetentionPolicies(),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteRetentionPolicy(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["retention-policies"] });
    },
  });

  function handleDelete(id: string, name: string) {
    if (window.confirm(`Delete retention policy "${name}"?`)) {
      deleteMutation.mutate(id);
    }
  }

  function handleSuccess() {
    queryClient.invalidateQueries({ queryKey: ["retention-policies"] });
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Shield className="h-5 w-5 text-muted-foreground" />
          <h1 className="text-lg font-semibold">Retention Policies</h1>
        </div>
        <Button onClick={() => setShowCreateDialog(true)}>Create Policy</Button>
      </div>

      {/* Policies Table */}
      {isLoading ? (
        <p className="text-muted-foreground text-sm">Loading policies...</p>
      ) : policies.length === 0 ? (
        <p className="text-muted-foreground text-sm">
          No retention policies defined yet.
        </p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Description</TableHead>
              <TableHead>Retention (days)</TableHead>
              <TableHead>Disposition</TableHead>
              <TableHead>Created</TableHead>
              <TableHead className="w-24">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {policies.map((policy) => (
              <TableRow key={policy.id}>
                <TableCell className="font-medium">{policy.name}</TableCell>
                <TableCell className="text-muted-foreground">
                  {policy.description ?? "-"}
                </TableCell>
                <TableCell>{policy.retention_period_days}</TableCell>
                <TableCell className="capitalize">
                  {policy.disposition_action}
                </TableCell>
                <TableCell>
                  {new Date(policy.created_at).toLocaleDateString()}
                </TableCell>
                <TableCell>
                  <div className="flex gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => setEditingPolicy(policy)}
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleDelete(policy.id, policy.name)}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      {/* Legal Holds info */}
      <div className="mt-8">
        <h2 className="text-md font-semibold mb-2">Legal Holds</h2>
        <p className="text-sm text-muted-foreground">
          Legal holds are managed per-document from the document detail panel.
          When a legal hold is active, the document cannot be deleted or have its
          retention reduced until the hold is released.
        </p>
      </div>

      {/* Create Dialog */}
      <PolicyDialog
        open={showCreateDialog}
        onOpenChange={setShowCreateDialog}
        onSuccess={handleSuccess}
        mode="create"
      />

      {/* Edit Dialog */}
      {editingPolicy && (
        <PolicyDialog
          open={editingPolicy !== null}
          onOpenChange={(open) => {
            if (!open) setEditingPolicy(null);
          }}
          onSuccess={() => {
            handleSuccess();
            setEditingPolicy(null);
          }}
          mode="edit"
          policy={editingPolicy}
        />
      )}
    </div>
  );
}

// --- Shared Create/Edit Dialog ---

interface PolicyDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
  mode: "create" | "edit";
  policy?: RetentionPolicyResponse;
}

function PolicyDialog({
  open,
  onOpenChange,
  onSuccess,
  mode,
  policy,
}: PolicyDialogProps) {
  const [name, setName] = useState(policy?.name ?? "");
  const [description, setDescription] = useState(policy?.description ?? "");
  const [retentionDays, setRetentionDays] = useState(
    String(policy?.retention_period_days ?? 365),
  );
  const [disposition, setDisposition] = useState<"archive" | "delete">(
    (policy?.disposition_action as "archive" | "delete") ?? "archive",
  );
  const [error, setError] = useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: (data: RetentionPolicyCreate) => createRetentionPolicy(data),
    onSuccess: () => {
      onSuccess();
      onOpenChange(false);
      resetForm();
    },
    onError: (err: Error) => setError(err.message),
  });

  const updateMutation = useMutation({
    mutationFn: (data: RetentionPolicyUpdate) =>
      updateRetentionPolicy(policy!.id, data),
    onSuccess: () => {
      onSuccess();
      onOpenChange(false);
    },
    onError: (err: Error) => setError(err.message),
  });

  function resetForm() {
    setName("");
    setDescription("");
    setRetentionDays("365");
    setDisposition("archive");
    setError(null);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const days = parseInt(retentionDays, 10);
    if (!name.trim()) {
      setError("Name is required.");
      return;
    }
    if (isNaN(days) || days <= 0) {
      setError("Retention period must be a positive number.");
      return;
    }

    const payload = {
      name: name.trim(),
      description: description.trim() || undefined,
      retention_period_days: days,
      disposition_action: disposition,
    };

    if (mode === "create") {
      createMutation.mutate(payload);
    } else {
      updateMutation.mutate(payload);
    }
  }

  const isPending = createMutation.isPending || updateMutation.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {mode === "create" ? "Create Retention Policy" : "Edit Retention Policy"}
          </DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="policy-name">Name</Label>
            <Input
              id="policy-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. 7-Year Financial"
            />
          </div>
          <div>
            <Label htmlFor="policy-desc">Description</Label>
            <Textarea
              id="policy-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional description"
              rows={2}
            />
          </div>
          <div>
            <Label htmlFor="policy-days">Retention Period (days)</Label>
            <Input
              id="policy-days"
              type="number"
              min={1}
              value={retentionDays}
              onChange={(e) => setRetentionDays(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="policy-disposition">Disposition Action</Label>
            <Select value={disposition} onValueChange={(v) => setDisposition(v as "archive" | "delete")}>
              <SelectTrigger id="policy-disposition">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="archive">Archive</SelectItem>
                <SelectItem value="delete">Delete</SelectItem>
              </SelectContent>
            </Select>
          </div>
          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? "Saving..." : mode === "create" ? "Create" : "Save"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
