import { useState, useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { DocumentDropZone } from "../components/documents/DocumentDropZone";
import { DocumentTable } from "../components/documents/DocumentTable";
import { DocumentDetailPanel } from "../components/documents/DocumentDetailPanel";
import { fetchDocuments } from "../api/documents";
import { useAuthStore } from "../stores/authStore";

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

  const documents = data?.data ?? [];
  const totalPages = data?.meta?.total_pages ?? 1;

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
      {/* Drop zone */}
      <DocumentDropZone onUploadComplete={handleUploadComplete} />

      {/* Split pane */}
      <div className="flex h-[calc(100vh-theme(spacing.16)-136px)]">
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
    </div>
  );
}
