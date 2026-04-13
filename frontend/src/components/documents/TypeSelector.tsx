/** TypeSelector — dropdown for choosing document type on upload/edit forms. */
import { useQuery } from "@tanstack/react-query";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import {
  fetchDocumentTypes,
  type DocumentTypeResponse,
} from "../../api/documentTypes";

interface TypeSelectorProps {
  value: string | null;
  onChange: (value: string | null) => void;
  disabled?: boolean;
}

interface TypeSelectorResult {
  element: React.ReactElement;
  selectedType: DocumentTypeResponse | null;
}

export function TypeSelector({
  value,
  onChange,
  disabled,
}: TypeSelectorProps): TypeSelectorResult["element"] {
  const { data: types, isLoading } = useQuery({
    queryKey: ["documentTypes"],
    queryFn: fetchDocumentTypes,
  });

  const sortedTypes = types
    ? [...types].sort((a, b) => a.name.localeCompare(b.name))
    : [];

  const handleValueChange = (val: string) => {
    onChange(val === "__none__" ? null : val);
  };

  const selectValue = value ?? "__none__";

  return (
    <Select
      value={selectValue}
      onValueChange={handleValueChange}
      disabled={disabled || isLoading}
    >
      <SelectTrigger>
        <SelectValue
          placeholder={isLoading ? "Loading types..." : "Select a type..."}
        />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="__none__">No type</SelectItem>
        {sortedTypes.map((type) => (
          <SelectItem key={type.id} value={type.id}>
            {type.parent_type_id ? `  ${type.name}` : type.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

/**
 * Hook to get the currently selected DocumentTypeResponse from the types list.
 * Used by parent components that need access to the schema.
 */
export function useSelectedType(
  value: string | null,
): DocumentTypeResponse | null {
  const { data: types } = useQuery({
    queryKey: ["documentTypes"],
    queryFn: fetchDocumentTypes,
  });

  if (!value || !types) return null;
  return types.find((t) => t.id === value) ?? null;
}
