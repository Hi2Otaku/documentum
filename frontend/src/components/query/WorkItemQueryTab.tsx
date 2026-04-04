import { useState, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import {
  queryWorkItems,
  fetchUsersForFilter,
  getStateBadgeClass,
  type WorkItemQueryResponse,
  type WorkItemQueryParams,
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

const WORK_ITEM_STATES = [
  { value: "", label: "All States" },
  { value: "AVAILABLE", label: "Available" },
  { value: "ACQUIRED", label: "Acquired" },
  { value: "COMPLETED", label: "Completed" },
  { value: "REJECTED", label: "Rejected" },
  { value: "SUSPENDED", label: "Suspended" },
];

const PRIORITY_OPTIONS = [
  { value: "", label: "All Priorities" },
  { value: "1", label: "Low" },
  { value: "3", label: "Normal" },
  { value: "5", label: "High" },
  { value: "9", label: "Urgent" },
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

function getPriorityLabel(priority: number): string {
  if (priority >= 9) return "Urgent";
  if (priority >= 5) return "High";
  if (priority >= 3) return "Normal";
  return "Low";
}

function getPriorityBadgeClass(priority: number): string {
  if (priority >= 9) return "bg-red-100 text-red-700";
  if (priority >= 5) return "bg-amber-100 text-amber-700";
  if (priority >= 3) return "bg-blue-100 text-blue-700";
  return "bg-gray-100 text-gray-700";
}

const columns: ColumnDef<WorkItemQueryResponse, unknown>[] = [
  {
    accessorKey: "activity_name",
    header: "Activity",
    cell: ({ row }) => (
      <span className="font-medium">{row.original.activity_name}</span>
    ),
  },
  {
    accessorKey: "workflow_name",
    header: "Workflow",
    cell: ({ row }) => (
      <span className="truncate max-w-[180px] inline-block">
        {row.original.workflow_name}
      </span>
    ),
    size: 180,
  },
  {
    accessorKey: "assignee",
    header: "Assignee",
    cell: ({ row }) => row.original.assignee || "---",
    size: 140,
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
    accessorKey: "priority",
    header: "Priority",
    cell: ({ row }) => (
      <Badge
        variant="secondary"
        className={getPriorityBadgeClass(row.original.priority)}
      >
        {getPriorityLabel(row.original.priority)}
      </Badge>
    ),
    size: 80,
  },
  {
    accessorKey: "created_at",
    header: "Created At",
    cell: ({ row }) => formatDate(row.original.created_at),
    size: 160,
  },
];

export function WorkItemQueryTab() {
  const [assigneeId, setAssigneeId] = useState("");
  const [state, setState] = useState("");
  const [workflowId, setWorkflowId] = useState("");
  const [priority, setPriority] = useState("");
  const [skip, setSkip] = useState(0);
  const [searchTriggered, setSearchTriggered] = useState(false);
  const [activeFilters, setActiveFilters] = useState<WorkItemQueryParams>({});

  const { data: users } = useQuery({
    queryKey: ["users"],
    queryFn: fetchUsersForFilter,
    staleTime: 300_000,
  });

  const queryParams: WorkItemQueryParams = {
    ...activeFilters,
    skip,
    limit: PAGE_SIZE,
  };

  const { data, isLoading } = useQuery({
    queryKey: ["query", "work-items", queryParams],
    queryFn: () => queryWorkItems(queryParams),
    enabled: searchTriggered,
  });

  const handleSearch = useCallback(() => {
    const filters: WorkItemQueryParams = {};
    if (assigneeId) filters.assignee_id = assigneeId;
    if (state) filters.state = state;
    if (workflowId) filters.workflow_id = workflowId;
    if (priority) filters.priority = Number(priority);
    setActiveFilters(filters);
    setSkip(0);
    setSearchTriggered(true);
  }, [assigneeId, state, workflowId, priority]);

  const handleClear = useCallback(() => {
    setAssigneeId("");
    setState("");
    setWorkflowId("");
    setPriority("");
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
          <Label htmlFor="wi-assignee">Assignee</Label>
          <Select value={assigneeId} onValueChange={setAssigneeId}>
            <SelectTrigger id="wi-assignee" className="w-[160px]">
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
          <Label htmlFor="wi-state">State</Label>
          <Select value={state} onValueChange={setState}>
            <SelectTrigger id="wi-state" className="w-[140px]">
              <SelectValue placeholder="All States" />
            </SelectTrigger>
            <SelectContent>
              {WORK_ITEM_STATES.map((s) => (
                <SelectItem key={s.value} value={s.value}>
                  {s.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="wi-workflow">Workflow ID</Label>
          <Input
            id="wi-workflow"
            type="text"
            placeholder="UUID"
            className="w-[220px]"
            value={workflowId}
            onChange={(e) => setWorkflowId(e.target.value)}
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="wi-priority">Priority</Label>
          <Select value={priority} onValueChange={setPriority}>
            <SelectTrigger id="wi-priority" className="w-[140px]">
              <SelectValue placeholder="All Priorities" />
            </SelectTrigger>
            <SelectContent>
              {PRIORITY_OPTIONS.map((p) => (
                <SelectItem key={p.value} value={p.value}>
                  {p.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
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
        emptyMessage="No work items found"
        emptyDescription="No work items match your filters. Try widening the date range or changing filters."
      />
    </div>
  );
}
