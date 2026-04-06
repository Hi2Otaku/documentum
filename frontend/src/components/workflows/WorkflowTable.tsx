import {
  useReactTable,
  getCoreRowModel,
  createColumnHelper,
  flexRender,
} from "@tanstack/react-table";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "../ui/table";
import { Button } from "../ui/button";
import { Skeleton } from "../ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import { WorkflowStateBadge } from "./WorkflowStateBadge";
import { WorkflowEmptyState } from "./WorkflowEmptyState";
import type {
  WorkflowInstanceResponse,
  WorkflowAdminListResponse,
} from "../../api/workflows";

interface WorkflowTableProps {
  workflows: (WorkflowInstanceResponse | WorkflowAdminListResponse)[];
  isLoading: boolean;
  selectedId: string | null;
  onSelectWorkflow: (id: string) => void;
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  templateFilter: string;
  onTemplateFilterChange: (v: string) => void;
  stateFilter: string;
  onStateFilterChange: (v: string) => void;
  templates: { id: string; name: string }[];
  isSuperuser: boolean;
  currentUserId: string;
}

function isAdminResponse(
  row: WorkflowInstanceResponse | WorkflowAdminListResponse,
): row is WorkflowAdminListResponse {
  return "template_name" in row;
}

export function WorkflowTable({
  workflows,
  isLoading,
  selectedId,
  onSelectWorkflow,
  currentPage,
  totalPages,
  onPageChange,
  templateFilter,
  onTemplateFilterChange,
  stateFilter,
  onStateFilterChange,
  templates,
  isSuperuser,
  currentUserId,
}: WorkflowTableProps) {
  const columnHelper =
    createColumnHelper<WorkflowInstanceResponse | WorkflowAdminListResponse>();

  const columns = [
    columnHelper.accessor(
      (row) =>
        isAdminResponse(row)
          ? (row.template_name ?? row.process_template_id.slice(0, 8))
          : row.process_template_id.slice(0, 8),
      {
        id: "name",
        header: "Name",
        cell: (info) => (
          <span className="text-sm font-semibold">{info.getValue()}</span>
        ),
        size: 180,
        minSize: 180,
      },
    ),
    columnHelper.accessor(
      (row) => (isAdminResponse(row) ? (row.template_name ?? "\u2014") : "\u2014"),
      {
        id: "template",
        header: "Template",
        cell: (info) => (
          <span className="text-sm truncate block max-w-[200px]">
            {info.getValue()}
          </span>
        ),
        size: 120,
        minSize: 120,
      },
    ),
    columnHelper.accessor("state", {
      header: "State",
      cell: (info) => <WorkflowStateBadge state={info.getValue()} />,
      size: 100,
    }),
    columnHelper.accessor(
      (row) =>
        isAdminResponse(row)
          ? (row.started_by_username ??
            (row.supervisor_id === currentUserId
              ? "You"
              : (row.supervisor_id?.slice(0, 8) ?? "\u2014")))
          : row.supervisor_id === currentUserId
            ? "You"
            : (row.supervisor_id?.slice(0, 8) ?? "\u2014"),
      {
        id: "startedBy",
        header: "Started By",
        cell: (info) => <span className="text-sm">{info.getValue()}</span>,
        size: 100,
        minSize: 100,
      },
    ),
    columnHelper.accessor("created_at", {
      header: "Started",
      cell: (info) => (
        <span className="text-xs text-muted-foreground">
          {new Date(info.getValue()).toLocaleDateString()}
        </span>
      ),
      size: 120,
    }),
  ];

  const table = useReactTable({
    data: workflows,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <div className="flex flex-col h-full">
      {/* Filter bar */}
      <div className="h-12 flex items-center justify-end gap-2 px-4 bg-secondary/50 shrink-0">
        {isSuperuser && (
          <>
            <Select value={templateFilter} onValueChange={onTemplateFilterChange}>
              <SelectTrigger className="w-[180px] h-8">
                <SelectValue placeholder="All templates" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All templates</SelectItem>
                {templates.map((t) => (
                  <SelectItem key={t.id} value={t.id}>
                    {t.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={stateFilter} onValueChange={onStateFilterChange}>
              <SelectTrigger className="w-[140px] h-8">
                <SelectValue placeholder="All states" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All states</SelectItem>
                <SelectItem value="running">Running</SelectItem>
                <SelectItem value="halted">Halted</SelectItem>
                <SelectItem value="finished">Finished</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
                <SelectItem value="dormant">Dormant</SelectItem>
              </SelectContent>
            </Select>
          </>
        )}
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto">
        {isLoading ? (
          <Table>
            <TableHeader>
              <TableRow className="h-10 bg-secondary">
                {columns.map((_, i) => (
                  <TableHead key={i}>
                    <Skeleton className="h-4 w-20" />
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {Array.from({ length: 5 }).map((_, rowIdx) => (
                <TableRow key={rowIdx}>
                  <TableCell colSpan={columns.length}>
                    <Skeleton className="h-[48px] w-full" />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : workflows.length === 0 ? (
          <WorkflowEmptyState />
        ) : (
          <Table>
            <TableHeader>
              {table.getHeaderGroups().map((headerGroup) => (
                <TableRow key={headerGroup.id} className="h-10 bg-secondary">
                  {headerGroup.headers.map((header) => (
                    <TableHead key={header.id}>
                      {header.isPlaceholder
                        ? null
                        : flexRender(
                            header.column.columnDef.header,
                            header.getContext(),
                          )}
                    </TableHead>
                  ))}
                </TableRow>
              ))}
            </TableHeader>
            <TableBody>
              {table.getRowModel().rows.map((row) => (
                <TableRow
                  key={row.id}
                  className={`min-h-[48px] cursor-pointer hover:bg-accent/50 ${
                    row.original.id === selectedId
                      ? "bg-accent border-l-[3px] border-primary"
                      : ""
                  }`}
                  onClick={() => onSelectWorkflow(row.original.id)}
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext(),
                      )}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>

      {/* Pagination footer */}
      <div className="h-12 flex items-center justify-center gap-2 px-4 border-t shrink-0">
        <Button
          variant="outline"
          size="sm"
          disabled={currentPage === 1}
          onClick={() => onPageChange(currentPage - 1)}
        >
          Previous
        </Button>
        <span className="text-sm text-muted-foreground">
          Page {currentPage} of {totalPages || 1}
        </span>
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
  );
}
