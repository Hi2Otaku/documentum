import { Badge } from "../ui/badge";

const STATE_STYLES: Record<string, React.CSSProperties> = {
  available: {
    backgroundColor: "oklch(0.95 0.05 142)",
    color: "oklch(0.35 0.15 142)",
    borderColor: "oklch(0.85 0.1 142)",
  },
  acquired: {
    backgroundColor: "oklch(0.95 0.05 250)",
    color: "oklch(0.35 0.12 250)",
    borderColor: "oklch(0.85 0.1 250)",
  },
  delegated: {
    backgroundColor: "oklch(0.95 0.04 280)",
    color: "oklch(0.35 0.12 280)",
    borderColor: "oklch(0.85 0.08 280)",
  },
  complete: {
    /* uses CSS variables via className instead */
  },
  rejected: {
    backgroundColor: "oklch(0.95 0.04 27)",
    color: "oklch(0.45 0.2 27)",
    borderColor: "oklch(0.85 0.1 27)",
  },
  suspended: {
    backgroundColor: "oklch(0.96 0.04 80)",
    color: "oklch(0.4 0.14 80)",
    borderColor: "oklch(0.88 0.1 80)",
  },
};

interface WorkItemStateBadgeProps {
  state: string;
}

export function WorkItemStateBadge({ state }: WorkItemStateBadgeProps) {
  const key = state.toLowerCase();
  const style = STATE_STYLES[key];
  const label = state.charAt(0).toUpperCase() + state.slice(1);

  if (key === "complete") {
    return (
      <Badge variant="outline" className="bg-muted text-muted-foreground border-border">
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
