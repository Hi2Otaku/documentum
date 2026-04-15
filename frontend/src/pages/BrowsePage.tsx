import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Archive,
  FolderOpen,
  PanelLeftClose,
  PanelLeft,
  File,
  FileText,
  FileSpreadsheet,
  Image,
  Search,
  Package,
} from "lucide-react";
import { Button } from "../components/ui/button";
import { Skeleton } from "../components/ui/skeleton";
import { Badge } from "../components/ui/badge";
import { Checkbox } from "../components/ui/checkbox";
import { BulkActionToolbar } from "../components/documents/BulkActionToolbar";
import { BulkJobDialog } from "../components/documents/BulkJobDialog";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "../components/ui/table";
import { FolderTree } from "../components/folders/FolderTree";
import { FolderBreadcrumb } from "../components/folders/FolderBreadcrumb";
import { DocumentDetailPanel } from "../components/documents/DocumentDetailPanel";
import { LifecycleStateBadge } from "../components/documents/LifecycleStateBadge";
import {
  fetchFolderTree,
  fetchFolder,
  fetchFolderDocuments,
  folderKeys,
} from "../api/folders";
import { fetchSmartFolders, savedSearchKeys } from "../api/savedSearches";
import { searchDocuments } from "../api/search";
import { useAuthStore } from "../stores/authStore";
import { ExportDialog } from "../components/browse/ExportDialog";

/** Minimal document shape returned by fetchFolderDocuments */
interface FolderDocument {
  id: string;
  title: string;
  content_type: string;
  document_type_name: string | null;
  lifecycle_state: string;
  updated_at: string;
}

interface FolderDocumentsResponse {
  data: FolderDocument[];
  meta: {
    total_pages: number;
    page: number;
    total: number;
  };
}

function FileTypeIcon({ contentType }: { contentType: string }) {
  if (contentType.startsWith("image/")) {
    return <Image className="h-4 w-4 text-muted-foreground" />;
  }
  if (contentType === "application/pdf") {
    return <FileText className="h-4 w-4 text-muted-foreground" />;
  }
  if (
    contentType.includes("spreadsheet") ||
    contentType.includes("excel") ||
    contentType === "text/csv"
  ) {
    return <FileSpreadsheet className="h-4 w-4 text-muted-foreground" />;
  }
  return <File className="h-4 w-4 text-muted-foreground" />;
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  const now = Date.now();
  const diffMs = now - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHour < 24) return `${diffHour}h ago`;
  if (diffDay < 30) return `${diffDay}d ago`;
  return date.toLocaleDateString();
}

