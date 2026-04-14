import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link2, Plus, Trash2, ArrowUpRight, ArrowDownLeft, LinkIcon } from "lucide-react";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import { Skeleton } from "../ui/skeleton";
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

interface RelatedInfo {
  relatedDocId: string;
  relatedTitle: string | null;
  direction: "outgoing" | "incoming";
  rel: RelationshipResponse;
}

export function RelationshipPanel({
  documentId,
  onNavigate,
}: RelationshipPanelProps) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const queryClient = useQueryClient();

  const { data: relationships = [], isLoading } = useQuery({
    queryKey: relationshipKeys.list(documentId),
    queryFn: () => fetchRelationships(documentId),
    enabled: !!documentId,
  });

  const deleteMutation = useMutation({
    mutationFn: (relId: string) => deleteRelationship(documentId, relId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: relationshipKeys.list(documentId),
      });
    },
  });

  function getRelatedInfo(rel: RelationshipResponse): RelatedInfo {
    const isSource = rel.source_document_id === documentId;
    return {
      relatedDocId: isSource
        ? rel.target_document_id
        : rel.source_document_id,
      relatedTitle: isSource
        ? rel.target_document_title
        : rel.source_document_title,
      direction: isSource ? "outgoing" : "incoming",
      rel,
    };
  }

  // Loading skeleton
  if (isLoading) {
    return (
      <div className="px-6 py-4">
        <h4 className="text-sm font-medium flex items-center gap-1 mb-3">
          <Link2 className="h-4 w-4" /> Relationships
        </h4>
        <div className="space-y-2">
          <Skeleton className="h-5 w-20" />
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-5 w-20" />
          <Skeleton className="h-8 w-full" />
        </div>
      </div>
    );
  }

  // Group by direction
  const allRelated = relationships.map(getRelatedInfo);
  const outgoing = allRelated.filter((r) => r.direction === "outgoing");
  const incoming = allRelated.filter((r) => r.direction === "incoming");

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
        <div className="flex flex-col items-center py-4 text-center">
          <LinkIcon className="h-8 w-8 text-muted-foreground/40 mb-2" />
          <p className="text-xs text-muted-foreground">
            No relationships
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {/* Outgoing section */}
          {outgoing.length > 0 && (
            <div>
              <div className="flex items-center gap-1 mb-1.5">
                <ArrowUpRight className="h-3.5 w-3.5 text-muted-foreground" />
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Outgoing ({outgoing.length})
                </span>
              </div>
              <div className="space-y-1.5">
                {outgoing.map((item) => (
                  <RelationshipRow
                    key={item.rel.id}
                    item={item}
                    onNavigate={onNavigate}
                    onDelete={(id) => deleteMutation.mutate(id)}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Incoming section */}
          {incoming.length > 0 && (
            <div>
              <div className="flex items-center gap-1 mb-1.5">
                <ArrowDownLeft className="h-3.5 w-3.5 text-muted-foreground" />
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Incoming ({incoming.length})
                </span>
              </div>
              <div className="space-y-1.5">
                {incoming.map((item) => (
                  <RelationshipRow
                    key={item.rel.id}
                    item={item}
                    onNavigate={onNavigate}
                    onDelete={(id) => deleteMutation.mutate(id)}
                  />
                ))}
              </div>
            </div>
          )}
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

// --- Internal row component ---

function RelationshipRow({
  item,
  onNavigate,
  onDelete,
}: {
  item: RelatedInfo;
  onNavigate?: (documentId: string) => void;
  onDelete: (relId: string) => void;
}) {
  const typeLabel =
    RELATIONSHIP_TYPE_LABELS[
      item.rel.relationship_type as RelationshipType
    ] ?? item.rel.relationship_type;

  return (
    <div className="flex items-center gap-2 text-sm group">
      <Badge
        className={`text-xs shrink-0 ${TYPE_COLORS[item.rel.relationship_type as RelationshipType] ?? ""}`}
        variant="outline"
      >
        {typeLabel}
      </Badge>

      <button
        className="text-sm text-primary hover:underline truncate text-left"
        onClick={() => onNavigate?.(item.relatedDocId)}
        title={item.relatedTitle ?? item.relatedDocId}
      >
        {item.relatedTitle ?? item.relatedDocId}
      </button>

      {item.rel.description && (
        <span className="text-xs text-muted-foreground truncate hidden sm:inline">
          {item.rel.description}
        </span>
      )}

      <Button
        variant="ghost"
        size="sm"
        className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100 shrink-0 ml-auto"
        onClick={() => onDelete(item.rel.id)}
        title="Remove relationship"
      >
        <Trash2 className="h-3 w-3 text-destructive" />
      </Button>
    </div>
  );
}
