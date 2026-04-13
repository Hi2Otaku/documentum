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
import { createDocumentType } from "../../api/documentTypes";
import type { DocumentTypeResponse } from "../../api/documentTypes";

const DEFAULT_SCHEMA_TEXT = `{
  "type": "object",
  "properties": {},
  "required": []
}`;

interface CreateTypeDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
  existingTypes: DocumentTypeResponse[];
}

export function CreateTypeDialog({
  open,
  onOpenChange,
  onSuccess,
  existingTypes,
}: CreateTypeDialogProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [parentTypeId, setParentTypeId] = useState<string>("__none__");
  const [schemaText, setSchemaText] = useState(DEFAULT_SCHEMA_TEXT);
  const [schemaError, setSchemaError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Reset state when dialog opens
  useEffect(() => {
    if (open) {
      setName("");
      setDescription("");
      setParentTypeId("__none__");
      setSchemaText(DEFAULT_SCHEMA_TEXT);
      setSchemaError(null);
      setIsSubmitting(false);
    }
  }, [open]);

  // Only allow root types as parent (prevent grandchild)
  const parentTypeOptions = existingTypes.filter(
    (t) => t.parent_type_id === null,
  );

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSchemaError(null);

    // Parse and validate JSON schema
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
      await createDocumentType({
        name: name.trim(),
        description: description.trim() || null,
        metadata_schema: parsed,
        parent_type_id: parentTypeId === "__none__" ? null : parentTypeId || null,
      });
      toast.success("Type created");
      onSuccess();
      onOpenChange(false);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to create type");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Create Document Type</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit}>
          <div className="space-y-4 py-2">
            {/* Name */}
            <div className="space-y-1.5">
              <Label htmlFor="type-name">
                Name <span className="text-destructive" aria-hidden="true">*</span>
              </Label>
              <Input
                id="type-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                aria-required="true"
                placeholder="e.g. Invoice"
              />
            </div>

            {/* Description */}
            <div className="space-y-1.5">
              <Label htmlFor="type-description">Description</Label>
              <Textarea
                id="type-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Optional description"
                className="resize-none min-h-[60px]"
              />
            </div>

            {/* Parent Type */}
            <div className="space-y-1.5">
              <Label htmlFor="parent-type">Parent Type</Label>
              <Select value={parentTypeId} onValueChange={setParentTypeId}>
                <SelectTrigger id="parent-type" className="w-full">
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

          <DialogFooter className="mt-4">
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
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
