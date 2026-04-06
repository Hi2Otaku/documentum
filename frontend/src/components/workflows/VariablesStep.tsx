import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Switch } from "../ui/switch";
import { Skeleton } from "../ui/skeleton";

interface TemplateVariable {
  id: string;
  name: string;
  variable_type: string;
  string_value: string | null;
  int_value: number | null;
  bool_value: boolean | null;
}

interface TemplateDetail {
  variables: TemplateVariable[];
}

async function fetchTemplateDetail(id: string): Promise<TemplateDetail> {
  const token = localStorage.getItem("token");
  const headers: HeadersInit = token
    ? { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }
    : { "Content-Type": "application/json" };
  const res = await fetch(`/api/v1/templates/${id}`, { headers });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  const json = await res.json();
  return json.data as TemplateDetail;
}

interface VariablesStepProps {
  templateId: string;
  variableValues: Record<string, unknown>;
  onChange: (name: string, value: unknown) => void;
}

export function VariablesStep({
  templateId,
  variableValues,
  onChange,
}: VariablesStepProps) {
  const { data: template, isLoading } = useQuery({
    queryKey: ["templates", templateId],
    queryFn: () => fetchTemplateDetail(templateId),
    enabled: !!templateId,
  });

  const variables = template?.variables ?? [];

  // Initialize defaults on load
  useEffect(() => {
    for (const v of variables) {
      if (variableValues[v.name] === undefined) {
        if (v.variable_type === "string") {
          onChange(v.name, v.string_value ?? "");
        } else if (v.variable_type === "integer") {
          onChange(v.name, v.int_value ?? 0);
        } else if (v.variable_type === "boolean") {
          onChange(v.name, v.bool_value ?? false);
        }
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [variables.length]);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    );
  }

  if (variables.length === 0) {
    return (
      <p className="text-sm text-muted-foreground text-center py-8">
        This template has no configurable variables.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {variables.map((v) => (
        <div key={v.id}>
          <Label className="text-xs text-muted-foreground">
            {v.name} ({v.variable_type})
          </Label>
          {v.variable_type === "boolean" ? (
            <div className="flex items-center justify-between mt-1">
              <span className="text-sm">{v.name}</span>
              <Switch
                checked={Boolean(variableValues[v.name] ?? false)}
                onCheckedChange={(checked) => onChange(v.name, checked)}
              />
            </div>
          ) : v.variable_type === "integer" ? (
            <Input
              type="number"
              className="mt-1"
              value={String(variableValues[v.name] ?? 0)}
              onChange={(e) => onChange(v.name, Number(e.target.value))}
            />
          ) : (
            <Input
              type="text"
              className="mt-1"
              value={String(variableValues[v.name] ?? "")}
              onChange={(e) => onChange(v.name, e.target.value)}
            />
          )}
        </div>
      ))}
    </div>
  );
}
