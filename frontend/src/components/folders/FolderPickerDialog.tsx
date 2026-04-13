import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "../ui/dialog";
import { Button } from "../ui/button";
import { Skeleton } from "../ui/skeleton";
import { FolderTree } from "./FolderTree";
import { fetchFolderTree, folderKeys } from "../../api/folders";

interface FolderPickerDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  onSelect: (folderId: string) => void;
  excludeId?: string;
}

export function FolderPickerDialog({
  open,
  onOpenChange,
  title,
  onSelect,
  excludeId,
}: FolderPickerDialogProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data: tree = [], isLoading } = useQuery({
    queryKey: folderKeys.tree(),
    queryFn: fetchFolderTree,
    enabled: open,
  });

  // Filter out the excluded node and its children from the displayed tree
  function filterTree(
    nodes: typeof tree,
  ): typeof tree {
    if (!excludeId) return nodes;
    return nodes
      .filter((n) => n.id !== excludeId)
      .map((n) => ({ ...n, children: filterTree(n.children) }));
  }

  const filteredTree = filterTree(tree);

  function handleConfirm() {
    if (selectedId) {
      onSelect(selectedId);
      setSelectedId(null);
      onOpenChange(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        <div className="border rounded min-h-[200px] max-h-[400px] overflow-y-auto">
          {isLoading ? (
            <div className="p-4 space-y-2">
              <Skeleton className="h-5 w-full" />
              <Skeleton className="h-5 w-[80%]" />
              <Skeleton className="h-5 w-[70%]" />
            </div>
          ) : (
            <FolderTree
              tree={filteredTree}
              selectedId={selectedId}
              onSelect={setSelectedId}
            />
          )}
        </div>
        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => {
              setSelectedId(null);
              onOpenChange(false);
            }}
          >
            Cancel
          </Button>
          <Button onClick={handleConfirm} disabled={!selectedId}>
            Select
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
