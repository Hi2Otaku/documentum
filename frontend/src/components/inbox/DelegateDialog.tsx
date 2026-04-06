import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
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
import { Label } from "../ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import { updateAvailability } from "../../api/users";
import { fetchUsersForFilter } from "../../api/query";
import { useAuthStore } from "../../stores/authStore";

interface DelegateDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function DelegateDialog({ open, onOpenChange }: DelegateDialogProps) {
  const [selectedUserId, setSelectedUserId] = useState<string>("");
  const userId = useAuthStore((s) => s.userId);
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();

  const { data: users } = useQuery({
    queryKey: ["users"],
    queryFn: fetchUsersForFilter,
    enabled: open,
  });

  const filteredUsers = (users ?? []).filter((u) => u.id !== userId);

  const delegateMutation = useMutation({
    mutationFn: () => updateAvailability(token!, false, selectedUserId),
    onSuccess: () => {
      useAuthStore.setState({ isAvailable: false });
      queryClient.invalidateQueries({ queryKey: ["inbox"] });
      toast.success("Delegation set. You are now unavailable.");
      setSelectedUserId("");
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
          <DialogTitle>Delegate Tasks</DialogTitle>
          <DialogDescription>
            Setting a delegate will route all your future tasks to the selected
            user. You will be marked as unavailable.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          <Label htmlFor="delegate-user">Delegate to</Label>
          <Select value={selectedUserId} onValueChange={setSelectedUserId}>
            <SelectTrigger id="delegate-user">
              <SelectValue placeholder="Select a user..." />
            </SelectTrigger>
            <SelectContent>
              {filteredUsers.map((user) => (
                <SelectItem key={user.id} value={user.id}>
                  {user.username}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            variant="default"
            disabled={!selectedUserId || delegateMutation.isPending}
            onClick={() => delegateMutation.mutate()}
          >
            {delegateMutation.isPending
              ? "Delegating..."
              : "Confirm Delegation"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
