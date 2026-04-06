import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "../ui/dialog";
import { fetchDocuments } from "../../api/documents";
import { addChild } from "../../api/virtualDocuments";

interface AddChildDialogProps {
  virtualDocId: string;
  existingChildIds: string[];
  onSuccess: () => void;
}

export function AddChildDialog({
  virtualDocId,
  existingChildIds,
  onSuccess,
}: AddChildDialogProps) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["documents", { title: search || undefined, page: 1, page_size: 20 }],
    queryFn: () =>
      fetchDocuments({
        page: 1,
        page_size: 20,
        title: search || undefined,
      }),
    enabled: open,
  });

  const documents = data?.data ?? [];

  const mutation = useMutation({
    mutationFn: (childDocumentId: string) =>
      addChild(virtualDocId, childDocumentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["virtual-documents"] });
      toast.success("Document added as child");
      onSuccess();
    },
    onError: (error: Error) => {
      toast.error("Failed to add child: " + error.message);
    },
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          Add Document
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Add Child Document</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <Input
            placeholder="Search documents by title..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <div className="max-h-[300px] overflow-y-auto space-y-1">
            {isLoading ? (
              <p className="text-sm text-muted-foreground py-4 text-center">
                Loading...
              </p>
            ) : documents.length === 0 ? (
              <p className="text-sm text-muted-foreground py-4 text-center">
                No documents found.
              </p>
            ) : (
              documents.map((doc) => {
                const alreadyAdded = existingChildIds.includes(doc.id);
                return (
                  <div
                    key={doc.id}
                    className={`flex items-center justify-between px-3 py-2 rounded-md ${
                      alreadyAdded
                        ? "opacity-50 bg-muted"
                        : "hover:bg-accent/50"
                    }`}
                  >
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium truncate">
                        {doc.title}
                      </p>
                      <p className="text-xs text-muted-foreground truncate">
                        {doc.filename}
                      </p>
                    </div>
                    {alreadyAdded ? (
                      <span className="text-xs text-muted-foreground shrink-0 ml-2">
                        Already added
                      </span>
                    ) : (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="shrink-0 ml-2"
                        disabled={mutation.isPending}
                        onClick={() => mutation.mutate(doc.id)}
                      >
                        Add
                      </Button>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
