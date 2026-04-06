import type { ProcessVariableResponse } from "../../api/workflows";

interface WorkflowVariablesListProps {
  variables: ProcessVariableResponse[];
}

function getDisplayValue(v: ProcessVariableResponse): string {
  if (v.string_value !== null) return v.string_value;
  if (v.int_value !== null) return String(v.int_value);
  if (v.bool_value !== null) return v.bool_value ? "true" : "false";
  if (v.date_value !== null) return v.date_value;
  return "\u2014";
}

export function WorkflowVariablesList({ variables }: WorkflowVariablesListProps) {
  if (variables.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">No variables defined.</p>
    );
  }

  return (
    <div className="space-y-3">
      {variables.map((v) => (
        <div key={v.id} className="flex flex-col gap-0.5">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold">{v.name}</span>
            <span className="text-xs text-muted-foreground">
              {v.variable_type}
            </span>
          </div>
          <span className="font-mono text-sm">{getDisplayValue(v)}</span>
        </div>
      ))}
    </div>
  );
}
