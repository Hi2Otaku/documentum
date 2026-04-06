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
import { WorkItemStateBadge } from "./WorkItemStateBadge";
import { PriorityIcon } from "./PriorityIcon";
import { InboxEmptyState } from "./InboxEmptyState";
import type { InboxItemResponse } from "../../api/inbox";

interface InboxTableProps {
  items: InboxItemResponse[];
  isLoading: boolean;
  selectedId: string | null;
  onSelectItem: (id: string) => void;
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  stateFilter: string;
  onStateFilterChange: (state: string) => void;
}

const columnHelper = createColumnHelper<InboxItemResponse>();

const columns = [
  columnHelper.accessor((row) => row.activity.name, {
    id: "task",
    header: "Task",
    cell: (info) => (
      <span className="text-sm font-semibold">{info.getValue()}</span>
    ),
  }),
  columnHelper.accessor((row) => row.workflow.template_name, {
    id: "workflow",
    header: "Workflow",
    cell: (info) => (
      <span className="text-sm truncate block max-w-[200px]" title={info.getValue()}>
        {info.getValue()}
      </span>
    ),
    size: 200,
  }),
  columnHelper.accessor("priority", {
    header: "Priority",
    cell: (info) => (
      <div className="flex justify-center">
        <PriorityIcon priority={info.getValue()} />
      </div>
    ),
    size: 60,
  }),
  columnHelper.accessor("state", {
    header: "State",
    cell: (info) => <WorkItemStateBadge state={info.getValue()} />,
    size: 100,
  }),
  columnHelper.accessor("created_at", {
    header: "Created",
    cell: (info) => (
      <span className="text-xs text-muted-foreground">
        {new Date(info.getValue()).toLocaleDateString()}
      </span>
    ),
    size: 100,
  }),
];

export function InboxTable({
  items,
  isLoading,
  selectedId,
  onSelectItem,
  currentPage,
  totalPages,
  onPageChange,
  stateFilter,
  onStateFilterChange,
}: InboxTableProps) {
  const table = useReactTable({
    data: items,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <div className="flex flex-col h-full">
      {/* Filter bar */}
      <div className="h-12 flex items-center gap-2 px-4 bg-secondary/50 shrink-0">
        <span className="text-xs text-muted-foreground">State</span>
        <Select value={stateFilter} onValueChange={onStateFilterChange}>
          <SelectTrigger className="w-[140px] h-8">
            <SelectValue placeholder="All" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All</SelectItem>
            <SelectItem value="available">Available</SelectItem>
            <SelectItem value="acquired">Acquired</SelectItem>
            <SelectItem value="delegated">Delegated</SelectItem>
          </SelectContent>
        </Select>
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
        ) : items.length === 0 ? (
          <InboxEmptyState
            heading="No work items"
            body="You have no pending tasks. New items will appear here when workflows assign work to you."
          />
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
                  onClick={() => onSelectItem(row.original.id)}
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
