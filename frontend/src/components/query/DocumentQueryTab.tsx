import { useState, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import {
  queryDocuments,
  getStateBadgeClass,
  type DocumentQueryResponse,
  type DocumentQueryParams,
} from "../../api/query";
import { QueryResultTable } from "./QueryResultTable";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";

const PAGE_SIZE = 20;

const LIFECYCLE_STATES = [
  { value: "all", label: "All States" },
  { value: "DRAFT", label: "Draft" },
  { value: "REVIEW", label: "Review" },
  { value: "APPROVED", label: "Approved" },
  { value: "ARCHIVED", label: "Archived" },
];

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const columns: ColumnDef<DocumentQueryResponse, unknown>[] = [
  {
    accessorKey: "title",
    header: "Title",
    cell: ({ row }) => (
      <span className="font-medium">{row.original.title}</span>
    ),
  },
  {
    accessorKey: "lifecycle_state",
    header: "Lifecycle State",
    cell: ({ row }) =>
      row.original.lifecycle_state ? (
        <Badge
          variant="secondary"
          className={getStateBadgeClass(row.original.lifecycle_state)}
          aria-label={`Lifecycle: ${row.original.lifecycle_state}`}
        >
          {row.original.lifecycle_state}
        </Badge>
      ) : (
        <span className="text-muted-foreground">---</span>
      ),
    size: 120,
  },
  {
    accessorKey: "current_version",
    header: "Version",
    cell: ({ row }) => row.original.current_version || "---",
    size: 80,
  },
  {
    id: "author",
    header: "Author",
    accessorFn: (row) => row.created_by,
    cell: ({ row }) => row.original.created_by || row.original.author || "---",
    size: 140,
  },
  {
    accessorKey: "updated_at",
    header: "Updated At",
    cell: ({ row }) => formatDate(row.original.updated_at),
    size: 160,
  },
];

export function DocumentQueryTab() {
  const [lifecycleState, setLifecycleState] = useState("all");
  const [metadataKey, setMetadataKey] = useState("");
  const [metadataValue, setMetadataValue] = useState("");
  const [version, setVersion] = useState("");
  const [skip, setSkip] = useState(0);
  const [searchTriggered, setSearchTriggered] = useState(false);
  const [activeFilters, setActiveFilters] = useState<DocumentQueryParams>({});

  const queryParams: DocumentQueryParams = {
    ...activeFilters,
    skip,
    limit: PAGE_SIZE,
  };

  const { data, isLoading } = useQuery({
    queryKey: ["query", "documents", queryParams],
    queryFn: () => queryDocuments(queryParams),
    enabled: searchTriggered,
  });

  const handleSearch = useCallback(() => {
    const filters: DocumentQueryParams = {};
    if (lifecycleState && lifecycleState !== "all") filters.lifecycle_state = lifecycleState;
    if (metadataKey) filters.metadata_key = metadataKey;
    if (metadataValue) filters.metadata_value = metadataValue;
    if (version) filters.version = version;
    setActiveFilters(filters);
    setSkip(0);
    setSearchTriggered(true);
  }, [lifecycleState, metadataKey, metadataValue, version]);

  const handleClear = useCallback(() => {
    setLifecycleState("all");
    setMetadataKey("");
    setMetadataValue("");
    setVersion("");
    setSkip(0);
    setActiveFilters({});
    setSearchTriggered(false);
  }, []);

  const handlePageChange = useCallback((newSkip: number) => {
    setSkip(newSkip);
  }, []);

  const pagination = data?.meta
    ? {
        page: Math.floor(data.meta.skip / PAGE_SIZE),
        pageSize: PAGE_SIZE,
        totalCount: data.meta.total,
        totalPages: data.meta.total_pages,
      }
    : undefined;

  return (
    <div className="space-y-4">
      {/* Filter panel */}
      <div className="flex flex-wrap items-end gap-4 p-6 rounded-md border bg-muted/30">
        <div className="space-y-1.5">
          <Label htmlFor="doc-lifecycle">Lifecycle State</Label>
          <Select value={lifecycleState} onValueChange={setLifecycleState}>
            <SelectTrigger id="doc-lifecycle" className="w-[160px]">
              <SelectValue placeholder="All States" />
            </SelectTrigger>
            <SelectContent>
              {LIFECYCLE_STATES.map((s) => (
                <SelectItem key={s.value} value={s.value}>
                  {s.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="doc-meta-key">Metadata Key</Label>
          <Input
            id="doc-meta-key"
            type="text"
            placeholder="e.g. author"
            className="w-[160px]"
            value={metadataKey}
            onChange={(e) => setMetadataKey(e.target.value)}
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="doc-meta-value">Metadata Value</Label>
          <Input
            id="doc-meta-value"
            type="text"
            placeholder="e.g. John"
            className="w-[160px]"
            value={metadataValue}
            onChange={(e) => setMetadataValue(e.target.value)}
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="doc-version">Version</Label>
          <Input
            id="doc-version"
            type="text"
            placeholder="e.g. 1.0"
            className="w-[100px]"
            value={version}
            onChange={(e) => setVersion(e.target.value)}
          />
        </div>

        <div className="flex gap-2 items-end">
          <Button onClick={handleSearch}>Search</Button>
          <Button variant="ghost" onClick={handleClear}>
            Clear Filters
          </Button>
        </div>
      </div>

      {/* Results table */}
      <QueryResultTable
        columns={columns}
        data={data?.data ?? []}
        loading={isLoading && searchTriggered}
        pagination={pagination}
        onPageChange={handlePageChange}
        emptyMessage="No documents found"
        emptyDescription="No documents match your filters. Try different metadata or lifecycle state criteria."
      />
    </div>
  );
}
