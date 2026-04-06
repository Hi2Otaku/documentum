import { useMemo } from "react";
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
import { Input } from "../ui/input";
import { Skeleton } from "../ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import { LifecycleStateBadge } from "./LifecycleStateBadge";
import { LockIndicator } from "./LockIndicator";
import { DocumentEmptyState } from "./DocumentEmptyState";
import type { DocumentResponse } from "../../api/documents";

interface DocumentTableProps {
  documents: DocumentResponse[];
  isLoading: boolean;
  selectedId: string | null;
  onSelectDocument: (id: string) => void;
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  titleFilter: string;
  onTitleFilterChange: (v: string) => void;
  authorFilter: string;
  onAuthorFilterChange: (v: string) => void;
  stateFilter: string;
  onStateFilterChange: (v: string) => void;
  currentUserId: string;
}

function formatRelativeDate(dateStr: string): string {
  const date = new Date(dateStr);
  const now = Date.now();
  const diffMs = now - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffSec < 60) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHour < 24) return `${diffHour}h ago`;
  if (diffDay < 30) return `${diffDay}d ago`;
  return date.toLocaleDateString();
}

const columnHelper = createColumnHelper<DocumentResponse>();

export function DocumentTable({
  documents,
  isLoading,
  selectedId,
  onSelectDocument,
  currentPage,
  totalPages,
  onPageChange,
  titleFilter,
  onTitleFilterChange,
  authorFilter,
  onAuthorFilterChange,
  stateFilter,
  onStateFilterChange,
  currentUserId,
}: DocumentTableProps) {
  const columns = useMemo(
    () => [
      columnHelper.accessor("title", {
        header: "Title",
        cell: (info) => (
          <div className="flex flex-col" style={{ minWidth: 180 }}>
            <span className="text-sm font-semibold">{info.getValue()}</span>
            <span className="text-xs text-muted-foreground">
              {info.row.original.filename}
            </span>
          </div>
        ),
        size: 300,
      }),
      columnHelper.accessor("author", {
        header: "Author",
        cell: (info) => (
          <span className="text-sm" style={{ minWidth: 100 }}>
            {info.getValue() ?? "-"}
          </span>
        ),
        size: 150,
      }),
      columnHelper.accessor("lifecycle_state", {
        header: "State",
        cell: (info) => <LifecycleStateBadge state={info.getValue()} />,
        size: 100,
      }),
      columnHelper.accessor("current_version", {
        header: "Version",
        cell: (info) => <span className="text-sm">{info.getValue()}</span>,
        size: 80,
      }),
      columnHelper.accessor("locked_by", {
        header: "Lock",
        cell: (info) => (
          <LockIndicator
            lockedBy={info.getValue()}
            currentUserId={currentUserId}
            compact
          />
        ),
        size: 40,
      }),
      columnHelper.accessor("updated_at", {
        header: "Updated",
        cell: (info) => (
          <span className="text-xs text-muted-foreground">
            {formatRelativeDate(info.getValue())}
          </span>
        ),
        size: 120,
      }),
    ],
    [currentUserId]
  );

  // Client-side state filter
  const filteredDocuments = useMemo(() => {
    if (stateFilter === "all") return documents;
    return documents.filter(
      (doc) =>
        (doc.lifecycle_state ?? "draft").toLowerCase() ===
        stateFilter.toLowerCase()
    );
  }, [documents, stateFilter]);

  const table = useReactTable({
    data: filteredDocuments,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <div className="flex flex-col h-full">
      {/* Filter bar */}
      <div className="h-12 flex items-center gap-3 px-4 bg-secondary/50 shrink-0">
        <Input
          placeholder="Search by title..."
          value={titleFilter}
          onChange={(e) => onTitleFilterChange(e.target.value)}
          className="h-8 w-[180px]"
        />
        <Input
          placeholder="Filter by author..."
          value={authorFilter}
          onChange={(e) => onAuthorFilterChange(e.target.value)}
          className="h-8 w-[160px]"
        />
        <Select value={stateFilter} onValueChange={onStateFilterChange}>
          <SelectTrigger className="w-[130px] h-8">
            <SelectValue placeholder="All" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All</SelectItem>
            <SelectItem value="draft">Draft</SelectItem>
            <SelectItem value="review">Review</SelectItem>
            <SelectItem value="approved">Approved</SelectItem>
            <SelectItem value="archived">Archived</SelectItem>
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
        ) : filteredDocuments.length === 0 ? (
          <DocumentEmptyState />
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
                            header.getContext()
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
                  onClick={() => onSelectDocument(row.original.id)}
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext()
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
