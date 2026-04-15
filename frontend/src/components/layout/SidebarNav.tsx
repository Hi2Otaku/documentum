import { useLocation } from "react-router";
import {
  LayoutTemplate,
  Inbox,
  FileText,
  GitBranch,
  BarChart3,
  Search,
  Tags,
  FolderOpen,
  FolderTree,
  Shield,
  ListChecks,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useAuthStore } from "../../stores/authStore";
import { TooltipProvider } from "../ui/tooltip";
import { Separator } from "../ui/separator";
import { SidebarNavItem } from "./SidebarNavItem";

interface NavItem {
  icon: LucideIcon;
  label: string;
  route: string;
  adminOnly: boolean;
}

const NAV_ITEMS: NavItem[] = [
  { icon: FolderTree, label: "Browse", route: "/browse", adminOnly: false },
  { icon: LayoutTemplate, label: "Templates", route: "/templates", adminOnly: false },
  { icon: Inbox, label: "Inbox", route: "/inbox", adminOnly: false },
  { icon: FileText, label: "Documents", route: "/documents", adminOnly: false },
  { icon: Search, label: "Search", route: "/search", adminOnly: false },
  { icon: GitBranch, label: "Workflows", route: "/workflows", adminOnly: false },
  { icon: BarChart3, label: "Dashboard", route: "/dashboard", adminOnly: true },
  { icon: Search, label: "Query", route: "/query", adminOnly: true },
  { icon: Tags, label: "Types", route: "/admin/types", adminOnly: true },
  { icon: FolderOpen, label: "Folders", route: "/admin/folders", adminOnly: true },
  { icon: Shield, label: "Retention", route: "/admin/retention", adminOnly: true },
  { icon: ListChecks, label: "Queues", route: "/admin/queues", adminOnly: true },
];

interface SidebarNavProps {
  isCollapsed: boolean;
  onNavClick?: () => void;
}

export function SidebarNav({ isCollapsed, onNavClick }: SidebarNavProps) {
  const { pathname } = useLocation();
  const isSuperuser = useAuthStore((s) => s.isSuperuser);

  const mainItems = NAV_ITEMS.filter((item) => !item.adminOnly);
  const adminItems = NAV_ITEMS.filter((item) => item.adminOnly);

  return (
    <TooltipProvider delayDuration={0}>
      <nav className="flex-1 overflow-y-auto py-2">
        {!isCollapsed && (
          <div className="px-4 py-2 text-xs text-muted-foreground uppercase tracking-wider">
            Main
          </div>
        )}
        <div className="space-y-1">
          {mainItems.map((item) => (
            <SidebarNavItem
              key={item.route}
              icon={item.icon}
              label={item.label}
              route={item.route}
              isActive={pathname.startsWith(item.route)}
              isCollapsed={isCollapsed}
              onClick={onNavClick}
            />
          ))}
        </div>

        {isSuperuser && (
          <>
            <Separator className="my-2" />
            {!isCollapsed && (
              <div className="px-4 py-2 text-xs text-muted-foreground uppercase tracking-wider">
                Admin
              </div>
            )}
            <div className="space-y-1">
              {adminItems.map((item) => (
                <SidebarNavItem
                  key={item.route}
                  icon={item.icon}
                  label={item.label}
                  route={item.route}
                  isActive={pathname.startsWith(item.route)}
                  isCollapsed={isCollapsed}
                  onClick={onNavClick}
                />
              ))}
            </div>
          </>
        )}
      </nav>
    </TooltipProvider>
  );
}
