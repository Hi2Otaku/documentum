import { useState, useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { DocumentDropZone } from "../components/documents/DocumentDropZone";
import { DocumentTable } from "../components/documents/DocumentTable";
import { DocumentDetailPanel } from "../components/documents/DocumentDetailPanel";
import { VirtualDocumentDetailPanel } from "../components/virtual-documents/VirtualDocumentDetailPanel";
import { CreateVirtualDocumentDialog } from "../components/virtual-documents/CreateVirtualDocumentDialog";
import { fetchDocuments } from "../api/documents";
import {
  fetchVirtualDocuments,
  type VirtualDocumentListItem,
} from "../api/virtualDocuments";
import { useAuthStore } from "../stores/authStore";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../components/ui/tabs";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "../components/ui/table";
import { Button } from "../components/ui/button";
import { Skeleton } from "../components/ui/skeleton";

const PAGE_SIZE = 20;

export function DocumentsPage() {
  const queryClient = useQueryClient();
  const userId = useAuthStore((s) => s.userId) ?? "";

  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(
    null
  );
  const [titleFilter, setTitleFilter] = useState("");
  const [authorFilter, setAuthorFilter] = useState("");
  const [stateFilter, setStateFilter] = useState("all");
  const [currentPage, setCurrentPage] = useState(1);

  // Virtual documents state
  const [selectedVirtualDocId, setSelectedVirtualDocId] = useState<
    string | null
  >(null);
  const [vdocPage, setVdocPage] = useState(1);

  // Debounced filter values
  const [debouncedTitle, setDebouncedTitle] = useState("");
  const [debouncedAuthor, setDebouncedAuthor] = useState("");

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedTitle(titleFilter), 300);
    return () => clearTimeout(timer);
  }, [titleFilter]);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedAuthor(authorFilter), 300);
    return () => clearTimeout(timer);
  }, [authorFilter]);

  const { data, isLoading } = useQuery({
    queryKey: [
      "documents",
      {
        page: currentPage,
        title: debouncedTitle || undefined,
        author: debouncedAuthor || undefined,
      },
    ],
    queryFn: () =>
      fetchDocuments({
        page: currentPage,
        page_size: PAGE_SIZE,
        title: debouncedTitle || undefined,
        author: debouncedAuthor || undefined,
      }),
  });

  const { data: vdocData, isLoading: vdocLoading } = useQuery({
    queryKey: ["virtual-documents", { page: vdocPage }],
    queryFn: () => fetchVirtualDocuments({ page: vdocPage, page_size: PAGE_SIZE }),
  });

  const documents = data?.data ?? [];
  const totalPages = data?.meta?.total_pages ?? 1;

  const virtualDocuments = vdocData?.data ?? [];
  const vdocTotalPages = vdocData?.meta?.total_pages ?? 1;

  function handleTitleFilterChange(v: string) {
    setTitleFilter(v);
    setCurrentPage(1);
    setSelectedDocumentId(null);
  }

  function handleAuthorFilterChange(v: string) {
    setAuthorFilter(v);
    setCurrentPage(1);
    setSelectedDocumentId(null);
  }

  function handleStateFilterChange(v: string) {
    setStateFilter(v);
    setCurrentPage(1);
    setSelectedDocumentId(null);
  }

  function handlePageChange(page: number) {
    setCurrentPage(page);
    setSelectedDocumentId(null);
  }

  function handleUploadComplete() {
    queryClient.invalidateQueries({ queryKey: ["documents"] });
  }

  return (
    <div className="h-full flex flex-col px-4 pt-4">
      <Tabs defaultValue="documents" className="flex flex-col h-full">
        <div className="flex items-center justify-between mb-3">
          <TabsList>
            <TabsTrigger value="documents">Documents</TabsTrigger>
            <TabsTrigger value="virtual">Virtual Documents</TabsTrigger>
          </TabsList>
        </div>

        {/* Documents Tab */}
        <TabsContent value="documents" className="flex-1 flex flex-col min-h-0">
          {/* Drop zone */}
          <DocumentDropZone onUploadComplete={handleUploadComplete} />

          {/* Split pane */}
          <div className="flex h-[calc(100vh-theme(spacing.16)-200px)]">
            {/* Left: Document table */}
            <div className="flex-1 min-w-[400px] flex flex-col overflow-hidden">
              <DocumentTable
                documents={documents}
                isLoading={isLoading}
                selectedId={selectedDocumentId}
                onSelectDocument={setSelectedDocumentId}
                currentPage={currentPage}
                totalPages={totalPages}
                onPageChange={handlePageChange}
                titleFilter={titleFilter}
                onTitleFilterChange={handleTitleFilterChange}
                authorFilter={authorFilter}
                onAuthorFilterChange={handleAuthorFilterChange}
                stateFilter={stateFilter}
                onStateFilterChange={handleStateFilterChange}
                currentUserId={userId}
              />
            </div>
            {/* Right: Detail panel */}
            <div className="w-[420px] border-l overflow-y-auto hidden lg:block">
              <DocumentDetailPanel
                documentId={selectedDocumentId}
                currentUserId={userId}
              />
            </div>
          </div>
        </TabsContent>

        {/* Virtual Documents Tab */}
        <TabsContent value="virtual" className="flex-1 flex flex-col min-h-0">
          {/* Toolbar */}
          <div className="flex items-center justify-end mb-3">
            <CreateVirtualDocumentDialog />
          </div>

          {/* Split pane */}
          <div className="flex h-[calc(100vh-theme(spacing.16)-200px)]">
            {/* Left: Virtual document list */}
            <div className="flex-1 min-w-[400px] flex flex-col overflow-hidden">
              <VirtualDocumentTable
                virtualDocuments={virtualDocuments}
                isLoading={vdocLoading}
                selectedId={selectedVirtualDocId}
                onSelect={setSelectedVirtualDocId}
                currentPage={vdocPage}
                totalPages={vdocTotalPages}
                onPageChange={setVdocPage}
              />
            </div>
            {/* Right: Detail panel */}
            <div className="w-[420px] border-l overflow-y-auto hidden lg:block">
              <VirtualDocumentDetailPanel
                virtualDocumentId={selectedVirtualDocId}
              />
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

// --- Internal component for virtual document table ---

interface VirtualDocumentTableProps {
  virtualDocuments: VirtualDocumentListItem[];
  isLoading: boolean;
  selectedId: string | null;
  onSelect: (id: string) => void;
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

function VirtualDocumentTable({
  virtualDocuments,
  isLoading,
  selectedId,
  onSelect,
  currentPage,
  totalPages,
  onPageChange,
}: VirtualDocumentTableProps) {
  if (isLoading) {
    return (
      <div className="p-4 space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    );
  }

  if (virtualDocuments.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center">
        <h3 className="text-lg font-semibold">No virtual documents</h3>
        <p className="text-sm text-muted-foreground mt-1">
          Create a virtual document to assemble multiple documents together.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-auto">
        <Table>
          <TableHeader>
            <TableRow className="h-10 bg-secondary">
              <TableHead>Title</TableHead>
              <TableHead>Children</TableHead>
              <TableHead>Created</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {virtualDocuments.map((vdoc) => (
              <TableRow
                key={vdoc.id}
                className={`min-h-[48px] cursor-pointer hover:bg-accent/50 ${
                  vdoc.id === selectedId
                    ? "bg-accent border-l-[3px] border-primary"
                    : ""
                }`}
                onClick={() => onSelect(vdoc.id)}
              >
                <TableCell>
                  <div className="flex flex-col">
                    <span className="text-sm font-semibold">
                      {vdoc.title ?? "Untitled"}
                    </span>
                    {vdoc.description && (
                      <span className="text-xs text-muted-foreground truncate max-w-[250px]">
                        {vdoc.description}
                      </span>
                    )}
                  </div>
                </TableCell>
                <TableCell>
                  <span className="text-sm">{vdoc.child_count}</span>
                </TableCell>
                <TableCell>
                  <span className="text-xs text-muted-foreground">
                    {new Date(vdoc.created_at).toLocaleDateString()}
                  </span>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      <div className="h-12 flex items-center justify-between px-4 border-t shrink-0">
        <span className="text-sm text-muted-foreground">
          Page {currentPage} of {totalPages || 1}
        </span>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={currentPage === 1}
            onClick={() => onPageChange(currentPage - 1)}
          >
            Previous
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={currentPage >= totalPages}
            onClick={() => onPageChange(currentPage + 1)}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  );
}
