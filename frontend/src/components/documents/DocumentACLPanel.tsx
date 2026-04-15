import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Shield, Plus, X, Users, User as UserIcon } from "lucide-react";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import { Skeleton } from "../ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "../ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import {
  fetchDocumentACLs,
  addDocumentACL,
  removeDocumentACL,
  type ACLEntryResponse,
} from "../../api/documents";
import { listUsers, type UserSummary } from "../../api/users";

interface DocumentACLPanelProps {
  documentId: string;
}

const PERMISSION_COLORS: Record<string, string> = {
  READ: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  WRITE: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  DELETE: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200",
  ADMIN: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
};

export function DocumentACLPanel({ documentId }: DocumentACLPanelProps) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const queryClient = useQueryClient();

  const { data: aclEntries = [], isLoading } = useQuery({
    queryKey: ["document-acl", documentId],
    queryFn: () => fetchDocumentACLs(documentId),
    enabled: !!documentId,
  });

  const removeMutation = useMutation({
    mutationFn: (aclId: string) => removeDocumentACL(documentId, aclId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["document-acl", documentId],
      });
    },
  });

  if (isLoading) {
    return (
      <div className="px-6 py-4">
        <h4 className="text-sm font-medium flex items-center gap-1 mb-3">
          <Shield className="h-4 w-4" /> Permissions
        </h4>
        <div className="space-y-2">
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
        </div>
      </div>
    );
  }

  return (
    <div className="px-6 py-4">
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-medium flex items-center gap-1">
          <Shield className="h-4 w-4" /> Permissions
          {aclEntries.length > 0 && (
            <span className="text-xs text-muted-foreground ml-1">
              ({aclEntries.length})
            </span>
          )}
        </h4>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button variant="ghost" size="sm">
              <Plus className="h-3 w-3 mr-1" /> Add
            </Button>
          </DialogTrigger>
          <AddACLDialog
            documentId={documentId}
            onSuccess={() => {
              setDialogOpen(false);
              queryClient.invalidateQueries({
                queryKey: ["document-acl", documentId],
              });
            }}
          />
        </Dialog>
      </div>

      {aclEntries.length === 0 ? (
        <div className="flex flex-col items-center py-4 text-center">
          <Shield className="h-8 w-8 text-muted-foreground/40 mb-2" />
          <p className="text-xs text-muted-foreground">No ACL entries</p>
        </div>
      ) : (
        <div className="space-y-1.5">
          {aclEntries.map((entry) => (
            <ACLEntryRow
              key={entry.id}
              entry={entry}
              onDelete={(id) => removeMutation.mutate(id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// --- Internal row component ---

function ACLEntryRow({
  entry,
  onDelete,
}: {
  entry: ACLEntryResponse;
  onDelete: (aclId: string) => void;
}) {
  const Icon = entry.principal_type === "group" ? Users : UserIcon;

  return (
    <div className="flex items-center gap-2 text-sm group">
      <Icon className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
      <span className="truncate text-sm" title={entry.principal_id}>
        {entry.principal_id.slice(0, 8)}...
      </span>
      <Badge
        className={`text-xs shrink-0 ${PERMISSION_COLORS[entry.permission_level] ?? ""}`}
        variant="outline"
      >
        {entry.permission_level}
      </Badge>
      <Button
        variant="ghost"
        size="sm"
        className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100 shrink-0 ml-auto"
        onClick={() => onDelete(entry.id)}
        title="Remove ACL entry"
      >
        <X className="h-3 w-3 text-destructive" />
      </Button>
    </div>
  );
}

// --- Add ACL Dialog ---

function AddACLDialog({
  documentId,
  onSuccess,
}: {
  documentId: string;
  onSuccess: () => void;
}) {
  const [principalType, setPrincipalType] = useState<"user" | "group">("user");
  const [principalId, setPrincipalId] = useState("");
  const [permissionLevel, setPermissionLevel] = useState<
    "READ" | "WRITE" | "DELETE" | "ADMIN"
  >("READ");

  const { data: users = [] } = useQuery({
    queryKey: ["users-list"],
    queryFn: listUsers,
  });

  const addMutation = useMutation({
    mutationFn: () =>
      addDocumentACL(documentId, {
        document_id: documentId,
        principal_id: principalId,
        principal_type: principalType,
        permission_level: permissionLevel,
      }),
    onSuccess: () => {
      setPrincipalId("");
      setPermissionLevel("READ");
      onSuccess();
    },
  });

  return (
    <DialogContent>
      <DialogHeader>
        <DialogTitle>Add Permission</DialogTitle>
      </DialogHeader>
      <div className="space-y-4 py-2">
        {/* Principal type */}
        <div>
          <label className="text-sm font-medium mb-1 block">
            Principal Type
          </label>
          <Select
            value={principalType}
            onValueChange={(v) => {
              setPrincipalType(v as "user" | "group");
              setPrincipalId("");
            }}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="user">User</SelectItem>
              <SelectItem value="group">Group</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Principal selection */}
        <div>
          <label className="text-sm font-medium mb-1 block">
            {principalType === "user" ? "User" : "Group ID"}
          </label>
          {principalType === "user" ? (
            <Select value={principalId} onValueChange={setPrincipalId}>
              <SelectTrigger>
                <SelectValue placeholder="Select a user" />
              </SelectTrigger>
              <SelectContent>
                {users.map((u: UserSummary) => (
                  <SelectItem key={u.id} value={u.id}>
                    {u.username}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : (
            <input
              type="text"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              placeholder="Enter group UUID"
              value={principalId}
              onChange={(e) => setPrincipalId(e.target.value)}
            />
          )}
        </div>

        {/* Permission level */}
        <div>
          <label className="text-sm font-medium mb-1 block">
            Permission Level
          </label>
          <Select
            value={permissionLevel}
            onValueChange={(v) =>
              setPermissionLevel(v as "READ" | "WRITE" | "DELETE" | "ADMIN")
            }
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="READ">Read</SelectItem>
              <SelectItem value="WRITE">Write</SelectItem>
              <SelectItem value="DELETE">Delete</SelectItem>
              <SelectItem value="ADMIN">Admin</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <Button
          className="w-full"
          onClick={() => addMutation.mutate()}
          disabled={!principalId || addMutation.isPending}
        >
          {addMutation.isPending ? "Adding..." : "Add Permission"}
        </Button>

        {addMutation.isError && (
          <p className="text-sm text-destructive">
            {(addMutation.error as Error).message}
          </p>
        )}
      </div>
    </DialogContent>
  );
}
