import { useQuery } from "@tanstack/react-query";
import { fetchFolderTree, type FolderTreeNode } from "../../api/folders";
import { fetchDocumentTypes } from "../../api/documentTypes";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import { Button } from "../ui/button";

export interface SearchFilterValues {
  folder_id?: string;
  document_type_id?: string;
  lifecycle_state?: string;
}

interface SearchFiltersProps {
  filters: SearchFilterValues;
  onFiltersChange: (filters: SearchFilterValues) => void;
}

const LIFECYCLE_STATES = [
  { value: "draft", label: "Draft" },
  { value: "active", label: "Active" },
  { value: "approved", label: "Approved" },
  { value: "obsolete", label: "Obsolete" },
  { value: "archived", label: "Archived" },
];

/** Flatten a folder tree into a flat list with indentation hints. */
function flattenTree(
  nodes: FolderTreeNode[],
  depth = 0,
): { id: string; name: string; depth: number }[] {
  const result: { id: string; name: string; depth: number }[] = [];
  for (const node of nodes) {
    result.push({ id: node.id, name: node.name, depth });
    if (node.children?.length) {
      result.push(...flattenTree(node.children, depth + 1));
    }
  }
  return result;
}

export function SearchFilters({ filters, onFiltersChange }: SearchFiltersProps) {
  const { data: folderTree } = useQuery({
    queryKey: ["folders", "tree"],
    queryFn: fetchFolderTree,
    staleTime: 60_000,
  });

  const { data: documentTypes } = useQuery({
    queryKey: ["document-types"],
    queryFn: fetchDocumentTypes,
    staleTime: 60_000,
  });

  const flatFolders = folderTree ? flattenTree(folderTree) : [];

  function updateFilter(key: keyof SearchFilterValues, value: string | undefined) {
    onFiltersChange({ ...filters, [key]: value });
  }

  const hasAnyFilter = filters.folder_id || filters.document_type_id || filters.lifecycle_state;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Filters</h3>
        {hasAnyFilter && (
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs"
            onClick={() => onFiltersChange({})}
          >
            Clear all
          </Button>
        )}
      </div>

      {/* Folder filter */}
      <div className="space-y-1.5">
        <label className="text-xs font-medium text-muted-foreground">
          Folder
        </label>
        <Select
          value={filters.folder_id ?? "__all__"}
          onValueChange={(v) => updateFilter("folder_id", v === "__all__" ? undefined : v)}
        >
          <SelectTrigger className="w-full">
            <SelectValue placeholder="All folders" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__all__">All folders</SelectItem>
            {flatFolders.map((folder) => (
              <SelectItem key={folder.id} value={folder.id}>
                <span style={{ paddingLeft: `${folder.depth * 12}px` }}>
                  {folder.name}
                </span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Document type filter */}
      <div className="space-y-1.5">
        <label className="text-xs font-medium text-muted-foreground">
          Document Type
        </label>
        <Select
          value={filters.document_type_id ?? "__all__"}
          onValueChange={(v) =>
            updateFilter("document_type_id", v === "__all__" ? undefined : v)
          }
        >
          <SelectTrigger className="w-full">
            <SelectValue placeholder="All types" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__all__">All types</SelectItem>
            {documentTypes?.map((dt) => (
              <SelectItem key={dt.id} value={dt.id}>
                {dt.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Lifecycle state filter */}
      <div className="space-y-1.5">
        <label className="text-xs font-medium text-muted-foreground">
          Lifecycle State
        </label>
        <Select
          value={filters.lifecycle_state ?? "__all__"}
          onValueChange={(v) =>
            updateFilter("lifecycle_state", v === "__all__" ? undefined : v)
          }
        >
          <SelectTrigger className="w-full">
            <SelectValue placeholder="All states" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__all__">All states</SelectItem>
            {LIFECYCLE_STATES.map((state) => (
              <SelectItem key={state.value} value={state.value}>
                {state.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}
