import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FolderPickerDialog } from "./FolderPickerDialog";
import { moveFolder, folderKeys } from "../../api/folders";

interface MoveFolderDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  folder: { id: string; name: string } | null;
}

export function MoveFolderDialog({
  open,
  onOpenChange,
  folder,
}: MoveFolderDialogProps) {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (destId: string) => moveFolder(folder!.id, destId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: folderKeys.tree() });
      onOpenChange(false);
    },
  });

  function handleSelect(destId: string) {
    if (!folder) return;
    mutation.mutate(destId);
  }

  return (
    <FolderPickerDialog
      open={open}
      onOpenChange={onOpenChange}
      title={`Move "${folder?.name ?? "folder"}" to…`}
      onSelect={handleSelect}
      excludeId={folder?.id}
    />
  );
}
