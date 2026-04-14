import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link2, Plus, Trash2, ArrowRight } from "lucide-react";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import {
  fetchRelationships,
  deleteRelationship,
  relationshipKeys,
  RELATIONSHIP_TYPE_LABELS,
  type RelationshipResponse,
  type RelationshipType,
} from "../../api/relationships";
import { AddRelationshipDialog } from "./AddRelationshipDialog";

interface RelationshipPanelProps {
  documentId: string;
  onNavigate?: (documentId: string) => void;
}

const TYPE_COLORS: Record<RelationshipType, string> = {
  supersedes: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200",
  references: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  is_part_of: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200",
  related_to: "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200",
};

export function RelationshipPanel({
  documentId,
  onNavigate,
}: RelationshipPanelProps) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const queryClient = useQueryClient();

  const { data: relationships = [], isLoading } = useQuery({
    queryKey: relationshipKeys.forDocument(documentId),
    queryFn: () => fetchRelationships(documentId),
    enabled: !!documentId,
  });

  const deleteMutation = useMutation({
    mutationFn: (relId: string) => deleteRelationship(documentId, relId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: relationshipKeys.forDocument(documentId),
      });
    },
  });

  function getRelatedInfo(rel: RelationshipResponse) {
    const isSource = rel.source_document_id === documentId;
    return {
      relatedDocId: isSource
        ? rel.target_document_id
        : rel.source_document_id,
      relatedTitle: isSource
        ? rel.target_document_title
        : rel.source_document_title,
      direction: isSource ? "outgoing" : "incoming",
    };
  }

  if (isLoading) {
    return (
      <div className="px-6 py-4">
        <h4 className="text-sm font-medium flex items-center gap-1 mb-2">
          <Link2 className="h-4 w-4" /> Relationships
        </h4>
        <p className="text-xs text-muted-foreground">Loading...</p>
      </div>
    );
  }

  return (
    <div className="px-6 py-4">
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-medium flex items-center gap-1">
          <Link2 className="h-4 w-4" /> Relationships
          {relationships.length > 0 && (
            <span className="text-xs text-muted-foreground ml-1">
              ({relationships.length})
            </span>
          )}
        </h4>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setDialogOpen(true)}
        >
          <Plus className="h-3 w-3 mr-1" /> Add
        </Button>
      </div>

      {relationships.length === 0 ? (
        <p className="text-xs text-muted-foreground">
          No relationships defined
        </p>
      ) : (
        <div className="space-y-2">
          {relationships.map((rel) => {
            const { relatedDocId, relatedTitle, direction } =
              getRelatedInfo(rel);
            const typeLabel =
              RELATIONSHIP_TYPE_LABELS[
                rel.relationship_type as RelationshipType
              ] ?? rel.relationship_type;

            return (
              <div
                key={rel.id}
                className="flex items-center gap-2 text-sm group"
              >
                <Badge
                  className={`text-xs shrink-0 ${TYPE_COLORS[rel.relationship_type as RelationshipType] ?? ""}`}
                  variant="outline"
                >
                  {typeLabel}
                </Badge>

                {direction === "outgoing" && (
                  <ArrowRight className="h-3 w-3 shrink-0 text-muted-foreground" />
                )}

                <button
                  className="text-sm text-primary hover:underline truncate text-left"
                  onClick={() => onNavigate?.(relatedDocId)}
                  title={relatedTitle ?? relatedDocId}
                >
                  {relatedTitle ?? relatedDocId}
                </button>

                {direction === "incoming" && (
                  <span className="text-xs text-muted-foreground shrink-0">
                    (incoming)
                  </span>
                )}

                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100 shrink-0 ml-auto"
                  onClick={() => deleteMutation.mutate(rel.id)}
                  title="Remove relationship"
                >
                  <Trash2 className="h-3 w-3 text-destructive" />
                </Button>
              </div>
            );
          })}
        </div>
      )}

      <AddRelationshipDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        sourceDocumentId={documentId}
      />
    </div>
  );
}
