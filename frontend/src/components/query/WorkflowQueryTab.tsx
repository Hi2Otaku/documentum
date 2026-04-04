import { useState, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import {
  queryWorkflows,
  fetchTemplatesForFilter,
  fetchUsersForFilter,
  getStateBadgeClass,
  type WorkflowQueryResponse,
  type WorkflowQueryParams,
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

const WORKFLOW_STATES = [
  { value: "", label: "All States" },
  { value: "RUNNING", label: "Running" },
  { value: "HALTED", label: "Halted" },
  { value: "FINISHED", label: "Finished" },
  { value: "FAILED", label: "Failed" },
  { value: "DORMANT", label: "Dormant" },
];

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "---";
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const columns: ColumnDef<WorkflowQueryResponse, unknown>[] = [
  {
    accessorKey: "template_name",
    header: "Name",
    cell: ({ row }) => (
      <span className="font-medium">
        {row.original.template_name}{" "}
        <span className="text-muted-foreground text-xs">
          #{row.original.id.slice(0, 8)}
        </span>
      </span>
    ),
  },
  {
    id: "template",
    header: "Template",
    accessorFn: (row) => row.template_name,
    cell: ({ row }) => (
      <span>
        {row.original.template_name}{" "}
        <span className="text-muted-foreground">
          v{row.original.template_version}
        </span>
      </span>
    ),
    size: 180,
  },
  {
    accessorKey: "state",
    header: "State",
    cell: ({ row }) => (
      <Badge
        variant="secondary"
        className={getStateBadgeClass(row.original.state)}
        aria-label={`State: ${row.original.state}`}
      >
        {row.original.state}
      </Badge>
    ),
    size: 100,
  },
  {
    accessorKey: "started_by",
    header: "Started By",
    cell: ({ row }) => row.original.started_by || "---",
    size: 140,
  },
  {
    accessorKey: "started_at",
    header: "Started At",
    cell: ({ row }) => formatDate(row.original.started_at),
    size: 160,
  },
  {
    accessorKey: "active_activity",
    header: "Active Activity",
    cell: ({ row }) => row.original.active_activity || "---",
    size: 160,
  },
];

export function WorkflowQueryTab() {
  // Filter state
  const [templateId, setTemplateId] = useState("");
  const [state, setState] = useState("");
  const [startedBy, setStartedBy] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [skip, setSkip] = useState(0);
  const [searchTriggered, setSearchTriggered] = useState(false);
  const [activeFilters, setActiveFilters] = useState<WorkflowQueryParams>({});

  // Fetch templates and users for filter dropdowns
  const { data: templates } = useQuery({
    queryKey: ["templates"],
    queryFn: fetchTemplatesForFilter,
    staleTime: 30_000,
  });

  const { data: users } = useQuery({
    queryKey: ["users"],
    queryFn: fetchUsersForFilter,
    staleTime: 300_000,
  });

  // Build params from active filters
  const queryParams: WorkflowQueryParams = {
    ...activeFilters,
    skip,
    limit: PAGE_SIZE,
  };

  const { data, isLoading } = useQuery({
    queryKey: ["query", "workflows", queryParams],
    queryFn: () => queryWorkflows(queryParams),
    enabled: searchTriggered,
  });

  const handleSearch = useCallback(() => {
    const filters: WorkflowQueryParams = {};
    if (templateId) filters.template_id = templateId;
    if (state) filters.state = state;
    if (startedBy) filters.started_by = startedBy;
    if (dateFrom) filters.date_from = dateFrom;
    if (dateTo) filters.date_to = dateTo;
    setActiveFilters(filters);
    setSkip(0);
    setSearchTriggered(true);
  }, [templateId, state, startedBy, dateFrom, dateTo]);

  const handleClear = useCallback(() => {
    setTemplateId("");
    setState("");
    setStartedBy("");
    setDateFrom("");
    setDateTo("");
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
          <Label htmlFor="wf-template">Template</Label>
          <Select value={templateId} onValueChange={setTemplateId}>
            <SelectTrigger id="wf-template" className="w-[180px]">
              <SelectValue placeholder="All Templates" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">All Templates</SelectItem>
              {templates?.map((t) => (
                <SelectItem key={t.id} value={t.id}>
                  {t.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="wf-state">State</Label>
          <Select value={state} onValueChange={setState}>
            <SelectTrigger id="wf-state" className="w-[140px]">
              <SelectValue placeholder="All States" />
            </SelectTrigger>
            <SelectContent>
              {WORKFLOW_STATES.map((s) => (
                <SelectItem key={s.value} value={s.value}>
                  {s.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="wf-started-by">Started By</Label>
          <Select value={startedBy} onValueChange={setStartedBy}>
            <SelectTrigger id="wf-started-by" className="w-[160px]">
              <SelectValue placeholder="All Users" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">All Users</SelectItem>
              {users?.map((u) => (
                <SelectItem key={u.id} value={u.id}>
                  {u.username}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="wf-date-from">Date From</Label>
          <Input
            id="wf-date-from"
            type="date"
            className="w-[160px]"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="wf-date-to">Date To</Label>
          <Input
            id="wf-date-to"
            type="date"
            className="w-[160px]"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
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
        emptyMessage="No workflows found"
        emptyDescription="No workflow instances match your filters. Try adjusting the search criteria."
      />
    </div>
  );
}
