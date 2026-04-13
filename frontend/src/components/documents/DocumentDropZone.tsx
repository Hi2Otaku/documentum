import { useRef, useState, useCallback } from "react";
import { Upload } from "lucide-react";
import { toast } from "sonner";
import { Button } from "../ui/button";
import { Label } from "../ui/label";
import { UploadProgressItem } from "./UploadProgressItem";
import { TypeSelector, useSelectedType } from "./TypeSelector";
import { TypeMetadataForm } from "./TypeMetadataForm";
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

/** Parse a 422 validation error response into field-level errors map. */
function parse422Errors(errorText: string): Record<string, string> | null {
  try {
    const json = JSON.parse(errorText) as unknown;
    if (
      json &&
      typeof json === "object" &&
      "detail" in json &&
      Array.isArray((json as { detail: unknown }).detail)
    ) {
      const detail = (json as { detail: { loc: string[]; msg: string }[] }).detail;
      const fieldErrors: Record<string, string> = {};
      for (const err of detail) {
        const loc = err.loc;
        // loc example: ["body", "custom_properties", "invoice_number"]
        if (loc.length >= 2) {
          const fieldKey = loc[loc.length - 1];
          fieldErrors[fieldKey] = err.msg;
        }
      }
      return Object.keys(fieldErrors).length > 0 ? fieldErrors : null;
    }
    // Flat error detail string
    if (
      json &&
      typeof json === "object" &&
      "detail" in json &&
      typeof (json as { detail: string }).detail === "string"
    ) {
      return null;
    }
  } catch {
    // not JSON
  }
  return null;
}

export function DocumentDropZone({ onUploadComplete }: DocumentDropZoneProps) {
  const [uploadingFiles, setUploadingFiles] = useState<UploadFileEntry[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [showUploadForm, setShowUploadForm] = useState(false);
  const [selectedTypeId, setSelectedTypeId] = useState<string | null>(null);
  const [metadata, setMetadata] = useState<Record<string, unknown>>({});
  const [metadataErrors, setMetadataErrors] = useState<Record<string, string>>({});
  const inputRef = useRef<HTMLInputElement>(null);
  const username = useAuthStore((s) => s.username) ?? "unknown";

  const isUploading = uploadingFiles.length > 0;

  const selectedType = useSelectedType(selectedTypeId);

  // Reset upload form state
  const resetForm = useCallback(() => {
    setPendingFile(null);
    setShowUploadForm(false);
    setSelectedTypeId(null);
    setMetadata({});
    setMetadataErrors({});
  }, []);

  // Handle single-file upload with optional type + metadata
  const uploadSingleFile = useCallback(
    async (file: File) => {
      const entry: UploadFileEntry = { name: file.name, status: "pending" };
      setUploadingFiles([entry]);
      setUploadingFiles([{ ...entry, status: "uploading" }]);

      try {
        await uploadDocument(
          file,
          titleFromFilename(file.name),
          username,
          selectedTypeId ?? undefined,
          Object.keys(metadata).length > 0 ? metadata : undefined,
        );
        setUploadingFiles([{ ...entry, status: "done" }]);
        toast.success("Document uploaded");
        onUploadComplete();
        setTimeout(() => setUploadingFiles([]), 3000);
        resetForm();
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "Unknown error";

        // Check for 422 with field-level errors
        const status422Match = message.match(/API error 422: (.+)/s);
        if (status422Match) {
          const fieldErrors = parse422Errors(status422Match[1]);
          if (fieldErrors) {
            const count = Object.keys(fieldErrors).length;
            setMetadataErrors(fieldErrors);
            setUploadingFiles([]);
            toast.error(`Metadata validation failed: ${count} field(s) have errors`);
            return;
          }
        }

        setUploadingFiles([{ ...entry, status: "error" }]);
        toast.error(`Upload failed: ${message}`);
        setTimeout(() => {
          setUploadingFiles([]);
          resetForm();
        }, 3000);
      }
    },
    [username, selectedTypeId, metadata, onUploadComplete, resetForm],
  );

  // Process multiple files (batch upload without type)
  const processMultipleFiles = useCallback(
    async (files: File[]) => {
      const entries: UploadFileEntry[] = files.map((f) => ({
        name: f.name,
        status: "pending" as const,
      }));
      setUploadingFiles(entries);

      for (let i = 0; i < files.length; i++) {
        setUploadingFiles((prev) =>
          prev.map((entry, idx) =>
            idx === i ? { ...entry, status: "uploading" } : entry,
          ),
        );

        try {
          await uploadDocument(files[i], titleFromFilename(files[i].name), username);
          setUploadingFiles((prev) =>
            prev.map((entry, idx) =>
              idx === i ? { ...entry, status: "done" } : entry,
            ),
          );
          toast.success("Document uploaded");
        } catch (err: unknown) {
          const message = err instanceof Error ? err.message : "Unknown error";
          setUploadingFiles((prev) =>
            prev.map((entry, idx) =>
              idx === i ? { ...entry, status: "error" } : entry,
            ),
          );
          toast.error(`Upload failed: ${message}`);
        }
      }

      onUploadComplete();
      setTimeout(() => setUploadingFiles([]), 3000);
    },
    [onUploadComplete, username],
  );

  const processFiles = useCallback(
    (files: FileList | File[]) => {
      const fileArray = Array.from(files);
      if (fileArray.length === 0) return;

      if (fileArray.length === 1) {
        // Single file: show upload form
        setPendingFile(fileArray[0]);
        setSelectedTypeId(null);
        setMetadata({});
        setMetadataErrors({});
        setShowUploadForm(true);
      } else {
        // Multiple files: batch upload without type
        void processMultipleFiles(fileArray);
      }
    },
    [processMultipleFiles],
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      processFiles(e.dataTransfer.files);
    },
    [processFiles],
  );

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files && e.target.files.length > 0) {
        processFiles(e.target.files);
        e.target.value = "";
      }
    },
    [processFiles],
  );

  const handleZoneClick = useCallback(() => {
    if (!isUploading && !showUploadForm) {
      inputRef.current?.click();
    }
  }, [isUploading, showUploadForm]);

  // Uploading state
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

  // Single file upload form
  if (showUploadForm && pendingFile) {
    const effectiveSchema = selectedType?.metadata_schema ?? null;
    const inheritedFields =
      selectedType?.parent_type_id && effectiveSchema
        ? [] // parent schema already merged by backend; client-side we just show all
        : [];

    return (
      <div className="border-2 border-dashed rounded-lg mb-4 p-4 bg-secondary space-y-4">
        <div className="text-sm font-semibold">{pendingFile.name}</div>

        <div className="space-y-1">
          <Label>Document Type</Label>
          <TypeSelector
            value={selectedTypeId}
            onChange={(val) => {
              setSelectedTypeId(val);
              setMetadata({});
              setMetadataErrors({});
            }}
          />
        </div>

        {effectiveSchema &&
          typeof effectiveSchema === "object" &&
          (effectiveSchema as { properties?: unknown }).properties && (
            <TypeMetadataForm
              schema={effectiveSchema as Record<string, unknown>}
              values={metadata}
              onChange={setMetadata}
              errors={metadataErrors}
              inheritedFields={inheritedFields}
            />
          )}

        <div className="flex gap-2 justify-end pt-2">
          <Button variant="outline" size="sm" onClick={resetForm}>
            Cancel
          </Button>
          <Button
            size="sm"
            onClick={() => void uploadSingleFile(pendingFile)}
          >
            Upload
          </Button>
        </div>
      </div>
    );
  }

  // Default drop zone
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
