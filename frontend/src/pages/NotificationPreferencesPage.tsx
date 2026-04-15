import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Bell, Loader2, CheckCircle2 } from "lucide-react";
import { Button } from "../components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../components/ui/card";
import { Label } from "../components/ui/label";
import { Switch } from "../components/ui/switch";
import { Separator } from "../components/ui/separator";
import {
  fetchNotificationPreferences,
  updateNotificationPreferences,
} from "../api/notifications";
import type { NotificationPreference } from "../api/notifications";

/** Human-readable labels and descriptions for each notification type. */
const TYPE_META: Record<string, { label: string; description: string }> = {
  "work_item.assigned": {
    label: "Work Item Assigned",
    description: "When a new work item is assigned to you or your group.",
  },
  "work_item.delegated": {
    label: "Work Item Delegated",
    description:
      "When a work item is delegated to you by another user.",
  },
  deadline_approaching: {
    label: "Deadline Approaching",
    description: "When a task deadline is approaching soon.",
  },
  deadline_escalated: {
    label: "Deadline Escalated",
    description:
      "When a task deadline has passed and the item is escalated.",
  },
  "workflow.failed": {
    label: "Workflow Failed",
    description: "When a workflow you started encounters an error.",
  },
};

export function NotificationPreferencesPage() {
  const queryClient = useQueryClient();

  const { data: serverPrefs, isLoading } = useQuery({
    queryKey: ["notification-preferences"],
    queryFn: fetchNotificationPreferences,
  });

  const [localPrefs, setLocalPrefs] = useState<NotificationPreference[]>([]);
  const [saved, setSaved] = useState(false);

  // Sync server data into local state
  useEffect(() => {
    if (serverPrefs) {
      setLocalPrefs(serverPrefs);
      setSaved(false);
    }
  }, [serverPrefs]);

  const mutation = useMutation({
    mutationFn: updateNotificationPreferences,
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["notification-preferences"],
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    },
  });

  function handleToggle(notificationType: string, enabled: boolean) {
    setLocalPrefs((prev) =>
      prev.map((p) =>
        p.notification_type === notificationType ? { ...p, enabled } : p,
      ),
    );
    setSaved(false);
  }

  function handleSave() {
    mutation.mutate({ preferences: localPrefs });
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="p-6 max-w-2xl">
      {/* Header */}
      <div className="flex items-center gap-3 mb-2">
        <Bell className="h-6 w-6 text-primary" />
        <h1 className="text-2xl font-bold">Notification Preferences</h1>
      </div>
      <p className="text-muted-foreground mb-6">
        Configure which event types trigger notifications for your account.
      </p>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Event Types</CardTitle>
        </CardHeader>
        <CardContent className="space-y-1">
          {localPrefs.map((pref, idx) => {
            const meta = TYPE_META[pref.notification_type];
            return (
              <div key={pref.notification_type}>
                {idx > 0 && <Separator className="my-3" />}
                <div className="flex items-center justify-between py-2">
                  <div className="space-y-0.5">
                    <Label className="text-sm font-medium">
                      {meta?.label ?? pref.notification_type}
                    </Label>
                    <p className="text-xs text-muted-foreground">
                      {meta?.description ?? ""}
                    </p>
                  </div>
                  <Switch
                    checked={pref.enabled}
                    onCheckedChange={(checked: boolean) =>
                      handleToggle(pref.notification_type, checked)
                    }
                  />
                </div>
              </div>
            );
          })}
        </CardContent>
      </Card>

      <div className="flex items-center gap-3 mt-4">
        <Button
          onClick={handleSave}
          disabled={mutation.isPending}
        >
          {mutation.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Saving...
            </>
          ) : (
            "Save Preferences"
          )}
        </Button>
        {saved && (
          <span className="flex items-center gap-1 text-sm text-green-600">
            <CheckCircle2 className="h-4 w-4" />
            Saved
          </span>
        )}
        {mutation.isError && (
          <span className="text-sm text-destructive">
            Failed to save. Please try again.
          </span>
        )}
      </div>
    </div>
  );
}
