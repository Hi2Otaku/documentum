import { Badge } from "../ui/badge";

const stateStyles: Record<string, React.CSSProperties> = {
  running: {
    background: "oklch(0.95 0.05 250)",
    color: "oklch(0.35 0.12 250)",
    borderColor: "oklch(0.85 0.1 250)",
  },
  halted: {
    background: "oklch(0.96 0.04 80)",
    color: "oklch(0.4 0.14 80)",
    borderColor: "oklch(0.88 0.1 80)",
  },
  finished: {
    background: "oklch(0.95 0.05 142)",
    color: "oklch(0.35 0.15 142)",
    borderColor: "oklch(0.85 0.1 142)",
  },
  failed: {
    background: "oklch(0.95 0.04 27)",
    color: "oklch(0.4 0.18 27)",
    borderColor: "oklch(0.88 0.12 27)",
  },
};

interface WorkflowStateBadgeProps {
  state: string;
}

export function WorkflowStateBadge({ state }: WorkflowStateBadgeProps) {
  const lower = state.toLowerCase();
  const style = stateStyles[lower];

  if (!style) {
    // dormant or unknown -- use secondary variant
    return <Badge variant="secondary">{state.toUpperCase()}</Badge>;
  }

  return (
    <Badge variant="outline" style={style}>
      {state.toUpperCase()}
    </Badge>
  );
}
