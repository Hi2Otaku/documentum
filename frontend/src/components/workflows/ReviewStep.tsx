import { Separator } from "../ui/separator";

interface ReviewStepProps {
  selectedTemplate: { id: string; name: string } | null;
  selectedDocumentIds: string[];
  variableValues: Record<string, unknown>;
  documents: { id: string; title: string }[];
}

export function ReviewStep({
  selectedTemplate,
  selectedDocumentIds,
  variableValues,
  documents,
}: ReviewStepProps) {
  const attachedDocs = documents.filter((d) =>
    selectedDocumentIds.includes(d.id),
  );
  const variableEntries = Object.entries(variableValues);

  return (
    <div>
      {/* Template */}
      <div>
        <p className="text-xs text-muted-foreground">Template</p>
        <p className="text-sm font-semibold mt-0.5">
          {selectedTemplate?.name ?? "None selected"}
        </p>
      </div>

      <Separator className="my-3" />

      {/* Documents */}
      <div>
        <p className="text-xs text-muted-foreground">Documents</p>
        {attachedDocs.length > 0 ? (
          <>
            <p className="text-sm mt-0.5">
              {attachedDocs.length} document(s) attached
            </p>
            <ul className="mt-1 space-y-0.5">
              {attachedDocs.map((d) => (
                <li key={d.id} className="text-sm">
                  {d.title}
                </li>
              ))}
            </ul>
          </>
        ) : (
          <p className="text-sm mt-0.5">No documents attached</p>
        )}
      </div>

      <Separator className="my-3" />

      {/* Variables */}
      <div>
        <p className="text-xs text-muted-foreground">Variables</p>
        {variableEntries.length > 0 ? (
          <ul className="mt-1 space-y-0.5">
            {variableEntries.map(([name, value]) => (
              <li key={name} className="text-sm">
                {name} = <span className="font-mono">{String(value)}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm mt-0.5">No variables to set</p>
        )}
      </div>
    </div>
  );
}
