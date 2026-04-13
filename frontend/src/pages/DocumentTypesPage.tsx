import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Tags } from "lucide-react";
import { Button } from "../components/ui/button";
import { DocumentTypeTable } from "../components/admin/DocumentTypeTable";
import { CreateTypeDialog } from "../components/admin/CreateTypeDialog";
import { EditTypeDialog } from "../components/admin/EditTypeDialog";
import { fetchDocumentTypes } from "../api/documentTypes";
import type { DocumentTypeResponse } from "../api/documentTypes";

export function DocumentTypesPage() {
  const queryClient = useQueryClient();
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [editingType, setEditingType] = useState<DocumentTypeResponse | null>(
    null,
  );

  const { data: types = [], isLoading } = useQuery({
    queryKey: ["documentTypes"],
    queryFn: fetchDocumentTypes,
  });

  function handleSuccess() {
    queryClient.invalidateQueries({ queryKey: ["documentTypes"] });
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Tags className="h-5 w-5 text-muted-foreground" />
          <h1 className="text-lg font-semibold">Document Types</h1>
        </div>
        <Button onClick={() => setShowCreateDialog(true)}>Create Type</Button>
      </div>

      {/* Table */}
      <DocumentTypeTable
        types={types}
        isLoading={isLoading}
        onEdit={setEditingType}
      />

      {/* Dialogs */}
      <CreateTypeDialog
        open={showCreateDialog}
        onOpenChange={setShowCreateDialog}
        onSuccess={handleSuccess}
        existingTypes={types}
      />

      {editingType && (
        <EditTypeDialog
          open={editingType !== null}
          onOpenChange={(open) => {
            if (!open) setEditingType(null);
          }}
          onSuccess={() => {
            handleSuccess();
            setEditingType(null);
          }}
          type={editingType}
          existingTypes={types}
        />
      )}
    </div>
  );
}
