import { useState, useEffect } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "../ui/dialog";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { renameFolder, folderKeys } from "../../api/folders";

interface RenameFolderDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  folder: { id: string; name: string } | null;
}

export function RenameFolderDialog({
  open,
  onOpenChange,
  folder,
}: RenameFolderDialogProps) {
  const queryClient = useQueryClient();
  const [name, setName] = useState(folder?.name ?? "");

  useEffect(() => {
    if (folder) setName(folder.name);
  }, [folder]);

  const mutation = useMutation({
    mutationFn: () => renameFolder(folder!.id, name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: folderKeys.tree() });
      onOpenChange(false);
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !folder) return;
    mutation.mutate();
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Rename Folder</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1">
            <Label htmlFor="rename-name">New Name</Label>
            <Input
              id="rename-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>
          {mutation.error && (
            <p className="text-sm text-destructive">
              {(mutation.error as Error).message}
            </p>
          )}
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending || !name.trim()}>
              {mutation.isPending ? "Renaming..." : "Rename"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
