import { useState } from "react";
import { Trash2, Edit, RefreshCw, X } from "lucide-react";
import { Button } from "../ui/button";
import { Textarea } from "../ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "../ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "../ui/dropdown-menu";
import { bulkUpdate, bulkDelete, bulkLifecycle } from "../../api/bulk";

interface BulkActionToolbarProps {
  selectedCount: number;
  selectedIds: string[];
  onClear: () => void;
  onJobStarted: (jobId: string) => void;
}

const LIFECYCLE_STATES = ["draft", "review", "approved", "archived"] as const;

export function BulkActionToolbar({
  selectedCount,
  selectedIds,
  onClear,
  onJobStarted,
}: BulkActionToolbarProps) {
  const [updateDialogOpen, setUpdateDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [metadataJson, setMetadataJson] = useState("{}");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleBulkUpdate() {
    setError(null);
    let parsed: Record<string, unknown>;
    try {
      parsed = JSON.parse(metadataJson);
    } catch {
      setError("Invalid JSON");
      return;
    }
    setLoading(true);
    try {
      const job = await bulkUpdate(selectedIds, parsed);
      onJobStarted(job.id);
      onClear();
      setUpdateDialogOpen(false);
      setMetadataJson("{}");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start bulk update");
    } finally {
      setLoading(false);
    }
  }

  async function handleBulkLifecycle(targetState: string) {
    setLoading(true);
    try {
      const job = await bulkLifecycle(selectedIds, targetState);
      onJobStarted(job.id);
      onClear();
    } catch (err) {
      window.alert(err instanceof Error ? err.message : "Failed to start lifecycle change");
    } finally {
      setLoading(false);
    }
  }

  async function handleBulkDelete() {
    setLoading(true);
    try {
      const job = await bulkDelete(selectedIds);
      onJobStarted(job.id);
      onClear();
      setDeleteDialogOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start bulk delete");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <div className="flex items-center gap-2 px-4 py-2 bg-accent/50 border-b">
        <span className="text-sm font-medium">
          {selectedCount} selected
        </span>

        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            setMetadataJson("{}");
            setError(null);
            setUpdateDialogOpen(true);
          }}
          disabled={loading}
        >
          <Edit className="h-3.5 w-3.5 mr-1.5" />
          Update Metadata
        </Button>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm" disabled={loading}>
              <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
              Change State
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            {LIFECYCLE_STATES.map((state) => (
              <DropdownMenuItem
                key={state}
                onClick={() => handleBulkLifecycle(state)}
              >
                {state.charAt(0).toUpperCase() + state.slice(1)}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>

        <Button
          variant="destructive"
          size="sm"
          onClick={() => {
            setError(null);
            setDeleteDialogOpen(true);
          }}
          disabled={loading}
        >
          <Trash2 className="h-3.5 w-3.5 mr-1.5" />
          Delete
        </Button>

        <Button variant="ghost" size="sm" onClick={onClear} disabled={loading}>
          <X className="h-3.5 w-3.5 mr-1.5" />
          Clear
        </Button>
      </div>

      {/* Update Metadata Dialog */}
      <Dialog open={updateDialogOpen} onOpenChange={setUpdateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Update Metadata</DialogTitle>
            <DialogDescription>
              Enter metadata JSON to apply to {selectedCount} document{selectedCount !== 1 ? "s" : ""}.
            </DialogDescription>
          </DialogHeader>
          <Textarea
            value={metadataJson}
            onChange={(e) => setMetadataJson(e.target.value)}
            rows={8}
            className="font-mono text-sm"
            placeholder='{"key": "value"}'
          />
          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setUpdateDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleBulkUpdate} disabled={loading}>
              {loading ? "Starting..." : "Apply Update"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete {selectedCount} document{selectedCount !== 1 ? "s" : ""}?</DialogTitle>
            <DialogDescription>
              This action cannot be undone. The selected documents will be permanently deleted.
            </DialogDescription>
          </DialogHeader>
          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleBulkDelete} disabled={loading}>
              {loading ? "Deleting..." : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
