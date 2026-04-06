import type { NotificationResponse } from "../../api/notifications";
import { cn } from "../../lib/utils";

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

interface NotificationItemProps {
  notification: NotificationResponse;
  onMarkRead: (id: string) => void;
}

export function NotificationItem({
  notification,
  onMarkRead,
}: NotificationItemProps) {
  return (
    <button
      type="button"
      className={cn(
        "flex items-start gap-2 w-full text-left p-3 hover:bg-accent cursor-pointer transition-colors border-b last:border-0",
        !notification.is_read && "bg-accent/50"
      )}
      onClick={() => {
        if (!notification.is_read) {
          onMarkRead(notification.id);
        }
      }}
    >
      {!notification.is_read && (
        <span className="mt-1.5 size-2 rounded-full bg-primary shrink-0" />
      )}
      <div className="flex-1 min-w-0">
        <p
          className={cn(
            "text-sm truncate",
            !notification.is_read ? "font-medium" : "text-muted-foreground"
          )}
        >
          {notification.title}
        </p>
        {notification.message && (
          <p className="text-xs text-muted-foreground truncate">
            {notification.message}
          </p>
        )}
        <p className="text-[10px] text-muted-foreground mt-0.5">
          {timeAgo(notification.created_at)}
        </p>
      </div>
    </button>
  );
}
