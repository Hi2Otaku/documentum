import { useState, useEffect, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { BookmarkPlus } from "lucide-react";
import { SearchInput } from "../components/search/SearchInput";
import { SearchResults } from "../components/search/SearchResults";
import { SearchFilters, type SearchFilterValues } from "../components/search/SearchFilters";
import { SaveSearchDialog } from "../components/search/SaveSearchDialog";
import { SavedSearchesList } from "../components/search/SavedSearchesList";
import { searchDocuments } from "../api/search";
import { Button } from "../components/ui/button";

const PAGE_SIZE = 20;

export function SearchPage() {
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [filters, setFilters] = useState<SearchFilterValues>({});
  const [page, setPage] = useState(1);
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);

  // Debounce query
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(query), 300);
    return () => clearTimeout(timer);
  }, [query]);

  // Reset page when query or filters change
  useEffect(() => {
    setPage(1);
  }, [debouncedQuery, filters]);

  const { data, isLoading } = useQuery({
    queryKey: ["search", debouncedQuery, filters, page],
    queryFn: () =>
      searchDocuments({
        q: debouncedQuery,
        folder_id: filters.folder_id,
        document_type_id: filters.document_type_id,
        lifecycle_state: filters.lifecycle_state,
        page,
        page_size: PAGE_SIZE,
      }),
    enabled: debouncedQuery.length >= 1,
  });

  const totalPages = data?.meta?.total_pages ?? 1;
  const totalCount = data?.meta?.total_count ?? 0;

  const handleFiltersChange = useCallback((newFilters: SearchFilterValues) => {
    setFilters(newFilters);
  }, []);

  const handleLoadSearch = useCallback(
    (savedQuery: string, savedFilters: SearchFilterValues) => {
      setQuery(savedQuery);
      setFilters(savedFilters);
    },
    [],
  );

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Search Documents</h1>

      <div className="flex items-center gap-2">
        <div className="flex-1">
          <SearchInput value={query} onChange={setQuery} />
        </div>
        <Button
          variant="outline"
          size="sm"
          className="shrink-0"
          disabled={!query.trim()}
          onClick={() => setSaveDialogOpen(true)}
          title="Save this search"
        >
          <BookmarkPlus className="h-4 w-4 mr-1.5" />
          Save Search
        </Button>
      </div>

      <div className="mt-6 flex gap-6">
        <aside className="w-64 shrink-0 space-y-6">
          <SearchFilters filters={filters} onFiltersChange={handleFiltersChange} />
          <SavedSearchesList onLoadSearch={handleLoadSearch} />
        </aside>
        <main className="flex-1 min-w-0">
          {/* Result count */}
          {debouncedQuery && data && (
            <p className="text-sm text-muted-foreground mb-3">
              {totalCount} result{totalCount !== 1 ? "s" : ""} found
            </p>
          )}

          <SearchResults
            results={data?.data ?? []}
            isLoading={isLoading && debouncedQuery.length >= 1}
            query={debouncedQuery}
          />

          {/* Pagination */}
          {data && totalPages > 1 && (
            <div className="mt-6 flex items-center justify-between">
              <span className="text-sm text-muted-foreground">
                Page {page} of {totalPages}
              </span>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page === 1}
                  onClick={() => setPage((p) => p - 1)}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </main>
      </div>

      <SaveSearchDialog
        open={saveDialogOpen}
        onOpenChange={setSaveDialogOpen}
        query={query}
        filters={filters}
        onSaved={() => {}}
      />
    </div>
  );
}
