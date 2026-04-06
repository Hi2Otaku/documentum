import { useQuery } from "@tanstack/react-query";
import { Skeleton } from "../ui/skeleton";

interface TemplateItem {
  id: string;
  name: string;
  description: string | null;
  state: string;
  is_installed: boolean;
}

interface TemplatePickerStepProps {
  selectedTemplateId: string | null;
  onSelect: (id: string) => void;
}

export function TemplatePickerStep({
  selectedTemplateId,
  onSelect,
}: TemplatePickerStepProps) {
  const { data: templates, isLoading } = useQuery({
    queryKey: ["templates"],
    queryFn: async () => {
      const token = localStorage.getItem("token");
      const headers: HeadersInit = token
        ? { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }
        : { "Content-Type": "application/json" };
      const res = await fetch("/api/v1/templates/", { headers });
      if (!res.ok) throw new Error(`API error ${res.status}`);
      const json = await res.json();
      return json.data as TemplateItem[];
    },
  });

  if (isLoading) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-16 w-full rounded-lg" />
        <Skeleton className="h-16 w-full rounded-lg" />
        <Skeleton className="h-16 w-full rounded-lg" />
      </div>
    );
  }

  const active = (templates ?? []).filter(
    (t) => t.state === "active" || t.is_installed,
  );

  if (active.length === 0) {
    return (
      <p className="text-sm text-muted-foreground text-center py-8">
        No installed templates available. Create and install a template first.
      </p>
    );
  }

  return (
    <div className="max-h-[280px] overflow-y-auto space-y-2">
      {active.map((t) => {
        const selected = t.id === selectedTemplateId;
        return (
          <div
            key={t.id}
            role="button"
            tabIndex={0}
            onClick={() => onSelect(t.id)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") onSelect(t.id);
            }}
            className={
              selected
                ? "border-2 border-primary rounded-lg p-[11px] bg-[oklch(0.97_0_0)] cursor-pointer"
                : "border border-border rounded-lg p-3 cursor-pointer hover:bg-accent/50"
            }
          >
            <p className="text-sm font-semibold">{t.name}</p>
            {t.description && (
              <p className="text-xs text-muted-foreground line-clamp-2 mt-0.5">
                {t.description}
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}
