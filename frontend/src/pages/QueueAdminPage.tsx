import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ListChecks, Pencil, Trash2, X, UserPlus, ChevronDown, ChevronRight } from "lucide-react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Badge } from "../components/ui/badge";
import { Switch } from "../components/ui/switch";
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
  fetchQueues,
  fetchQueueDetail,
  createQueue,
  updateQueue,
  deleteQueue,
  addQueueMember,
  removeQueueMember,
} from "../api/queues";
import { listUsers } from "../api/users";
import type {
  WorkQueueResponse,
  WorkQueueDetailResponse,
  WorkQueueCreate,
  WorkQueueUpdate,
} from "../api/queues";

export function QueueAdminPage() {
  const queryClient = useQueryClient();
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [editingQueue, setEditingQueue] = useState<WorkQueueResponse | null>(null);
  const [expandedQueueId, setExpandedQueueId] = useState<string | null>(null);

  const { data: queuesData, isLoading } = useQuery({
    queryKey: ["queues"],
    queryFn: () => fetchQueues(),
  });
  const queues = queuesData?.data ?? [];

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteQueue(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["queues"] });
    },
  });

  function handleDelete(id: string, name: string) {
    if (window.confirm(`Delete work queue "${name}"?`)) {
      deleteMutation.mutate(id);
    }
  }

  function handleSuccess() {
    queryClient.invalidateQueries({ queryKey: ["queues"] });
  }

  function toggleExpand(queueId: string) {
    setExpandedQueueId((prev) => (prev === queueId ? null : queueId));
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <ListChecks className="h-5 w-5 text-muted-foreground" />
          <h1 className="text-lg font-semibold">Work Queues</h1>
        </div>
        <Button onClick={() => setShowCreateDialog(true)}>Create Queue</Button>
      </div>

      {/* Queue Table */}
      {isLoading ? (
        <p className="text-muted-foreground text-sm">Loading queues...</p>
      ) : queues.length === 0 ? (
        <p className="text-muted-foreground text-sm">
          No work queues defined yet.
        </p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-8"></TableHead>
              <TableHead>Name</TableHead>
              <TableHead>Description</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Members</TableHead>
              <TableHead>Created</TableHead>
              <TableHead className="w-24">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {queues.map((queue) => (
              <>
                <TableRow key={queue.id}>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6"
                      onClick={() => toggleExpand(queue.id)}
                    >
                      {expandedQueueId === queue.id ? (
                        <ChevronDown className="h-4 w-4" />
                      ) : (
                        <ChevronRight className="h-4 w-4" />
                      )}
                    </Button>
                  </TableCell>
                  <TableCell className="font-medium">{queue.name}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {queue.description ?? "-"}
                  </TableCell>
                  <TableCell>
                    <Badge variant={queue.is_active ? "default" : "secondary"}>
                      {queue.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </TableCell>
                  <TableCell>{queue.member_count}</TableCell>
                  <TableCell>
                    {new Date(queue.created_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setEditingQueue(queue)}
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleDelete(queue.id, queue.name)}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
                {expandedQueueId === queue.id && (
                  <TableRow key={`${queue.id}-detail`}>
                    <TableCell colSpan={7} className="bg-muted/50 p-4">
                      <QueueMemberPanel queueId={queue.id} />
                    </TableCell>
                  </TableRow>
                )}
              </>
            ))}
          </TableBody>
        </Table>
      )}

      {/* Create Dialog */}
      <QueueDialog
        open={showCreateDialog}
        onOpenChange={setShowCreateDialog}
        onSuccess={handleSuccess}
        mode="create"
      />

      {/* Edit Dialog */}
      {editingQueue && (
        <QueueDialog
          open={editingQueue !== null}
          onOpenChange={(open) => {
            if (!open) setEditingQueue(null);
          }}
          onSuccess={() => {
            handleSuccess();
            setEditingQueue(null);
          }}
          mode="edit"
          queue={editingQueue}
        />
      )}
    </div>
  );
}

// --- Queue Create/Edit Dialog ---

interface QueueDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
  mode: "create" | "edit";
  queue?: WorkQueueResponse;
}

