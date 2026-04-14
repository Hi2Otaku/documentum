import { useEffect, useState } from "react";
import { Search, X } from "lucide-react";
import { Input } from "../ui/input";

interface SearchInputProps {
  value: string;
  onChange: (value: string) => void;
}

export function SearchInput({ value, onChange }: SearchInputProps) {
  const [localValue, setLocalValue] = useState(value);

  // Sync external value changes
  useEffect(() => {
    setLocalValue(value);
  }, [value]);

  // Debounce with 300ms delay
  useEffect(() => {
    const timer = setTimeout(() => {
      onChange(localValue);
    }, 300);
    return () => clearTimeout(timer);
  }, [localValue, onChange]);

  return (
    <div className="relative">
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
      <Input
        value={localValue}
        onChange={(e) => setLocalValue(e.target.value)}
        placeholder="Search documents by content or metadata..."
        className="h-12 text-lg pl-10 pr-10"
      />
      {localValue && (
        <button
          type="button"
          onClick={() => {
            setLocalValue("");
            onChange("");
          }}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
        >
          <X className="h-5 w-5" />
        </button>
      )}
    </div>
  );
}
