import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { User, Users } from "lucide-react";
import { Button } from "../ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "../ui/dialog";
import {
  Select,
  SelectTrigger,
  SelectContent,
  SelectItem,
  SelectValue,
} from "../ui/select";
import { addFolderAcl, folderKeys } from "../../api/folders";

interface AddPermissionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  folderId: string;
}

export function AddPermissionDialog({
  open,
  onOpenChange,
  folderId,
}: AddPermissionDialogProps) {
  const queryClient = useQueryClient();
  const [principalType, setPrincipalType] = useState<"user" | "group">("user");
  const [principalId, setPrincipalId] = useState<string>("");
  const [permissionLevel, setPermissionLevel] = useState<string>("READ");
  const [error, setError] = useState<string>("");

  // Fetch users for the dropdown
  const { data: users = [] } = useQuery({
    queryKey: ["users"],
    queryFn: async () => {
      const token = localStorage.getItem("token");
      const res = await fetch("/api/v1/users", {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) return [];
      const json = await res.json();
      return json.data || [];
    },
    enabled: open && principalType === "user",
  });

  const mutation = useMutation({
    mutationFn: () => addFolderAcl(folderId, principalId, principalType, permissionLevel),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: folderKeys.acl(folderId) });
      onOpenChange(false);
      setPrincipalId("");
      setPermissionLevel("READ");
      setError("");
    },
    onError: () => {
      setError("Failed to add permission. The user may already have an entry on this folder.");
    },
  });

  function handleSubmit() {
    setError("");
    mutation.mutate();
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Add Permission</DialogTitle>
          <DialogDescription>
            Grant a user or group access to this folder and its documents.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Principal type toggle */}
          <div className="flex gap-1">
            <Button
              variant={principalType === "user" ? "default" : "outline"}
              size="sm"
              className="flex-1 h-9"
              onClick={() => {
                setPrincipalType("user");
                setPrincipalId("");
              }}
            >
              <User className="h-4 w-4 mr-1" />
              User
            </Button>
            <Button
              variant={principalType === "group" ? "default" : "outline"}
              size="sm"
              className="flex-1 h-9"
              onClick={() => {
                setPrincipalType("group");
                setPrincipalId("");
              }}
            >
              <Users className="h-4 w-4 mr-1" />
              Group
            </Button>
          </div>

          {/* Principal selector */}
          <Select value={principalId} onValueChange={setPrincipalId}>
            <SelectTrigger>
              <SelectValue
                placeholder={
                  principalType === "user" ? "Select a user..." : "Select a group..."
                }
              />
            </SelectTrigger>
            <SelectContent>
              {principalType === "user" ? (
                users.map((u: { id: string; username: string }) => (
                  <SelectItem key={u.id} value={u.id}>
                    {u.username}
                  </SelectItem>
                ))
              ) : (
                <SelectItem value="none" disabled>
                  No groups available
                </SelectItem>
              )}
            </SelectContent>
          </Select>

          {/* Permission level */}
          <Select value={permissionLevel} onValueChange={setPermissionLevel}>
            <SelectTrigger>
              <SelectValue placeholder="Select permission..." />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="READ">Read</SelectItem>
              <SelectItem value="WRITE">Write</SelectItem>
              <SelectItem value="DELETE">Delete</SelectItem>
              <SelectItem value="ADMIN">Admin</SelectItem>
            </SelectContent>
          </Select>

          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={!principalId || !permissionLevel || mutation.isPending}
          >
            Add Permission
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
