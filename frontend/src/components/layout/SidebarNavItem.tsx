import { Link } from "react-router";
import type { LucideIcon } from "lucide-react";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "../ui/tooltip";
import { cn } from "../../lib/utils";

interface SidebarNavItemProps {
  icon: LucideIcon;
  label: string;
  route: string;
  isActive: boolean;
  isCollapsed: boolean;
  onClick?: () => void;
}

export function SidebarNavItem({
  icon: Icon,
  label,
  route,
  isActive,
  isCollapsed,
  onClick,
}: SidebarNavItemProps) {
  const link = (
    <Link
      to={route}
      onClick={onClick}
      className={cn(
        "flex items-center h-10 px-3 rounded-md text-sm transition-colors relative",
        isActive
          ? "border-l-[3px] border-primary bg-accent text-foreground"
          : "text-muted-foreground hover:bg-accent hover:text-foreground",
        isCollapsed ? "justify-center px-0 mx-2" : "mx-2"
      )}
    >
      <Icon className="size-5 shrink-0" />
      {!isCollapsed && <span className="ml-3">{label}</span>}
    </Link>
  );

  if (isCollapsed) {
    return (
      <Tooltip>
        <TooltipTrigger asChild>{link}</TooltipTrigger>
        <TooltipContent side="right">{label}</TooltipContent>
      </Tooltip>
    );
  }

  return link;
}
