/** TypeMetadataForm — dynamic form fields rendered from JSON Schema. */
import { Label } from "../ui/label";
import { Input } from "../ui/input";
import { Checkbox } from "../ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";

interface SchemaProperty {
  type?: string;
  title?: string;
  format?: string;
  enum?: string[];
}

interface JsonSchema {
  properties?: Record<string, SchemaProperty>;
  required?: string[];
}

interface TypeMetadataFormProps {
  schema: Record<string, unknown>;
  values: Record<string, unknown>;
  onChange: (values: Record<string, unknown>) => void;
  errors?: Record<string, string>;
  inheritedFields?: string[];
}

function parseSchema(schema: Record<string, unknown>): JsonSchema {
  return schema as JsonSchema;
}

export function TypeMetadataForm({
  schema,
  values,
  onChange,
  errors = {},
  inheritedFields = [],
}: TypeMetadataFormProps) {
  const parsed = parseSchema(schema);
  const properties = parsed.properties ?? {};
  const requiredFields = parsed.required ?? [];

  const allKeys = Object.keys(properties);
  const inheritedKeys = allKeys
    .filter((k) => inheritedFields.includes(k))
    .sort();
  const ownKeys = allKeys.filter((k) => !inheritedFields.includes(k));
  const orderedKeys = [...inheritedKeys, ...ownKeys];

  if (orderedKeys.length === 0) return null;

  const handleFieldChange = (key: string, newValue: unknown) => {
    onChange({ ...values, [key]: newValue });
  };

  return (
    <div className="space-y-4">
      <div className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
        Type-Specific Metadata
      </div>

      {orderedKeys.map((key) => {
        const prop = properties[key];
        const isRequired = requiredFields.includes(key);
        const isInherited = inheritedFields.includes(key);
        const fieldLabel = prop.title ?? key;
        const fieldId = `metadata-${key}`;
        const currentValue = values[key];
        const error = errors[key];

        return (
          <div key={key} className="space-y-1">
            <Label htmlFor={fieldId}>
              {fieldLabel}
              {isRequired && (
                <span className="text-destructive ml-1" aria-hidden="true">
                  *
                </span>
              )}
              {isInherited && (
                <span className="text-xs text-muted-foreground ml-2">
                  (inherited)
                </span>
              )}
            </Label>

            {renderField(prop, key, fieldId, currentValue, isRequired, handleFieldChange)}

            {error && (
              <span className="text-sm text-destructive">{error}</span>
            )}
          </div>
        );
      })}
    </div>
  );
}

function renderField(
  prop: SchemaProperty,
  key: string,
  fieldId: string,
  currentValue: unknown,
  isRequired: boolean,
  handleChange: (key: string, value: unknown) => void,
): React.ReactElement {
  const { type, format, enum: enumValues } = prop;

  // Boolean -> Checkbox
  if (type === "boolean") {
    return (
      <Checkbox
        id={fieldId}
        checked={currentValue === true}
        onCheckedChange={(checked) => handleChange(key, checked === true)}
        aria-required={isRequired ? "true" : undefined}
      />
    );
  }

  // String with enum -> Select
  if (type === "string" && enumValues && enumValues.length > 0) {
    return (
      <Select
        value={typeof currentValue === "string" ? currentValue : ""}
        onValueChange={(val) => handleChange(key, val)}
      >
        <SelectTrigger id={fieldId} aria-required={isRequired ? "true" : undefined}>
          <SelectValue placeholder="Select..." />
        </SelectTrigger>
        <SelectContent>
          {enumValues.map((opt) => (
            <SelectItem key={opt} value={opt}>
              {opt}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    );
  }

  // String with date format
  if (type === "string" && format === "date") {
    return (
      <Input
        id={fieldId}
        type="date"
        value={typeof currentValue === "string" ? currentValue : ""}
        onChange={(e) => handleChange(key, e.target.value)}
        aria-required={isRequired ? "true" : undefined}
      />
    );
  }

  // Number
  if (type === "number") {
    return (
      <Input
        id={fieldId}
        type="number"
        value={typeof currentValue === "number" ? String(currentValue) : ""}
        onChange={(e) => handleChange(key, e.target.value === "" ? "" : Number(e.target.value))}
        aria-required={isRequired ? "true" : undefined}
      />
    );
  }

  // Default: string -> text input
  return (
    <Input
      id={fieldId}
      type="text"
      value={typeof currentValue === "string" ? currentValue : ""}
      onChange={(e) => handleChange(key, e.target.value)}
      aria-required={isRequired ? "true" : undefined}
    />
  );
}
