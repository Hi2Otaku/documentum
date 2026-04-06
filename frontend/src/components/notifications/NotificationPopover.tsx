import type { ReactNode } from "react";
import { CheckCheck } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchNotifications,
  markNotificationRead,
  markAllNotificationsRead,
} from "../../api/notifications";
import {
  Popover,
  PopoverTrigger,
  PopoverContent,
} from "../ui/popover";
import { Button } from "../ui/button";
import { NotificationItem } from "./NotificationItem";

interface NotificationPopoverProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: ReactNode;
}

export function NotificationPopover({
  open,
  onOpenChange,
  children,
}: NotificationPopoverProps) {
  const queryClient = useQueryClient();

  const { data: notificationsData } = useQuery({
    queryKey: ["notifications", "list"],
    queryFn: () => fetchNotifications(1, 20),
    refetchInterval: 30_000,
  });

  const markReadMutation = useMutation({
    mutationFn: markNotificationRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  const markAllReadMutation = useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  const notifications = notificationsData?.items ?? [];
  const hasUnread = notifications.some((n) => !n.is_read);

  return (
    <Popover open={open} onOpenChange={onOpenChange}>
      <PopoverTrigger asChild>{children}</PopoverTrigger>
      <PopoverContent
        align="end"
        side="right"
        className="w-80 p-0"
      >
        <div className="flex items-center justify-between px-3 py-2 border-b">
          <span className="text-sm font-semibold">Notifications</span>
          {hasUnread && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-xs gap-1"
              onClick={() => markAllReadMutation.mutate()}
              disabled={markAllReadMutation.isPending}
            >
              <CheckCheck className="size-3.5" />
              Mark all read
            </Button>
          )}
        </div>
        <div className="max-h-80 overflow-y-auto">
          {notifications.length === 0 ? (
            <div className="px-3 py-6 text-center text-sm text-muted-foreground">
              No notifications
            </div>
          ) : (
            notifications.map((notification) => (
              <NotificationItem
                key={notification.id}
                notification={notification}
                onMarkRead={(id) => markReadMutation.mutate(id)}
              />
            ))
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
}
