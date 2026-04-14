import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { BookmarkPlus } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "../ui/dialog";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Checkbox } from "../ui/checkbox";
import { createSavedSearch, savedSearchKeys } from "../../api/savedSearches";
import type { SearchFilterValues } from "./SearchFilters";

interface SaveSearchDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  query: string;
  filters: SearchFilterValues;
  onSaved: () => void;
}

export function SaveSearchDialog({
  open,
  onOpenChange,
  query,
  filters,
  onSaved,
}: SaveSearchDialogProps) {
  const [name, setName] = useState("");
  const [isSmartFolder, setIsSmartFolder] = useState(false);
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: () =>
      createSavedSearch({
        name,
        query,
        filters,
        is_smart_folder: isSmartFolder,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: savedSearchKeys.all });
      setName("");
      setIsSmartFolder(false);
      onSaved();
      onOpenChange(false);
    },
  });

  function handleSave() {
    if (!name.trim()) return;
    mutation.mutate();
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <BookmarkPlus className="h-5 w-5" />
            Save Search
          </DialogTitle>
          <DialogDescription>
            Save the current search query and filters for quick access later.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <label htmlFor="search-name" className="text-sm font-medium">
              Name
            </label>
            <Input
              id="search-name"
              placeholder="e.g. Draft contracts in HR folder"
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSave();
              }}
            />
          </div>

          <div className="flex items-center gap-2">
            <Checkbox
              id="smart-folder"
              checked={isSmartFolder}
              onCheckedChange={(checked) =>
                setIsSmartFolder(checked === true)
              }
            />
            <label
              htmlFor="smart-folder"
              className="text-sm cursor-pointer select-none"
            >
              Show as Smart Folder in Browse tree
            </label>
          </div>

          <div className="rounded border p-3 bg-muted/50 text-xs text-muted-foreground space-y-1">
            <p>
              <span className="font-medium">Query:</span>{" "}
              {query || "(empty)"}
            </p>
            {filters.folder_id && (
              <p>
                <span className="font-medium">Folder filter:</span> set
              </p>
            )}
            {filters.document_type_id && (
              <p>
                <span className="font-medium">Type filter:</span> set
              </p>
            )}
            {filters.lifecycle_state && (
              <p>
                <span className="font-medium">Lifecycle filter:</span>{" "}
                {filters.lifecycle_state}
              </p>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            disabled={!name.trim() || mutation.isPending}
          >
            {mutation.isPending ? "Saving..." : "Save"}
          </Button>
        </DialogFooter>

        {mutation.isError && (
          <p className="text-sm text-destructive">
            Failed to save: {(mutation.error as Error).message}
          </p>
        )}
      </DialogContent>
    </Dialog>
  );
}
