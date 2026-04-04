import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import { listTemplates, createTemplate, deleteTemplate } from "../api/templates";
import type { ProcessTemplate } from "../types/workflow";
import { toast } from "sonner";
import { MoreVertical } from "lucide-react";
import { Button } from "../components/ui/button";
import { Card, CardContent } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Skeleton } from "../components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "../components/ui/dropdown-menu";

export function TemplateListPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [deleteTarget, setDeleteTarget] = useState<ProcessTemplate | null>(null);

  const {
    data: templates,
    isLoading,
    error,
    refetch,
  } = useQuery<ProcessTemplate[]>({
    queryKey: ["templates"],
    queryFn: listTemplates,
  });

  const createMutation = useMutation({
    mutationFn: () => createTemplate({ name: "Untitled Template" }),
    onSuccess: (template) => {
      queryClient.invalidateQueries({ queryKey: ["templates"] });
      navigate(`/templates/${template.id}/edit`);
    },
    onError: () => {
      toast.error("Failed to create template.");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteTemplate(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["templates"] });
      toast.success("Template deleted");
      setDeleteTarget(null);
    },
    onError: () => {
      toast.error("Failed to delete template.");
      setDeleteTarget(null);
    },
  });

  return (
    <div className="p-8 max-w-4xl mx-auto">
      {/* Page header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold">Workflow Templates</h1>
        <Button
          onClick={() => createMutation.mutate()}
          disabled={createMutation.isPending}
        >
          {createMutation.isPending ? "Creating..." : "New Template"}
        </Button>
      </div>

      {/* Loading state: 3 skeleton cards */}
      {isLoading && (
        <div className="flex flex-col gap-4">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="p-6">
              <Skeleton className="h-5 w-[40%] mb-3" />
              <Skeleton className="h-4 w-[70%] mb-3" />
              <Skeleton className="h-3 w-[30%]" />
            </Card>
          ))}
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="text-center py-12">
          <p className="text-destructive mb-4">
            Error loading templates. Make sure the backend is running.
          </p>
          <Button variant="outline" onClick={() => refetch()}>
            Retry
          </Button>
        </div>
      )}

      {/* Empty state */}
      {templates && templates.length === 0 && (
        <div className="text-center py-12">
          <h2 className="text-lg font-semibold mb-2">No workflow templates</h2>
          <p className="text-muted-foreground mb-4">
            Create your first workflow template to get started.
          </p>
          <Button onClick={() => createMutation.mutate()}>
            New Template
          </Button>
        </div>
      )}

      {/* Template grid */}
      {templates && templates.length > 0 && (
        <div className="flex flex-col gap-4">
          {templates.map((t) => (
            <Card
              key={t.id}
              className="cursor-pointer hover:shadow-md transition-shadow"
              onClick={() => navigate(`/templates/${t.id}/edit`)}
            >
              <CardContent className="p-6 flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-1">
                    <span className="font-semibold truncate">{t.name}</span>
                    <Badge
                      variant={t.state === "active" ? "default" : "secondary"}
                      className={
                        t.state === "active"
                          ? "bg-green-600 hover:bg-green-600"
                          : ""
                      }
                    >
                      {t.state === "active" ? "Active" : "Draft"}
                    </Badge>
                  </div>
                  <div className="text-sm text-muted-foreground flex items-center gap-4">
                    <span>v{t.version}</span>
                    <span>
                      {new Date(t.updated_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>

                {/* Overflow menu */}
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="shrink-0"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <MoreVertical className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem
                      className="text-destructive focus:text-destructive"
                      onClick={(e) => {
                        e.stopPropagation();
                        setDeleteTarget(t);
                      }}
                    >
                      Delete
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Delete confirmation dialog */}
      <Dialog
        open={!!deleteTarget}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete template &apos;{deleteTarget?.name}&apos;?</DialogTitle>
            <DialogDescription>
              This cannot be undone. Running workflow instances will not be
              affected.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              disabled={deleteMutation.isPending}
              onClick={() => {
                if (deleteTarget) {
                  deleteMutation.mutate(deleteTarget.id);
                }
              }}
            >
              {deleteMutation.isPending ? "Deleting..." : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
