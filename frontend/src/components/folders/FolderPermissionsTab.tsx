import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Shield, User, Users, X } from "lucide-react";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import { Skeleton } from "../ui/skeleton";
import { fetchFolderAcls, removeFolderAcl, folderKeys } from "../../api/folders";
import { AddPermissionDialog } from "./AddPermissionDialog";

interface FolderPermissionsTabProps {
  folderId: string;
}

export function FolderPermissionsTab({ folderId }: FolderPermissionsTabProps) {
  const queryClient = useQueryClient();
  const [addOpen, setAddOpen] = useState(false);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const { data: acls, isLoading } = useQuery({
    queryKey: folderKeys.acl(folderId),
    queryFn: () => fetchFolderAcls(folderId),
  });

  const removeMutation = useMutation({
    mutationFn: (aclId: string) => removeFolderAcl(folderId, aclId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: folderKeys.acl(folderId) });
      setConfirmDeleteId(null);
    },
  });

  if (isLoading) {
    return (
      <div className="space-y-2 pt-4">
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-full" />
      </div>
    );
  }

  return (
    <div className="pt-4">
      {/* Header row */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Shield className="h-4 w-4 text-muted-foreground" />
          <h4 className="text-sm font-medium">Permissions</h4>
        </div>
        <Button size="sm" onClick={() => setAddOpen(true)}>
          Add Permission
        </Button>
      </div>

      {/* ACL list or empty state */}
      {!acls || acls.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <Shield className="h-8 w-8 text-muted-foreground mb-3" />
          <h4 className="text-sm font-medium">No permissions set</h4>
          <p className="text-sm text-muted-foreground mt-1">
            This folder is open to all users. Add a permission entry to restrict access.
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {acls.map((entry) => (
            <div
              key={entry.id}
              className="flex items-center gap-2 py-2 px-2 rounded-md hover:bg-muted"
            >
              {entry.principal_type === "group" ? (
                <Users className="h-4 w-4 text-muted-foreground shrink-0" />
              ) : (
                <User className="h-4 w-4 text-muted-foreground shrink-0" />
              )}
              <span className="text-sm truncate flex-1" title={entry.principal_id}>
                {entry.principal_id.slice(0, 8)}...
              </span>
              <Badge variant="outline" className="text-xs">
                {entry.principal_type === "group" ? "Group" : "User"}
              </Badge>
              <Badge variant="secondary" className="text-xs">
                {entry.permission_level.charAt(0).toUpperCase() + entry.permission_level.slice(1).toLowerCase()}
              </Badge>
              {/* Inline confirm pattern instead of window.confirm() */}
              {confirmDeleteId === entry.id ? (
                <Button
                  variant="destructive"
                  size="sm"
                  className="h-7 text-xs shrink-0"
                  onClick={() => removeMutation.mutate(entry.id)}
                  disabled={removeMutation.isPending}
                  onBlur={() => setConfirmDeleteId(null)}
                >
                  Confirm?
                </Button>
              ) : (
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 text-muted-foreground hover:text-destructive shrink-0"
                  onClick={() => setConfirmDeleteId(entry.id)}
                  disabled={removeMutation.isPending}
                >
                  <X className="h-3.5 w-3.5" />
                </Button>
              )}
            </div>
          ))}
        </div>
      )}

      <AddPermissionDialog
        open={addOpen}
        onOpenChange={setAddOpen}
        folderId={folderId}
      />
    </div>
  );
}
