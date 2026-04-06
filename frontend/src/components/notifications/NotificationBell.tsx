import { useState, useEffect, useRef } from "react";
import { Bell } from "lucide-react";
import { toast } from "sonner";
import { useNotificationSSE } from "../../hooks/useNotificationSSE";
import { NotificationPopover } from "./NotificationPopover";

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const { unreadCount, latestNotification } = useNotificationSSE();

  // Track the last notification id to avoid duplicate toasts
  const lastNotifIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (
      latestNotification &&
      latestNotification.id !== lastNotifIdRef.current
    ) {
      lastNotifIdRef.current = latestNotification.id;
      toast(latestNotification.title, {
        description: latestNotification.message,
      });
    }
  }, [latestNotification]);

  return (
    <NotificationPopover open={open} onOpenChange={setOpen}>
      <button
        type="button"
        className="relative p-1.5 rounded-md hover:bg-accent transition-colors"
        aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ""}`}
      >
        <Bell className="size-5 text-muted-foreground" />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 bg-destructive text-destructive-foreground text-xs rounded-full min-w-[18px] h-[18px] flex items-center justify-center px-1">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>
    </NotificationPopover>
  );
}
