import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Card, CardHeader, CardTitle, CardContent } from "../ui/card";
import { Button } from "../ui/button";
import { Separator } from "../ui/separator";
import { Skeleton } from "../ui/skeleton";
import { VirtualDocumentChildrenList } from "./VirtualDocumentChildrenList";
import { AddChildDialog } from "./AddChildDialog";
import {
  fetchVirtualDocument,
  reorderChildren,
  removeChild,
  downloadMergedPdf,
} from "../../api/virtualDocuments";
import { useState } from "react";

interface VirtualDocumentDetailPanelProps {
  virtualDocumentId: string | null;
}

export function VirtualDocumentDetailPanel({
  virtualDocumentId,
}: VirtualDocumentDetailPanelProps) {
  const queryClient = useQueryClient();
  const [isDownloading, setIsDownloading] = useState(false);

  const { data: vdoc, isLoading } = useQuery({
    queryKey: ["virtual-documents", virtualDocumentId],
    queryFn: () => fetchVirtualDocument(virtualDocumentId!),
    enabled: !!virtualDocumentId,
  });

  const reorderMutation = useMutation({
    mutationFn: (childIds: string[]) =>
      reorderChildren(virtualDocumentId!, childIds),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["virtual-documents", virtualDocumentId],
      });
    },
    onError: (error: Error) => {
      toast.error("Failed to reorder: " + error.message);
    },
  });

  const removeMutation = useMutation({
    mutationFn: (childId: string) =>
      removeChild(virtualDocumentId!, childId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["virtual-documents", virtualDocumentId],
      });
      toast.success("Child removed");
    },
    onError: (error: Error) => {
      toast.error("Failed to remove child: " + error.message);
    },
  });

  async function handleDownloadPdf() {
    if (!virtualDocumentId) return;
    setIsDownloading(true);
    try {
      await downloadMergedPdf(virtualDocumentId);
      toast.success("PDF downloaded");
    } catch (error) {
      toast.error(
        "Failed to generate PDF: " +
          (error instanceof Error ? error.message : "Unknown error"),
      );
    } finally {
      setIsDownloading(false);
    }
  }

  // No selection
  if (!virtualDocumentId) {
    return (
      <div className="flex flex-col items-center justify-center h-full">
        <h3 className="text-lg font-semibold">Select a virtual document</h3>
        <p className="text-sm text-muted-foreground mt-1">
          Click a row in the table to view its details.
        </p>
      </div>
    );
  }

  // Loading
  if (isLoading || !vdoc) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-6 w-[60%]" />
        <Card>
          <CardContent className="p-4 space-y-3">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
          </CardContent>
        </Card>
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  const existingChildDocIds = vdoc.children.map((c) => c.child_document_id);

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      {/* Header */}
      <div className="p-6">
        <h2 className="text-base font-semibold">
          {vdoc.document_title ?? "Untitled Virtual Document"}
        </h2>
        {vdoc.description && (
          <p className="text-sm text-muted-foreground mt-1">
            {vdoc.description}
          </p>
        )}
      </div>

      {/* Info Card */}
      <div className="px-6">
        <Card>
          <CardHeader className="p-4 pb-0">
            <CardTitle className="text-sm font-semibold">
              Virtual Document Info
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-3">
            <div className="grid grid-cols-2 gap-y-2 gap-x-4">
              <span className="text-xs text-muted-foreground">Created</span>
              <span className="text-sm">
                {new Date(vdoc.created_at).toLocaleDateString()}
              </span>

              <span className="text-xs text-muted-foreground">Updated</span>
              <span className="text-sm">
                {new Date(vdoc.updated_at).toLocaleDateString()}
              </span>

              <span className="text-xs text-muted-foreground">Children</span>
              <span className="text-sm">{vdoc.children.length} document(s)</span>
            </div>
          </CardContent>
        </Card>
      </div>

      <Separator className="my-4" />

      {/* Children Section */}
      <div className="px-6 pb-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold">Children</h3>
          <AddChildDialog
            virtualDocId={virtualDocumentId}
            existingChildIds={existingChildDocIds}
            onSuccess={() =>
              queryClient.invalidateQueries({
                queryKey: ["virtual-documents", virtualDocumentId],
              })
            }
          />
        </div>
        <VirtualDocumentChildrenList
          children={vdoc.children}
          virtualDocId={virtualDocumentId}
          onReorder={(ids) => reorderMutation.mutate(ids)}
          onRemove={(id) => removeMutation.mutate(id)}
        />
      </div>

      <Separator />

      {/* Merge PDF */}
      <div className="px-6 py-4">
        <Button
          className="w-full"
          disabled={vdoc.children.length === 0 || isDownloading}
          onClick={handleDownloadPdf}
        >
          {isDownloading ? "Generating PDF..." : "Generate Merged PDF"}
        </Button>
        {vdoc.children.length === 0 && (
          <p className="text-xs text-muted-foreground mt-2 text-center">
            Add at least one child document to generate a merged PDF.
          </p>
        )}
      </div>
    </div>
  );
}
