import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Package } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "../ui/dialog";
import { Button } from "../ui/button";
import { Checkbox } from "../ui/checkbox";
import { Label } from "../ui/label";
import { exportDocuments } from "../../api/importExport";

interface ExportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  selectedDocumentIds?: string[];
  selectedFolderIds?: string[];
}

export function ExportDialog({
  open,
  onOpenChange,
  selectedDocumentIds = [],
  selectedFolderIds = [],
}: ExportDialogProps) {
  const [includeAcls, setIncludeAcls] = useState(true);
  const [includeRelationships, setIncludeRelationships] = useState(true);

  const mutation = useMutation({
    mutationFn: () =>
      exportDocuments({
        document_ids: selectedDocumentIds.length > 0 ? selectedDocumentIds : undefined,
        folder_ids: selectedFolderIds.length > 0 ? selectedFolderIds : undefined,
        include_acls: includeAcls,
        include_relationships: includeRelationships,
      }),
    onSuccess: () => {
      onOpenChange(false);
    },
  });

  const totalItems =
    (selectedDocumentIds?.length ?? 0) + (selectedFolderIds?.length ?? 0);

  const summaryText =
    selectedDocumentIds.length > 0 && selectedFolderIds.length > 0
      ? `Exporting ${selectedDocumentIds.length} document${selectedDocumentIds.length !== 1 ? "s" : ""} and ${selectedFolderIds.length} folder${selectedFolderIds.length !== 1 ? "s" : ""}`
      : selectedFolderIds.length > 0
        ? `Exporting ${selectedFolderIds.length} folder${selectedFolderIds.length !== 1 ? "s" : ""}`
        : `Exporting ${selectedDocumentIds.length} document${selectedDocumentIds.length !== 1 ? "s" : ""}`;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Package className="h-5 w-5" />
            Export Package
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <p className="text-sm text-muted-foreground">{summaryText}</p>

          <div className="space-y-3">
            <div className="flex items-center space-x-2">
              <Checkbox
                id="include-acls"
                checked={includeAcls}
                onCheckedChange={(checked) => setIncludeAcls(!!checked)}
              />
              <Label htmlFor="include-acls">Include ACLs</Label>
            </div>
            <div className="flex items-center space-x-2">
              <Checkbox
                id="include-relationships"
                checked={includeRelationships}
                onCheckedChange={(checked) =>
                  setIncludeRelationships(!!checked)
                }
              />
              <Label htmlFor="include-relationships">
                Include relationships
              </Label>
            </div>
          </div>

          {mutation.isError && (
            <p className="text-sm text-destructive">
              {(mutation.error as Error).message}
            </p>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={mutation.isPending}
          >
            Cancel
          </Button>
          <Button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending || totalItems === 0}
          >
            {mutation.isPending ? "Exporting..." : "Export"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
