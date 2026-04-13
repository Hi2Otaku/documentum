import { Label } from "../ui/label";
import { Textarea } from "../ui/textarea";

const SCHEMA_PLACEHOLDER = `{
  "type": "object",
  "properties": {},
  "required": []
}`;

interface SchemaEditorProps {
  value: string;
  onChange: (value: string) => void;
  error: string | null;
}

export function SchemaEditor({ value, onChange, error }: SchemaEditorProps) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor="schema-textarea">Metadata Schema (JSON)</Label>
      <Textarea
        id="schema-textarea"
        className="font-mono min-h-[200px] resize-y"
        placeholder={SCHEMA_PLACEHOLDER}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        aria-describedby={error ? "schema-error" : undefined}
      />
      {error && (
        <p id="schema-error" className="text-sm text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}
