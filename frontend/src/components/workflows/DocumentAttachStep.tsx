import { useQuery } from "@tanstack/react-query";
import { Checkbox } from "../ui/checkbox";
import { Skeleton } from "../ui/skeleton";
import { fetchDocuments } from "../../api/documents";

interface DocumentAttachStepProps {
  selectedDocumentIds: string[];
  onToggle: (id: string) => void;
}

export function DocumentAttachStep({
  selectedDocumentIds,
  onToggle,
}: DocumentAttachStepProps) {
  const { data, isLoading } = useQuery({
    queryKey: ["documents"],
    queryFn: () => fetchDocuments({ page: 1, page_size: 100 }),
  });

  const documents = data?.data ?? [];

  if (isLoading) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    );
  }

  return (
    <div>
      <p className="text-sm text-muted-foreground mb-3">
        Attach documents to this workflow (optional)
      </p>

      {documents.length === 0 ? (
        <p className="text-sm text-muted-foreground text-center py-8">
          No documents available.
        </p>
      ) : (
        <div className="max-h-[280px] overflow-y-auto space-y-1">
          {documents.map((doc) => (
            <label
              key={doc.id}
              className="flex items-center gap-3 h-10 px-3 rounded-md hover:bg-accent/50 cursor-pointer"
            >
              <Checkbox
                checked={selectedDocumentIds.includes(doc.id)}
                onCheckedChange={() => onToggle(doc.id)}
              />
              <span className="text-sm flex-1 truncate">{doc.title}</span>
              {doc.lifecycle_state && (
                <span className="text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                  {doc.lifecycle_state}
                </span>
              )}
            </label>
          ))}
        </div>
      )}
    </div>
  );
}
