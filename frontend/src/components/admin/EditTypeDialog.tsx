import { useState, useEffect } from "react";
import { toast } from "sonner";
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
import { Textarea } from "../ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import { SchemaEditor } from "./SchemaEditor";
import { updateDocumentType, deleteDocumentType } from "../../api/documentTypes";
import type { DocumentTypeResponse } from "../../api/documentTypes";

interface EditTypeDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
  type: DocumentTypeResponse;
  existingTypes: DocumentTypeResponse[];
}

export function EditTypeDialog({
  open,
  onOpenChange,
  onSuccess,
  type,
  existingTypes,
}: EditTypeDialogProps) {
  const [name, setName] = useState(type.name);
  const [description, setDescription] = useState(type.description ?? "");
  const [parentTypeId, setParentTypeId] = useState<string>(
    type.parent_type_id ?? "__none__",
  );
  const [schemaText, setSchemaText] = useState(
    JSON.stringify(type.metadata_schema, null, 2),
  );
  const [schemaError, setSchemaError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // Re-sync when type prop changes
  useEffect(() => {
    if (open) {
      setName(type.name);
      setDescription(type.description ?? "");
      setParentTypeId(type.parent_type_id ?? "__none__");
      setSchemaText(JSON.stringify(type.metadata_schema, null, 2));
      setSchemaError(null);
      setIsSubmitting(false);
      setShowDeleteConfirm(false);
      setIsDeleting(false);
    }
  }, [open, type]);

  // Filter: exclude current type and any types that already have a parent (prevent grandchild)
  const parentTypeOptions = existingTypes.filter(
    (t) => t.id !== type.id && t.parent_type_id === null,
  );

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSchemaError(null);

    let parsed: Record<string, unknown>;
    try {
      parsed = JSON.parse(schemaText) as Record<string, unknown>;
    } catch (err) {
      setSchemaError(
        `Invalid JSON: ${err instanceof Error ? err.message : String(err)}`,
      );
      return;
    }

    setIsSubmitting(true);
    try {
      await updateDocumentType(type.id, {
        name: name.trim(),
        description: description.trim() || null,
        metadata_schema: parsed,
        parent_type_id: parentTypeId === "__none__" ? null : parentTypeId || null,
      });
      toast.success("Type updated");
      onSuccess();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to update type");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDelete() {
    setIsDeleting(true);
    try {
      await deleteDocumentType(type.id);
      toast.success("Type deleted");
      setShowDeleteConfirm(false);
      onSuccess();
      onOpenChange(false);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to delete type");
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Edit Document Type</DialogTitle>
          </DialogHeader>

          <form onSubmit={handleSubmit}>
            <div className="space-y-4 py-2">
              {/* Name */}
              <div className="space-y-1.5">
                <Label htmlFor="edit-type-name">
                  Name <span className="text-destructive" aria-hidden="true">*</span>
                </Label>
                <Input
                  id="edit-type-name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  aria-required="true"
                />
              </div>

              {/* Description */}
              <div className="space-y-1.5">
                <Label htmlFor="edit-type-description">Description</Label>
                <Textarea
                  id="edit-type-description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="resize-none min-h-[60px]"
                />
              </div>

              {/* Parent Type */}
              <div className="space-y-1.5">
                <Label htmlFor="edit-parent-type">Parent Type</Label>
                <Select value={parentTypeId} onValueChange={setParentTypeId}>
                  <SelectTrigger id="edit-parent-type" className="w-full">
                    <SelectValue placeholder="Select parent type..." />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none__">None</SelectItem>
                    {parentTypeOptions.map((t) => (
                      <SelectItem key={t.id} value={t.id}>
                        {t.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Schema Editor */}
              <SchemaEditor
                value={schemaText}
                onChange={setSchemaText}
                error={schemaError}
              />
            </div>

            <DialogFooter className="mt-4 flex items-center justify-between">
              <Button
                type="button"
                variant="destructive"
                onClick={() => setShowDeleteConfirm(true)}
                disabled={isSubmitting || isDeleting}
              >
                Delete Type
              </Button>
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => onOpenChange(false)}
                  disabled={isSubmitting}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={isSubmitting || !name.trim()}>
                  {isSubmitting ? "Saving..." : "Save Type"}
                </Button>
              </div>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete confirmation dialog */}
      <Dialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Delete {type.name}?</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            This will remove the type definition. Documents currently using this
            type will become untyped.
          </p>
          <DialogFooter className="mt-4">
            <Button
              variant="outline"
              onClick={() => setShowDeleteConfirm(false)}
              autoFocus
              disabled={isDeleting}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={isDeleting}
            >
              {isDeleting ? "Deleting..." : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
