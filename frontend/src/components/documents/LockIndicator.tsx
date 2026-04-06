import { Lock } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "../ui/tooltip";

interface LockIndicatorProps {
  lockedBy: string | null;
  currentUserId: string;
  compact?: boolean;
}

export function LockIndicator({
  lockedBy,
  currentUserId,
  compact = false,
}: LockIndicatorProps) {
  if (!lockedBy) {
    return null;
  }

  const isSelf = lockedBy === currentUserId;
  const iconColor = isSelf ? "oklch(0.55 0.19 250)" : "oklch(0.55 0.2 27)";
  const displayName = isSelf
    ? "you"
    : lockedBy.slice(0, 8);
  const fullText = isSelf
    ? "Checked out by you"
    : `Checked out by ${lockedBy.slice(0, 8)}`;

  if (compact) {
    return (
      <Tooltip>
        <TooltipTrigger asChild>
          <span className="inline-flex items-center">
            <Lock size={14} style={{ color: iconColor }} />
          </span>
        </TooltipTrigger>
        <TooltipContent>{fullText}</TooltipContent>
      </Tooltip>
    );
  }

  return (
    <span className="inline-flex items-center gap-1">
      <Lock size={14} style={{ color: iconColor }} />
      <span
        className={isSelf ? "text-xs" : "text-xs text-muted-foreground"}
        style={isSelf ? { color: "oklch(0.55 0.19 250)" } : undefined}
      >
        Checked out by {displayName}
      </span>
    </span>
  );
}
