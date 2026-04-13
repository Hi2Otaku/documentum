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
import { Skeleton } from "../ui/skeleton";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "../ui/dropdown-menu";
import { MoreHorizontal } from "lucide-react";
import type { DocumentTypeResponse } from "../../api/documentTypes";

interface DocumentTypeTableProps {
  types: DocumentTypeResponse[];
  isLoading: boolean;
  onEdit: (type: DocumentTypeResponse) => void;
}

const columnHelper = createColumnHelper<DocumentTypeResponse>();

export function DocumentTypeTable({
  types,
  isLoading,
  onEdit,
}: DocumentTypeTableProps) {
  const columns = useMemo(
    () => [
      columnHelper.accessor("name", {
        header: "Name",
        cell: (info) => (
          <div className="flex flex-col">
            <span className="text-sm font-semibold">{info.getValue()}</span>
            {info.row.original.description && (
              <span className="text-xs text-muted-foreground truncate max-w-[280px]">
                {info.row.original.description}
              </span>
            )}
          </div>
        ),
        size: 300,
      }),
      columnHelper.accessor("field_count", {
        header: "Fields",
        cell: (info) => <span className="text-sm">{info.getValue()}</span>,
        size: 80,
      }),
      columnHelper.accessor("document_count", {
        header: "Documents",
        cell: (info) => <span className="text-sm">{info.getValue()}</span>,
        size: 100,
      }),
      columnHelper.accessor("parent_type_name", {
        header: "Parent Type",
        cell: (info) => (
          <span className="text-sm">
            {info.getValue() ?? <span className="text-muted-foreground">—</span>}
          </span>
        ),
        size: 150,
      }),
      columnHelper.display({
        id: "actions",
        header: "Actions",
        cell: (info) => (
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                onEdit(info.row.original);
              }}
            >
              Edit
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0"
                  onClick={(e) => e.stopPropagation()}
                >
                  <MoreHorizontal className="h-4 w-4" />
                  <span className="sr-only">Open menu</span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem
                  className="text-destructive focus:text-destructive"
                  onClick={(e) => {
                    e.stopPropagation();
                    onEdit(info.row.original);
                  }}
                >
                  Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        ),
        size: 120,
      }),
    ],
    [onEdit],
  );

  const table = useReactTable({
    data: types,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  if (isLoading) {
    return (
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
    );
  }

  if (types.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <h3 className="text-base font-semibold">No document types</h3>
        <p className="text-sm text-muted-foreground mt-2 max-w-sm">
          Document types define metadata schemas for your documents. Create your
          first type to get started.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-auto">
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
              className="min-h-[48px] hover:bg-accent/50"
            >
              {row.getVisibleCells().map((cell) => (
                <TableCell key={cell.id}>
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
