import { useQuery } from "@tanstack/react-query";
import { Avatar, AvatarFallback } from "../ui/avatar";
import { Badge } from "../ui/badge";
import { Separator } from "../ui/separator";
import { Skeleton } from "../ui/skeleton";
import { fetchQueueDetail } from "../../api/queues";

interface QueueDetailPanelProps {
  queueId: string | null;
}

export function QueueDetailPanel({ queueId }: QueueDetailPanelProps) {
  const { data: queue, isLoading } = useQuery({
    queryKey: ["queues", queueId],
    queryFn: () => fetchQueueDetail(queueId!),
    enabled: !!queueId,
  });

  // No selection state
  if (!queueId) {
    return (
      <div className="flex flex-col items-center justify-center h-full">
        <h3 className="text-lg font-semibold">Select a queue</h3>
        <p className="text-sm text-muted-foreground mt-1">
          Click a queue from the list to view its details.
        </p>
      </div>
    );
  }

  // Loading state
  if (isLoading || !queue) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-6 w-48" />
        <Separator />
        <div className="space-y-2">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      {/* Header */}
      <div className="p-6">
        <h2 className="text-base font-semibold">{queue.name}</h2>
        {queue.description && (
          <p className="text-sm text-muted-foreground mt-1">
            {queue.description}
          </p>
        )}
      </div>

      <Separator />

      {/* Members section */}
      <div className="p-6">
        <div className="flex items-center gap-2 mb-3">
          <h3 className="text-sm font-semibold">Members</h3>
          <Badge variant="secondary">{queue.members.length}</Badge>
        </div>

        {queue.members.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No members in this queue.
          </p>
        ) : (
          <div className="space-y-2">
            {queue.members.map((member) => (
              <div key={member.id} className="flex items-center gap-3">
                <Avatar className="h-7 w-7">
                  <AvatarFallback className="text-xs">
                    {member.username.slice(0, 2).toUpperCase()}
                  </AvatarFallback>
                </Avatar>
                <div className="min-w-0">
                  <div className="text-sm">{member.username}</div>
                  {member.email && (
                    <div className="text-xs text-muted-foreground">
                      {member.email}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Info message */}
      <div className="px-6 pb-6">
        <p className="text-xs text-muted-foreground italic">
          Queue work items appear as available items in your My Inbox tab.
        </p>
      </div>
    </div>
  );
}
