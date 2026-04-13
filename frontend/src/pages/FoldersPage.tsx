import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { FolderOpen, Plus, Pencil, Move, Copy, Trash2, FolderPlus } from "lucide-react";
import { Button } from "../components/ui/button";
import { Skeleton } from "../components/ui/skeleton";
import { Separator } from "../components/ui/separator";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../components/ui/tabs";
import { FolderTree } from "../components/folders/FolderTree";
import { FolderBreadcrumb } from "../components/folders/FolderBreadcrumb";
import { CreateFolderDialog } from "../components/folders/CreateFolderDialog";
import { RenameFolderDialog } from "../components/folders/RenameFolderDialog";
import { MoveFolderDialog } from "../components/folders/MoveFolderDialog";
import { FolderPickerDialog } from "../components/folders/FolderPickerDialog";
import { FolderPermissionsTab } from "../components/folders/FolderPermissionsTab";
import {
  fetchFolderTree,
  fetchFolder,
  deleteFolder,
  copyFolder,
  folderKeys,
  type FolderTreeNode,
} from "../api/folders";

export function FoldersPage() {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Dialog state
  const [createOpen, setCreateOpen] = useState(false);
  const [createParentId, setCreateParentId] = useState<string | undefined>(undefined);
  const [renameOpen, setRenameOpen] = useState(false);
  const [moveOpen, setMoveOpen] = useState(false);
  const [copyOpen, setCopyOpen] = useState(false);
  const [actionTarget, setActionTarget] = useState<{
    id: string;
    name: string;
  } | null>(null);

  // Fetch folder tree
  const { data: tree = [], isLoading: treeLoading } = useQuery({
    queryKey: folderKeys.tree(),
    queryFn: fetchFolderTree,
  });

  // Fetch selected folder detail
  const { data: selectedFolder } = useQuery({
    queryKey: folderKeys.detail(selectedId ?? ""),
    queryFn: () => fetchFolder(selectedId!),
    enabled: !!selectedId,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteFolder(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: folderKeys.tree() });
      setSelectedId(null);
    },
  });

  const copyMutation = useMutation({
    mutationFn: ({ id, destId }: { id: string; destId?: string }) =>
      copyFolder(id, destId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: folderKeys.tree() });
    },
  });

  function handleContextAction(action: string, node: FolderTreeNode) {
    setActionTarget({ id: node.id, name: node.name });
    if (action === "rename") {
      setRenameOpen(true);
    } else if (action === "move") {
      setMoveOpen(true);
    } else if (action === "copy") {
      setCopyOpen(true);
    } else if (action === "delete") {
      if (window.confirm(`Delete "${node.name}" and all its contents?`)) {
        deleteMutation.mutate(node.id);
      }
    } else if (action === "new-subfolder") {
      setCreateParentId(node.id);
      setCreateOpen(true);
    }
  }

  function handleNewCabinet() {
    setCreateParentId(undefined);
    setCreateOpen(true);
  }

  function handleNewSubfolder() {
    if (!selectedId) return;
    setCreateParentId(selectedId);
    setCreateOpen(true);
  }

  function handleRename() {
    if (!selectedFolder) return;
    setActionTarget({ id: selectedFolder.id, name: selectedFolder.name });
    setRenameOpen(true);
  }

  function handleMove() {
    if (!selectedFolder) return;
    setActionTarget({ id: selectedFolder.id, name: selectedFolder.name });
    setMoveOpen(true);
  }

  function handleCopy() {
    if (!selectedFolder) return;
    setActionTarget({ id: selectedFolder.id, name: selectedFolder.name });
    setCopyOpen(true);
  }

  function handleDelete() {
    if (!selectedFolder) return;
    if (window.confirm(`Delete "${selectedFolder.name}" and all its contents?`)) {
      deleteMutation.mutate(selectedFolder.id);
    }
  }

  function handleCopySelect(destId: string) {
    if (!actionTarget) return;
    copyMutation.mutate({ id: actionTarget.id, destId });
  }

  return (
    <div className="flex flex-col h-full">
      {/* Page header */}
      <div className="flex items-center justify-between px-6 py-4 border-b">
        <div className="flex items-center gap-2">
          <FolderOpen className="h-5 w-5 text-muted-foreground" />
          <h1 className="text-lg font-semibold">Folders</h1>
        </div>
        <Button onClick={handleNewCabinet} size="sm">
          <Plus className="h-4 w-4 mr-1" />
          New Cabinet
        </Button>
      </div>

      {/* Main content: tree + detail */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left panel: folder tree */}
        <div className="w-64 border-r overflow-y-auto shrink-0">
          <div className="py-2">
            {treeLoading ? (
              <div className="px-4 space-y-2">
                <Skeleton className="h-5 w-full" />
                <Skeleton className="h-5 w-[80%]" />
                <Skeleton className="h-5 w-[70%]" />
              </div>
            ) : (
              <FolderTree
                tree={tree}
                selectedId={selectedId}
                onSelect={setSelectedId}
                onContextAction={handleContextAction}
              />
            )}
          </div>
        </div>

        {/* Right panel: folder detail */}
        <div className="flex-1 overflow-y-auto p-6">
          {!selectedId ? (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <FolderOpen className="h-12 w-12 text-muted-foreground mb-3" />
              <h3 className="text-base font-medium">Select a folder</h3>
              <p className="text-sm text-muted-foreground mt-1">
                Click a cabinet or folder in the tree to view details.
              </p>
            </div>
          ) : !selectedFolder ? (
            <div className="space-y-3">
              <Skeleton className="h-6 w-48" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-[80%]" />
            </div>
          ) : (
            <div className="space-y-4">
              {/* Breadcrumb stays above tabs */}
              <FolderBreadcrumb
                path={selectedFolder.path}
                onNavigate={setSelectedId}
              />

              <Tabs defaultValue="details">
                <TabsList>
                  <TabsTrigger value="details">Details</TabsTrigger>
                  <TabsTrigger value="permissions">Permissions</TabsTrigger>
                </TabsList>

                <TabsContent value="details">
                  {/* Folder info */}
                  <div className="space-y-4 pt-4">
                    <div>
                      <h2 className="text-lg font-semibold">{selectedFolder.name}</h2>
                      {selectedFolder.description && (
                        <p className="text-sm text-muted-foreground mt-1">
                          {selectedFolder.description}
                        </p>
                      )}
                      <p className="text-sm text-muted-foreground mt-1">
                        {selectedFolder.document_count} document
                        {selectedFolder.document_count !== 1 ? "s" : ""}
                        {selectedFolder.is_cabinet ? " · Cabinet" : " · Folder"}
                      </p>
                    </div>

                    <Separator />

                    {/* Action buttons */}
                    <div className="flex flex-wrap gap-2">
                      <Button variant="outline" size="sm" onClick={handleNewSubfolder}>
                        <FolderPlus className="h-4 w-4 mr-1" />
                        New Subfolder
                      </Button>
                      <Button variant="outline" size="sm" onClick={handleRename}>
                        <Pencil className="h-4 w-4 mr-1" />
                        Rename
                      </Button>
                      {!selectedFolder.is_cabinet && (
                        <Button variant="outline" size="sm" onClick={handleMove}>
                          <Move className="h-4 w-4 mr-1" />
                          Move
                        </Button>
                      )}
                      <Button variant="outline" size="sm" onClick={handleCopy}>
                        <Copy className="h-4 w-4 mr-1" />
                        Copy
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleDelete}
                        className="text-destructive hover:text-destructive"
                        disabled={deleteMutation.isPending}
                      >
                        <Trash2 className="h-4 w-4 mr-1" />
                        Delete
                      </Button>
                    </div>
                  </div>
                </TabsContent>

                <TabsContent value="permissions">
                  <FolderPermissionsTab folderId={selectedFolder.id} />
                </TabsContent>
              </Tabs>
            </div>
          )}
        </div>
      </div>

      {/* Dialogs */}
      <CreateFolderDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        parentId={createParentId}
      />

      <RenameFolderDialog
        open={renameOpen}
        onOpenChange={setRenameOpen}
        folder={actionTarget}
      />

      <MoveFolderDialog
        open={moveOpen}
        onOpenChange={setMoveOpen}
        folder={actionTarget}
      />

      <FolderPickerDialog
        open={copyOpen}
        onOpenChange={setCopyOpen}
        title={`Copy "${actionTarget?.name ?? "folder"}" to…`}
        onSelect={handleCopySelect}
        excludeId={actionTarget?.id}
      />
    </div>
  );
}
