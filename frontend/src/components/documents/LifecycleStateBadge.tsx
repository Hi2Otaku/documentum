import { Badge } from "../ui/badge";

const LIFECYCLE_STYLES: Record<string, React.CSSProperties> = {
  draft: {
    backgroundColor: "oklch(0.96 0.04 80)",
    color: "oklch(0.4 0.14 80)",
    borderColor: "oklch(0.88 0.1 80)",
  },
  review: {
    backgroundColor: "oklch(0.95 0.05 250)",
    color: "oklch(0.35 0.12 250)",
    borderColor: "oklch(0.85 0.1 250)",
  },
  approved: {
    backgroundColor: "oklch(0.95 0.05 142)",
    color: "oklch(0.35 0.15 142)",
    borderColor: "oklch(0.85 0.1 142)",
  },
};

interface LifecycleStateBadgeProps {
  state: string | null;
}

export function LifecycleStateBadge({ state }: LifecycleStateBadgeProps) {
  const key = (state ?? "draft").toLowerCase();
  const label = key.charAt(0).toUpperCase() + key.slice(1);
  const style = LIFECYCLE_STYLES[key];

  if (key === "archived" || !style) {
    return (
      <Badge
        variant="outline"
        className="bg-muted text-muted-foreground border-border"
      >
        {label}
      </Badge>
    );
  }

  return (
    <Badge variant="outline" style={style}>
      {label}
    </Badge>
  );
}