export function BrowsePage() {
  const userId = useAuthStore((s) => s.userId) ?? "";

  const [selectedFolderId, setSelectedFolderId] = useState<string | null>(null);
  const [selectedSmartFolderId, setSelectedSmartFolderId] = useState<string | null>(null);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(
    null
  );
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedDocIds, setSelectedDocIds] = useState<Set<string>>(new Set());
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [exportOpen, setExportOpen] = useState(false);

  // Folder tree query
  const { data: tree = [], isLoading: treeLoading } = useQuery({
    queryKey: folderKeys.tree(),
    queryFn: fetchFolderTree,
  });

  // Smart folders query
  const { data: smartFolders = [] } = useQuery({
    queryKey: savedSearchKeys.smartFolders(),
    queryFn: fetchSmartFolders,
  });

  // Selected folder detail (provides path for breadcrumb)
  const { data: selectedFolder } = useQuery({
    queryKey: folderKeys.detail(selectedFolderId ?? ""),
    queryFn: () => fetchFolder(selectedFolderId!),
    enabled: !!selectedFolderId,
  });

  // Folder documents
  const { data: documentsData, isLoading: documentsLoading } = useQuery({
    queryKey: [...folderKeys.documents(selectedFolderId ?? ""), currentPage],
    queryFn: () =>
      fetchFolderDocuments(selectedFolderId!, currentPage) as Promise<FolderDocumentsResponse>,
    enabled: !!selectedFolderId,
  });

  // Find the selected smart folder object
  const activeSmartFolder = smartFolders.find((sf) => sf.id === selectedSmartFolderId);

  // Smart folder search results
  const { data: smartFolderResults, isLoading: smartFolderLoading } = useQuery({
    queryKey: ["smart-folder-results", selectedSmartFolderId],
    queryFn: () =>
      searchDocuments({
        q: activeSmartFolder!.query,
        folder_id: activeSmartFolder!.filters?.folder_id,
        document_type_id: activeSmartFolder!.filters?.document_type_id,
        lifecycle_state: activeSmartFolder!.filters?.lifecycle_state,
        page: 1,
        page_size: 50,
      }),
    enabled: !!selectedSmartFolderId && !!activeSmartFolder,
  });

  const documents = documentsData?.data ?? [];
  const totalPages = documentsData?.meta?.total_pages ?? 1;

  function handleFolderSelect(id: string) {
    setSelectedFolderId(id);
    setSelectedSmartFolderId(null);
    setSelectedDocumentId(null);
    setCurrentPage(1);
    setSelectedDocIds(new Set());
  }

  function handleSmartFolderSelect(id: string) {
    setSelectedSmartFolderId(id);
    setSelectedFolderId(null);
    setSelectedDocumentId(null);
    setCurrentPage(1);
    setSelectedDocIds(new Set());
  }

  function handleBreadcrumbNavigate(id: string) {
    setSelectedFolderId(id);
    setSelectedSmartFolderId(null);
    setSelectedDocumentId(null);
    setCurrentPage(1);
  }

  // Find child folders of selected folder from tree data
  function findNode(nodes: typeof tree, id: string): typeof tree[0] | null {
    for (const n of nodes) {
      if (n.id === id) return n;
      const found = findNode(n.children, id);
      if (found) return found;
    }
    return null;
  }
  const selectedNode = selectedFolderId ? findNode(tree, selectedFolderId) : null;
  const childFolders = selectedNode?.children ?? [];

  // Determine what to show in content area
  const showSmartFolder = !!selectedSmartFolderId && !!activeSmartFolder;
  const showFolder = !!selectedFolderId;
  const showEmpty = !showSmartFolder && !showFolder;

  return (
    <div className="flex flex-col h-full">
      {/* Page header */}
      <div className="flex items-center gap-2 px-6 py-4 border-b">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setSidebarCollapsed((prev) => !prev)}
          title={sidebarCollapsed ? "Show folder tree" : "Hide folder tree"}
        >
          {sidebarCollapsed ? (
            <PanelLeft className="h-4 w-4" />
          ) : (
            <PanelLeftClose className="h-4 w-4" />
          )}
        </Button>
        <FolderOpen className="h-5 w-5 text-muted-foreground" />
        <h1 className="text-lg font-semibold">Browse</h1>
        <div className="flex-1" />
        <Button
          variant="outline"
          size="sm"
          disabled={selectedDocIds.size === 0 && !selectedFolderId}
          onClick={() => setExportOpen(true)}
        >
          <Package className="h-4 w-4 mr-1" />
          Export
        </Button>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Left: Collapsible folder tree sidebar */}
        {!sidebarCollapsed && (
          <div className="w-64 border-r overflow-y-auto shrink-0">
            <div className="py-2">
              {treeLoading ? (
                <div className="px-4 space-y-2">
                  <Skeleton className="h-5 w-full" />
                  <Skeleton className="h-5 w-[80%]" />
                  <Skeleton className="h-5 w-[70%]" />
                  <Skeleton className="h-5 w-[60%]" />
                </div>
              ) : (
                <FolderTree
                  tree={tree}
                  selectedId={selectedFolderId}
                  onSelect={handleFolderSelect}
                  smartFolders={smartFolders.map((sf) => ({
                    id: sf.id,
                    name: sf.name,
                  }))}
                  selectedSmartFolderId={selectedSmartFolderId}
                  onSmartFolderSelect={handleSmartFolderSelect}
                />
              )}
            </div>
          </div>
        )}

        {/* Center: Document content area */}
        <div className="flex-1 flex flex-col overflow-hidden min-w-0">
          {/* Breadcrumb bar or Smart Folder header */}
          {showFolder && selectedFolder && (
            <div className="px-4 py-2 border-b shrink-0">
              <FolderBreadcrumb
                path={selectedFolder.path}
                onNavigate={handleBreadcrumbNavigate}
              />
            </div>
          )}
          {showSmartFolder && (
            <div className="px-4 py-2 border-b shrink-0 flex items-center gap-2">
              <Search className="h-4 w-4 text-violet-500" />
              <span className="text-sm font-medium">
                Smart Folder: {activeSmartFolder.name}
              </span>
            </div>
          )}

          {/* Bulk action toolbar */}
          {selectedDocIds.size > 0 && (
            <BulkActionToolbar
              selectedCount={selectedDocIds.size}
              selectedIds={Array.from(selectedDocIds)}
              onClear={() => setSelectedDocIds(new Set())}
              onJobStarted={(jobId) => setActiveJobId(jobId)}
            />
          )}

          {/* Content rendering */}
          {showEmpty ? (
            /* Repository root — show cabinets and top-level folders */
            <div className="flex flex-col flex-1 overflow-hidden">
              <div className="px-4 py-2 border-b shrink-0">
                <span className="text-sm font-medium text-muted-foreground">Repository</span>
              </div>
              {treeLoading ? (
                <div className="p-4 space-y-3">
                  {Array.from({ length: 4 }).map((_, i) => (
                    <Skeleton key={i} className="h-12 w-full" />
                  ))}
                </div>
              ) : tree.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-center">
                  <FolderOpen className="h-12 w-12 text-muted-foreground mb-3" />
                  <h3 className="text-base font-medium">No cabinets yet</h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    Create a cabinet from the Folders admin page to get started.
                  </p>
                </div>
              ) : (
                <div className="flex-1 overflow-auto p-4">
                  <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
                    {tree.map((node) => (
                      <button
                        key={node.id}
                        className="flex flex-col items-center gap-2 p-4 rounded-lg border hover:bg-accent hover:border-primary/30 transition-colors text-center group"
                        onClick={() => handleFolderSelect(node.id)}
                      >
                        {node.is_cabinet ? (
                          <Archive className="h-10 w-10 text-amber-500 group-hover:text-amber-600" />
                        ) : (
                          <FolderOpen className="h-10 w-10 text-blue-500 group-hover:text-blue-600" />
                        )}
                        <span className="text-sm font-medium truncate w-full">{node.name}</span>
                        <span className="text-xs text-muted-foreground">
                          {node.document_count} doc{node.document_count !== 1 ? "s" : ""}
                          {node.children.length > 0 && ` \u00B7 ${node.children.length} folder${node.children.length !== 1 ? "s" : ""}`}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : showSmartFolder ? (
            /* Smart folder results */
            smartFolderLoading ? (
              <div className="p-4 space-y-3 flex-1">
                {Array.from({ length: 6 }).map((_, i) => (
                  <Skeleton key={i} className="h-12 w-full" />
                ))}
              </div>
            ) : !smartFolderResults?.data?.length ? (
              <div className="flex flex-col items-center justify-center h-full text-center">
                <Search className="h-10 w-10 text-muted-foreground mb-3" />
                <h3 className="text-base font-medium">No results</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  This smart folder's search returned no documents.
                </p>
              </div>
            ) : (
              <div className="flex flex-col flex-1 overflow-hidden">
                <div className="flex-1 overflow-auto">
                  <Table>
                    <TableHeader>
                      <TableRow className="h-10 bg-secondary">
                        <TableHead className="w-10" />
                        <TableHead>Title</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>Lifecycle</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {smartFolderResults.data.map((doc) => (
                        <TableRow
                          key={doc.id}
                          className={`cursor-pointer hover:bg-accent/50 ${
                            doc.id === selectedDocumentId
                              ? "bg-accent border-l-[3px] border-primary"
                              : ""
                          }`}
                          onClick={() => setSelectedDocumentId(doc.id)}
                        >
                          <TableCell className="w-10 px-3">
                            <FileTypeIcon contentType={doc.content_type} />
                          </TableCell>
                          <TableCell>
                            <span className="text-sm font-medium">
                              {doc.title}
                            </span>
                            {doc.headline && (
                              <p
                                className="text-xs text-muted-foreground mt-0.5 line-clamp-1"
                                dangerouslySetInnerHTML={{ __html: doc.headline }}
                              />
                            )}
                          </TableCell>
                          <TableCell>
                            {doc.document_type_name ? (
                              <Badge variant="outline" className="text-xs">
                                {doc.document_type_name}
                              </Badge>
                            ) : (
                              <span className="text-xs text-muted-foreground">
                                --
                              </span>
                            )}
                          </TableCell>
                          <TableCell>
                            <LifecycleStateBadge state={doc.lifecycle_state ?? "draft"} />
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
                <div className="h-10 flex items-center px-4 border-t shrink-0">
                  <span className="text-sm text-muted-foreground">
                    {smartFolderResults.data.length} result
                    {smartFolderResults.data.length !== 1 ? "s" : ""}
                  </span>
                </div>
              </div>
            )
          ) : documentsLoading ? (
            /* Loading state */
            <div className="p-4 space-y-3 flex-1">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : documents.length === 0 && childFolders.length === 0 ? (
            /* Empty folder */
            <div className="flex flex-col items-center justify-center h-full text-center">
              <FolderOpen className="h-10 w-10 text-muted-foreground mb-3" />
              <h3 className="text-base font-medium">No documents in this folder</h3>
              <p className="text-sm text-muted-foreground mt-1">
                This folder is empty. File documents here from the Documents page.
              </p>
            </div>
          ) : (
            /* Child folders + Document table */
            <div className="flex flex-col flex-1 overflow-hidden">
              <div className="flex-1 overflow-auto">
                {/* Child folders */}
                {childFolders.length > 0 && (
                  <div className="p-4 pb-2">
                    <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 gap-2">
                      {childFolders.map((child) => (
                        <button
                          key={child.id}
                          className="flex flex-col items-center gap-1.5 p-3 rounded-lg border hover:bg-accent hover:border-primary/30 transition-colors text-center group"
                          onClick={() => handleFolderSelect(child.id)}
                        >
                          <FolderOpen className="h-8 w-8 text-blue-500 group-hover:text-blue-600" />
                          <span className="text-xs font-medium truncate w-full">{child.name}</span>
                          <span className="text-[10px] text-muted-foreground">
                            {child.document_count} doc{child.document_count !== 1 ? "s" : ""}
                          </span>
                        </button>
                      ))}
                    </div>
                    {documents.length > 0 && (
                      <div className="border-t mt-3" />
                    )}
                  </div>
                )}
                {/* Documents */}
                {documents.length > 0 && (
                <Table>
                  <TableHeader>
                    <TableRow className="h-10 bg-secondary">
                      <TableHead className="w-10 px-3">
                        <Checkbox
                          checked={
                            documents.length > 0 &&
                            documents.every((d) => selectedDocIds.has(d.id))
                          }
                          onCheckedChange={(checked) => {
                            if (checked) {
                              setSelectedDocIds(new Set(documents.map((d) => d.id)));
                            } else {
                              setSelectedDocIds(new Set());
                            }
                          }}
                        />
                      </TableHead>
                      <TableHead className="w-10" />
                      <TableHead>Title</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Lifecycle</TableHead>
                      <TableHead>Modified</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {documents.map((doc) => (
                      <TableRow
                        key={doc.id}
                        className={`cursor-pointer hover:bg-accent/50 ${
                          doc.id === selectedDocumentId
                            ? "bg-accent border-l-[3px] border-primary"
                            : ""
                        }`}
                        onClick={() => setSelectedDocumentId(doc.id)}
                      >
                        <TableCell className="w-10 px-3" onClick={(e) => e.stopPropagation()}>
                          <Checkbox
                            checked={selectedDocIds.has(doc.id)}
                            onCheckedChange={(checked) => {
                              setSelectedDocIds((prev) => {
                                const next = new Set(prev);
                                if (checked) {
                                  next.add(doc.id);
                                } else {
                                  next.delete(doc.id);
                                }
                                return next;
                              });
                            }}
                          />
                        </TableCell>
                        <TableCell className="w-10 px-3">
                          <FileTypeIcon contentType={doc.content_type} />
                        </TableCell>
                        <TableCell>
                          <span className="text-sm font-medium">
                            {doc.title}
                          </span>
                        </TableCell>
                        <TableCell>
                          {doc.document_type_name ? (
                            <Badge variant="outline" className="text-xs">
                              {doc.document_type_name}
                            </Badge>
                          ) : (
                            <span className="text-xs text-muted-foreground">
                              --
                            </span>
                          )}
                        </TableCell>
                        <TableCell>
                          <LifecycleStateBadge state={doc.lifecycle_state} />
                        </TableCell>
                        <TableCell>
                          <span className="text-xs text-muted-foreground">
                            {formatDate(doc.updated_at)}
                          </span>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
                )}
              </div>

              {/* Pagination */}
              <div className="h-12 flex items-center justify-between px-4 border-t shrink-0">
                <span className="text-sm text-muted-foreground">
                  Page {currentPage} of {totalPages}
                </span>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={currentPage === 1}
                    onClick={() => {
                      setCurrentPage((p) => p - 1);
                      setSelectedDocumentId(null);
                    }}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={currentPage >= totalPages}
                    onClick={() => {
                      setCurrentPage((p) => p + 1);
                      setSelectedDocumentId(null);
                    }}
                  >
                    Next
                  </Button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right: Document detail panel */}
        {selectedDocumentId && (
          <div className="w-[420px] border-l overflow-y-auto shrink-0">
            <DocumentDetailPanel
              documentId={selectedDocumentId}
              currentUserId={userId}
              onDocumentSelect={setSelectedDocumentId}
            />
          </div>
        )}
      </div>

      {/* Bulk job progress dialog */}
      <BulkJobDialog
        jobId={activeJobId}
        open={!!activeJobId}
        onClose={() => setActiveJobId(null)}
      />

      {/* Export dialog */}
      <ExportDialog
        open={exportOpen}
        onOpenChange={setExportOpen}
        selectedDocumentIds={Array.from(selectedDocIds)}
        selectedFolderIds={selectedFolderId ? [selectedFolderId] : []}
      />
    </div>
  );
}
