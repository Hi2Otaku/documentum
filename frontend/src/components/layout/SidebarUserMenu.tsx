import { useNavigate } from "react-router";
import { Circle, LogOut } from "lucide-react";
import { useAuthStore } from "../../stores/authStore";
import { Avatar, AvatarFallback } from "../ui/avatar";
import { Badge } from "../ui/badge";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from "../ui/dropdown-menu";
import { cn } from "../../lib/utils";
import { NotificationBell } from "../notifications/NotificationBell";

interface SidebarUserMenuProps {
  isCollapsed: boolean;
}

export function SidebarUserMenu({ isCollapsed }: SidebarUserMenuProps) {
  const navigate = useNavigate();
  const username = useAuthStore((s) => s.username);
  const isSuperuser = useAuthStore((s) => s.isSuperuser);
  const isAvailable = useAuthStore((s) => s.isAvailable);
  const setAvailability = useAuthStore((s) => s.setAvailability);
  const logout = useAuthStore((s) => s.logout);

  const initials = username ? username.slice(0, 2).toUpperCase() : "??";

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div
      className={cn(
        "h-14 flex items-center gap-2 px-3 shrink-0",
        isCollapsed && "justify-center"
      )}
    >
      {!isCollapsed && <NotificationBell />}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            className={cn(
              "flex items-center gap-2 rounded-md p-1 hover:bg-accent transition-colors w-full",
              isCollapsed && "justify-center w-auto"
            )}
          >
            <Avatar className="h-8 w-8">
              <AvatarFallback className="bg-muted text-xs">
                {initials}
              </AvatarFallback>
            </Avatar>
            {!isCollapsed && (
              <div className="flex items-center gap-1.5 min-w-0">
                <span className="text-sm font-medium truncate max-w-[140px]">
                  {username}
                </span>
                <span
                  className="inline-block size-2 rounded-full shrink-0"
                  style={{
                    backgroundColor: isAvailable
                      ? "oklch(0.72 0.19 142)"
                      : "var(--color-destructive)",
                  }}
                />
              </div>
            )}
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent
          align="start"
          side={isCollapsed ? "right" : "bottom"}
          className="w-48"
        >
          <DropdownMenuItem disabled className="font-semibold text-sm">
            {username}
          </DropdownMenuItem>
          {isSuperuser && (
            <div className="px-2 py-1">
              <Badge variant="secondary">Admin</Badge>
            </div>
          )}
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => setAvailability(!isAvailable)}>
            <Circle
              className="size-2"
              fill={
                isAvailable
                  ? "oklch(0.72 0.19 142)"
                  : "var(--color-destructive)"
              }
              stroke="none"
            />
            {isAvailable ? "Available" : "Unavailable"}
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            onClick={handleLogout}
            className="focus:text-destructive"
          >
            <LogOut className="size-4" />
            Log out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