function QueueDialog({
  open,
  onOpenChange,
  onSuccess,
  mode,
  queue,
}: QueueDialogProps) {
  const [name, setName] = useState(queue?.name ?? "");
  const [description, setDescription] = useState(queue?.description ?? "");
  const [isActive, setIsActive] = useState(queue?.is_active ?? true);
  const [error, setError] = useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: (data: WorkQueueCreate) => createQueue(data),
    onSuccess: () => {
      onSuccess();
      onOpenChange(false);
      resetForm();
    },
    onError: (err: Error) => setError(err.message),
  });

  const updateMutation = useMutation({
    mutationFn: (data: WorkQueueUpdate) => updateQueue(queue!.id, data),
    onSuccess: () => {
      onSuccess();
      onOpenChange(false);
    },
    onError: (err: Error) => setError(err.message),
  });

  function resetForm() {
    setName("");
    setDescription("");
    setIsActive(true);
    setError(null);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!name.trim()) {
      setError("Name is required.");
      return;
    }

    const payload = {
      name: name.trim(),
      description: description.trim() || undefined,
      is_active: isActive,
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
            {mode === "create" ? "Create Work Queue" : "Edit Work Queue"}
          </DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="queue-name">Name</Label>
            <Input
              id="queue-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Invoice Processing"
            />
          </div>
          <div>
            <Label htmlFor="queue-desc">Description</Label>
            <Textarea
              id="queue-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional description"
              rows={2}
            />
          </div>
          <div className="flex items-center gap-3">
            <Switch
              id="queue-active"
              checked={isActive}
              onCheckedChange={setIsActive}
            />
            <Label htmlFor="queue-active">Active</Label>
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
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

// --- Queue Member Panel (expanded row) ---

function QueueMemberPanel({ queueId }: { queueId: string }) {
  const queryClient = useQueryClient();
  const [showAddMember, setShowAddMember] = useState(false);
  const [selectedUserId, setSelectedUserId] = useState<string>("");

  const { data: detail, isLoading } = useQuery({
    queryKey: ["queue-detail", queueId],
    queryFn: () => fetchQueueDetail(queueId),
  });

  const { data: allUsers = [] } = useQuery({
    queryKey: ["users"],
    queryFn: listUsers,
    enabled: showAddMember,
  });

  const addMutation = useMutation({
    mutationFn: (userId: string) => addQueueMember(queueId, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["queues"] });
      queryClient.invalidateQueries({ queryKey: ["queue-detail", queueId] });
      setShowAddMember(false);
      setSelectedUserId("");
    },
  });

  const removeMutation = useMutation({
    mutationFn: (userId: string) => removeQueueMember(queueId, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["queues"] });
      queryClient.invalidateQueries({ queryKey: ["queue-detail", queueId] });
    },
  });

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Loading members...</p>;
  }

  const members = detail?.members ?? [];
  const memberIds = new Set(members.map((m) => m.id));
  const availableUsers = allUsers.filter((u) => !memberIds.has(u.id));

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium">
          Members ({members.length})
        </h3>
        <Button
          size="sm"
          variant="outline"
          onClick={() => setShowAddMember(true)}
        >
          <UserPlus className="h-3 w-3 mr-1" />
          Add Member
        </Button>
      </div>

      {members.length === 0 ? (
        <p className="text-sm text-muted-foreground">No members yet.</p>
      ) : (
        <div className="space-y-1">
          {members.map((member) => (
            <div
              key={member.id}
              className="flex items-center justify-between bg-background rounded px-3 py-1.5 text-sm"
            >
              <span>
                {member.username}
                {member.email && (
                  <span className="text-muted-foreground ml-2">
                    ({member.email})
                  </span>
                )}
              </span>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6"
                onClick={() => removeMutation.mutate(member.id)}
                disabled={removeMutation.isPending}
              >
                <X className="h-3 w-3" />
              </Button>
            </div>
          ))}
        </div>
      )}

      {/* Add Member Dialog */}
      <Dialog open={showAddMember} onOpenChange={setShowAddMember}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Member</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Select User</Label>
              <Select value={selectedUserId} onValueChange={setSelectedUserId}>
                <SelectTrigger>
                  <SelectValue placeholder="Choose a user..." />
                </SelectTrigger>
                <SelectContent>
                  {availableUsers.map((user) => (
                    <SelectItem key={user.id} value={user.id}>
                      {user.username}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setShowAddMember(false)}
              >
                Cancel
              </Button>
              <Button
                disabled={!selectedUserId || addMutation.isPending}
                onClick={() => addMutation.mutate(selectedUserId)}
              >
                {addMutation.isPending ? "Adding..." : "Add"}
              </Button>
            </DialogFooter>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
