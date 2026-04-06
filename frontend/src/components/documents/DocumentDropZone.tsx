import { useRef, useState, useCallback } from "react";
import { Upload } from "lucide-react";
import { toast } from "sonner";
import { Button } from "../ui/button";
import { UploadProgressItem } from "./UploadProgressItem";
import { uploadDocument } from "../../api/documents";
import { useAuthStore } from "../../stores/authStore";

interface UploadFileEntry {
  name: string;
  status: "pending" | "uploading" | "done" | "error";
}

interface DocumentDropZoneProps {
  onUploadComplete: () => void;
}

function titleFromFilename(filename: string): string {
  const lastDot = filename.lastIndexOf(".");
  return lastDot > 0 ? filename.slice(0, lastDot) : filename;
}

export function DocumentDropZone({ onUploadComplete }: DocumentDropZoneProps) {
  const [uploadingFiles, setUploadingFiles] = useState<UploadFileEntry[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const username = useAuthStore((s) => s.username) ?? "unknown";

  const isUploading = uploadingFiles.length > 0;

  const processFiles = useCallback(
    async (files: FileList | File[]) => {
      const fileArray = Array.from(files);
      if (fileArray.length === 0) return;

      const entries: UploadFileEntry[] = fileArray.map((f) => ({
        name: f.name,
        status: "pending" as const,
      }));
      setUploadingFiles(entries);

      for (let i = 0; i < fileArray.length; i++) {
        setUploadingFiles((prev) =>
          prev.map((entry, idx) =>
            idx === i ? { ...entry, status: "uploading" } : entry
          )
        );

        try {
          await uploadDocument(
            fileArray[i],
            titleFromFilename(fileArray[i].name),
            username
          );
          setUploadingFiles((prev) =>
            prev.map((entry, idx) =>
              idx === i ? { ...entry, status: "done" } : entry
            )
          );
          toast.success("Document uploaded");
        } catch (err: unknown) {
          const message =
            err instanceof Error ? err.message : "Unknown error";
          setUploadingFiles((prev) =>
            prev.map((entry, idx) =>
              idx === i ? { ...entry, status: "error" } : entry
            )
          );
          toast.error(`Upload failed: ${message}`);
        }
      }

      onUploadComplete();

      setTimeout(() => {
        setUploadingFiles([]);
      }, 3000);
    },
    [onUploadComplete, username]
  );

  const handleDragOver = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(true);
    },
    []
  );

  const handleDragLeave = useCallback(() => {
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      processFiles(e.dataTransfer.files);
    },
    [processFiles]
  );

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files && e.target.files.length > 0) {
        processFiles(e.target.files);
        // Reset so the same file can be re-selected
        e.target.value = "";
      }
    },
    [processFiles]
  );

  const handleZoneClick = useCallback(() => {
    if (!isUploading) {
      inputRef.current?.click();
    }
  }, [isUploading]);

  if (isUploading) {
    return (
      <div className="border-2 border-dashed rounded-lg mb-4 bg-secondary">
        {uploadingFiles.map((file, idx) => (
          <UploadProgressItem
            key={`${file.name}-${idx}`}
            name={file.name}
            status={file.status}
          />
        ))}
      </div>
    );
  }

  return (
    <div
      className={`border-2 border-dashed rounded-lg h-[120px] flex flex-col items-center justify-center gap-2 mb-4 transition-colors cursor-pointer ${
        isDragOver
          ? "bg-[oklch(0.97_0.02_250)] border-primary"
          : "bg-secondary border-border"
      }`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={handleZoneClick}
    >
      <Upload
        size={32}
        className={isDragOver ? "text-primary" : "text-muted-foreground"}
      />
      <span className="text-sm text-muted-foreground">
        {isDragOver
          ? "Drop files to upload"
          : "Drag files here or click to upload"}
      </span>
      {!isDragOver && (
        <Button
          variant="outline"
          size="sm"
          onClick={(e) => {
            e.stopPropagation();
            inputRef.current?.click();
          }}
        >
          Browse
        </Button>
      )}
      <input
        ref={inputRef}
        type="file"
        multiple
        className="hidden"
        onChange={handleInputChange}
      />
    </div>
  );
}
