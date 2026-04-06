import { useQuery } from "@tanstack/react-query";
import { Badge } from "../ui/badge";
import { Skeleton } from "../ui/skeleton";
import { InboxEmptyState } from "./InboxEmptyState";
import { fetchQueues } from "../../api/queues";
import { cn } from "../../lib/utils";

interface QueueListProps {
  selectedQueueId: string | null;
  onSelectQueue: (id: string) => void;
}

export function QueueList({ selectedQueueId, onSelectQueue }: QueueListProps) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["queues"],
    queryFn: () => fetchQueues(),
  });

  if (isLoading) {
    return (
      <div className="space-y-0">
        {[1, 2, 3].map((i) => (
          <div key={i} className="px-4 py-3 border-b">
            <Skeleton className="h-[48px] w-full" />
          </div>
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <InboxEmptyState
        heading="No queues"
        body="You are not a member of any work queues. Contact an administrator to be added to a queue."
      />
    );
  }

  const queues = data?.data ?? [];

  if (queues.length === 0) {
    return (
      <InboxEmptyState
        heading="No queues"
        body="You are not a member of any work queues. Contact an administrator to be added to a queue."
      />
    );
  }

  return (
    <div className="overflow-y-auto">
      {queues.map((queue) => {
        const isSelected = queue.id === selectedQueueId;
        return (
          <div
            key={queue.id}
            className={cn(
              "flex items-center justify-between px-4 py-3 border-b cursor-pointer",
              isSelected
                ? "bg-accent border-l-[3px] border-primary"
                : "hover:bg-accent/50",
            )}
            onClick={() => onSelectQueue(queue.id)}
          >
            <div className="min-w-0 flex-1">
              <div className="text-sm font-semibold truncate">{queue.name}</div>
              {queue.description && (
                <div className="text-xs text-muted-foreground truncate">
                  {queue.description}
                </div>
              )}
            </div>
            <Badge variant="secondary" className="ml-2 shrink-0">
              {queue.member_count}
            </Badge>
          </div>
        );
      })}
    </div>
  );
}
