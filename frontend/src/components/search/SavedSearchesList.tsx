import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Search, Trash2, FolderSearch } from "lucide-react";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import {
  fetchSavedSearches,
  deleteSavedSearch,
  savedSearchKeys,
} from "../../api/savedSearches";
import type { SearchFilterValues } from "./SearchFilters";

interface SavedSearchesListProps {
  onLoadSearch: (query: string, filters: SearchFilterValues) => void;
}

export function SavedSearchesList({ onLoadSearch }: SavedSearchesListProps) {
  const queryClient = useQueryClient();

  const { data: savedSearches = [], isLoading } = useQuery({
    queryKey: savedSearchKeys.list(),
    queryFn: fetchSavedSearches,
  });

  const deleteMutation = useMutation({
    mutationFn: deleteSavedSearch,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: savedSearchKeys.all });
    },
  });

  if (isLoading) {
    return (
      <div className="space-y-2">
        <h3 className="text-sm font-semibold">Saved Searches</h3>
        <p className="text-xs text-muted-foreground">Loading...</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold">Saved Searches</h3>

      {savedSearches.length === 0 ? (
        <p className="text-xs text-muted-foreground py-2">
          No saved searches yet
        </p>
      ) : (
        <div className="space-y-1">
          {savedSearches.map((search) => (
            <div
              key={search.id}
              className="group flex items-center gap-2 rounded p-2 hover:bg-accent text-sm"
            >
              <Search className="h-3.5 w-3.5 text-muted-foreground shrink-0" />

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="font-medium truncate">{search.name}</span>
                  {search.is_smart_folder && (
                    <Badge
                      variant="secondary"
                      className="text-[10px] px-1 py-0 h-4 shrink-0"
                    >
                      <FolderSearch className="h-2.5 w-2.5 mr-0.5" />
                      Smart
                    </Badge>
                  )}
                </div>
                {search.query && (
                  <p className="text-xs text-muted-foreground truncate">
                    {search.query}
                  </p>
                )}
              </div>

              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 opacity-0 group-hover:opacity-100 shrink-0"
                onClick={() => onLoadSearch(search.query, search.filters)}
                title="Load this search"
              >
                <Search className="h-3.5 w-3.5" />
              </Button>

              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 opacity-0 group-hover:opacity-100 shrink-0 text-destructive hover:text-destructive"
                onClick={() => deleteMutation.mutate(search.id)}
                disabled={deleteMutation.isPending}
                title="Delete this search"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
