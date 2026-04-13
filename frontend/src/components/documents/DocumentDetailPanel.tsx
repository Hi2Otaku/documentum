import React from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardHeader, CardTitle, CardContent } from "../ui/card";
import { Separator } from "../ui/separator";
import { Skeleton } from "../ui/skeleton";
import { LifecycleStateBadge } from "./LifecycleStateBadge";
import { LockIndicator } from "./LockIndicator";
import { DocumentActions } from "./DocumentActions";
import { VersionHistoryList } from "./VersionHistoryList";
import { useSelectedType } from "./TypeSelector";
import { fetchDocument } from "../../api/documents";

interface DocumentDetailPanelProps {
  documentId: string | null;
  currentUserId: string;
}

export function DocumentDetailPanel({
  documentId,
  currentUserId,
}: DocumentDetailPanelProps) {
  const { data: document, isLoading } = useQuery({
    queryKey: ["documents", documentId],
    queryFn: () => fetchDocument(documentId!),
    enabled: !!documentId,
  });

  // Resolve the type schema from the cached documentTypes list (no extra fetch)
  const selectedType = useSelectedType(document?.document_type_id ?? null);

  // No selection state
  if (!documentId) {
    return (
      <div className="flex flex-col items-center justify-center h-full">
        <h3 className="text-lg font-semibold">Select a document</h3>
        <p className="text-sm text-muted-foreground mt-1">
          Click a row in the table to view its details.
        </p>
      </div>
    );
  }

  // Loading state
  if (isLoading || !document) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-6 w-[60%]" />
        <Card>
          <CardContent className="p-4 space-y-3">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
          </CardContent>
        </Card>
        <div className="flex gap-2">
          <Skeleton className="h-9 w-24" />
          <Skeleton className="h-9 w-24" />
        </div>
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-12 w-full" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      {/* Section 1 - Header */}
      <div className="p-6">
        <h2 className="text-base font-semibold break-words">{document.title}</h2>
        <div className="flex items-center gap-2 mt-2">
          <LifecycleStateBadge state={document.lifecycle_state} />
          <LockIndicator
            lockedBy={document.locked_by}
            currentUserId={currentUserId}
          />
        </div>
      </div>

      {/* Section 2 - Metadata Card */}
      <div className="px-6">
        <Card>
          <CardHeader className="p-4 pb-0">
            <CardTitle className="text-sm font-semibold">
              Document Info
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-3">
            <div className="grid grid-cols-[auto_1fr] gap-y-2 gap-x-4">
              <span className="text-xs text-muted-foreground">Filename</span>
              <span className="text-sm truncate" title={document.filename}>{document.filename}</span>

              <span className="text-xs text-muted-foreground">MIME Type</span>
              <span className="text-sm truncate" title={document.content_type}>{document.content_type}</span>

              <span className="text-xs text-muted-foreground">Doc Type</span>
              <span className="text-sm truncate">
                {document.document_type_name ?? "\u2014"}
              </span>

              <span className="text-xs text-muted-foreground">Author</span>
              <span className="text-sm truncate">{document.author ?? "Unknown"}</span>

              <span className="text-xs text-muted-foreground">Created</span>
              <span className="text-sm">
                {new Date(document.created_at).toLocaleDateString()}
              </span>

              <span className="text-xs text-muted-foreground">Updated</span>
              <span className="text-sm">
                {new Date(document.updated_at).toLocaleDateString()}
              </span>

              <span className="text-xs text-muted-foreground whitespace-nowrap">
                Current Version
              </span>
              <span className="text-sm">{document.current_version}</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Section 3 - Type Metadata */}
      {selectedType && Object.keys(document.custom_properties).length > 0 && (
        <div className="px-6 pb-4">
          <Card>
            <CardHeader className="p-4 pb-0">
              <CardTitle className="text-sm font-semibold">
                {selectedType.name} Metadata
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 pt-3">
              <div className="grid grid-cols-[auto_1fr] gap-y-2 gap-x-4">
                {Object.entries(document.custom_properties).map(([key, val]) => {
                  const schemaProp = (
                    selectedType.metadata_schema?.properties as
                      | Record<string, { title?: string }>
                      | undefined
                  )?.[key];
                  const label = schemaProp?.title ?? key;
                  const display =
                    val === null || val === undefined
                      ? "\u2014"
                      : typeof val === "boolean"
                        ? val ? "Yes" : "No"
                        : String(val);
                  return (
                    <React.Fragment key={key}>
                      <span className="text-xs text-muted-foreground whitespace-nowrap">
                        {label}
                      </span>
                      <span className="text-sm truncate" title={display}>
                        {display}
                      </span>
                    </React.Fragment>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Section 4 - Actions */}
      <div className="px-6 py-4">
        <DocumentActions document={document} currentUserId={currentUserId} />
      </div>

      {/* Section 5 - Separator */}
      <Separator />

      {/* Section 6 - Version History */}
      <div className="px-6 py-4">
        <h3 className="text-base font-semibold mb-3">Version History</h3>
        <VersionHistoryList documentId={documentId} />
      </div>
    </div>
  );
}
