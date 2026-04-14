import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import { Textarea } from "../ui/textarea";
import {
  createRelationship,
  relationshipKeys,
  RELATIONSHIP_TYPES,
  RELATIONSHIP_TYPE_LABELS,
  type RelationshipType,
} from "../../api/relationships";
import { fetchDocuments } from "../../api/documents";

interface AddRelationshipDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  sourceDocumentId: string;
}

export function AddRelationshipDialog({
  open,
  onOpenChange,
  sourceDocumentId,
}: AddRelationshipDialogProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [relType, setRelType] = useState<RelationshipType>("references");
  const [description, setDescription] = useState("");
  const queryClient = useQueryClient();

  // Search documents for the picker
  const { data: searchResults } = useQuery({
    queryKey: ["documents", "search", searchTerm],
    queryFn: () => fetchDocuments({ title: searchTerm, page_size: 10 }),
    enabled: searchTerm.length >= 2,
  });

  const filteredDocs = (searchResults?.data ?? []).filter(
    (d) => d.id !== sourceDocumentId && !d.is_deleted,
  );

  const mutation = useMutation({
    mutationFn: () =>
      createRelationship(sourceDocumentId, {
        target_document_id: selectedDocId!,
        relationship_type: relType,
        description: description || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: relationshipKeys.forDocument(sourceDocumentId),
      });
      resetAndClose();
    },
  });

  function resetAndClose() {
    setSearchTerm("");
    setSelectedDocId(null);
    setRelType("references");
    setDescription("");
    onOpenChange(false);
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add Relationship</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Relationship type */}
          <div className="space-y-2">
            <Label>Relationship Type</Label>
            <Select
              value={relType}
              onValueChange={(v) => setRelType(v as RelationshipType)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {RELATIONSHIP_TYPES.map((t) => (
                  <SelectItem key={t} value={t}>
                    {RELATIONSHIP_TYPE_LABELS[t]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Target document search */}
          <div className="space-y-2">
            <Label>Target Document</Label>
            <Input
              placeholder="Search by title..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setSelectedDocId(null);
              }}
            />
            {filteredDocs.length > 0 && !selectedDocId && (
              <div className="max-h-40 overflow-y-auto border rounded-md">
                {filteredDocs.map((doc) => (
                  <button
                    key={doc.id}
                    className="w-full text-left px-3 py-2 text-sm hover:bg-accent truncate"
                    onClick={() => {
                      setSelectedDocId(doc.id);
                      setSearchTerm(doc.title);
                    }}
                  >
                    {doc.title}
                  </button>
                ))}
              </div>
            )}
            {selectedDocId && (
              <p className="text-xs text-muted-foreground">
                Selected: {searchTerm}
              </p>
            )}
          </div>

          {/* Optional description */}
          <div className="space-y-2">
            <Label>Description (optional)</Label>
            <Textarea
              placeholder="Describe the relationship..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
            />
          </div>

          {mutation.isError && (
            <p className="text-sm text-destructive">
              {(mutation.error as Error).message}
            </p>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={resetAndClose}>
            Cancel
          </Button>
          <Button
            onClick={() => mutation.mutate()}
            disabled={!selectedDocId || mutation.isPending}
          >
            {mutation.isPending ? "Adding..." : "Add"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
