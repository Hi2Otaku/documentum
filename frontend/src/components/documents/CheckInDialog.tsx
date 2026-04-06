import { useState, useEffect, useRef } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "../ui/dialog";
import { Button } from "../ui/button";
import { Textarea } from "../ui/textarea";
import { checkinDocument } from "../../api/documents";

interface CheckInDialogProps {
  documentId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CheckInDialog({
  documentId,
  open,
  onOpenChange,
}: CheckInDialogProps) {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [comment, setComment] = useState("");

  // Reset state when dialog opens
  useEffect(() => {
    if (open) {
      setSelectedFile(null);
      setComment("");
    }
  }, [open]);

  const mutation = useMutation({
    mutationFn: () =>
      checkinDocument(documentId, selectedFile!, comment || undefined),
    onSuccess: () => {
      onOpenChange(false);
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({
        queryKey: ["documents", documentId],
      });
      queryClient.invalidateQueries({
        queryKey: ["documents", documentId, "versions"],
      });
      toast.success("New version checked in");
    },
    onError: (error: Error) => {
      toast.error("Action failed: " + error.message);
    },
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Check In Document</DialogTitle>
          <DialogDescription>
            Upload a new version of this document.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div>
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
            />
            <Button
              variant="outline"
              onClick={() => fileInputRef.current?.click()}
            >
              Select new version
            </Button>
            {selectedFile && (
              <p className="text-sm text-muted-foreground mt-2">
                {selectedFile.name} selected
              </p>
            )}
          </div>
          <Textarea
            placeholder="Version comment (optional)"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
          />
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Keep Checked Out
          </Button>
          <Button
            disabled={!selectedFile || mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            {mutation.isPending ? "Checking in..." : "Check In"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
