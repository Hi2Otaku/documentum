import { ArrowUp, AlertTriangle } from "lucide-react";

interface PriorityIconProps {
  priority: number;
}

export function PriorityIcon({ priority }: PriorityIconProps) {
  if (priority === 0) {
    return null;
  }

  if (priority === 1) {
    return <ArrowUp size={14} style={{ color: "oklch(0.55 0.2 27)" }} />;
  }

  // priority >= 2 (urgent)
  return <AlertTriangle size={14} style={{ color: "oklch(0.55 0.2 27)" }} />;
}
