import { FileText } from "lucide-react";
import { cn } from "../../lib/utils";

interface SidebarHeaderProps {
  isCollapsed: boolean;
}

export function SidebarHeader({ isCollapsed }: SidebarHeaderProps) {
  return (
    <div
      className={cn(
        "h-12 flex items-center px-4 shrink-0",
        isCollapsed && "justify-center px-2"
      )}
    >
      <FileText className="size-5 text-foreground shrink-0" />
      {!isCollapsed && (
        <span className="ml-2 text-base font-semibold text-foreground">
          Documentum
        </span>
      )}
    </div>
  );
}
