import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { InboxTable } from "../components/inbox/InboxTable";
import { InboxDetailPanel } from "../components/inbox/InboxDetailPanel";
import { QueueList } from "../components/inbox/QueueList";
import { QueueDetailPanel } from "../components/inbox/QueueDetailPanel";
import { fetchInboxItems } from "../api/inbox";

const PAGE_SIZE = 20;

export function InboxPage() {
  const [activeTab, setActiveTab] = useState<"inbox" | "queues">("inbox");
  const [selectedWorkItemId, setSelectedWorkItemId] = useState<string | null>(null);
  const [stateFilter, setStateFilter] = useState<string>("all");
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedQueueId, setSelectedQueueId] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: [
      "inbox",
      { state: stateFilter === "all" ? undefined : stateFilter, skip: (currentPage - 1) * PAGE_SIZE, limit: PAGE_SIZE },
    ],
    queryFn: () =>
      fetchInboxItems({
        state: stateFilter === "all" ? undefined : stateFilter,
        skip: (currentPage - 1) * PAGE_SIZE,
        limit: PAGE_SIZE,
      }),
  });

  const items = data?.data ?? [];
  const totalPages = data?.meta?.total_pages ?? 1;

  function handleStateFilterChange(state: string) {
    setStateFilter(state);
    setCurrentPage(1);
    setSelectedWorkItemId(null);
  }

  function handlePageChange(page: number) {
    setCurrentPage(page);
    setSelectedWorkItemId(null);
  }

  function handleTabChange(tab: string) {
    setActiveTab(tab as "inbox" | "queues");
    setSelectedQueueId(null);
  }

  return (
    <div className="h-full flex flex-col">
      <Tabs
        value={activeTab}
        onValueChange={handleTabChange}
        className="flex flex-col h-full"
      >
        <div className="px-4 pt-2">
          <TabsList>
            <TabsTrigger value="inbox">My Inbox</TabsTrigger>
            <TabsTrigger value="queues">Queues</TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="inbox" className="flex-1 mt-0 overflow-hidden">
          <div className="flex h-[calc(100vh-theme(spacing.16))]">
            {/* Left pane: table */}
            <div className="flex-1 min-w-[400px] flex flex-col overflow-hidden">
              <InboxTable
                items={items}
                isLoading={isLoading}
                selectedId={selectedWorkItemId}
                onSelectItem={setSelectedWorkItemId}
                currentPage={currentPage}
                totalPages={totalPages}
                onPageChange={handlePageChange}
                stateFilter={stateFilter}
                onStateFilterChange={handleStateFilterChange}
              />
            </div>
            {/* Right pane: detail */}
            <div className="w-[420px] border-l overflow-y-auto hidden lg:block">
              <InboxDetailPanel workItemId={selectedWorkItemId} />
            </div>
          </div>
        </TabsContent>

        <TabsContent value="queues" className="flex-1 mt-0 overflow-hidden">
          <div className="flex h-[calc(100vh-theme(spacing.16))]">
            {/* Left pane: queue list */}
            <div className="flex-1 min-w-[400px] flex flex-col overflow-hidden">
              <QueueList
                selectedQueueId={selectedQueueId}
                onSelectQueue={setSelectedQueueId}
              />
            </div>
            {/* Right pane: queue detail */}
            <div className="w-[420px] border-l overflow-y-auto hidden lg:block">
              <QueueDetailPanel queueId={selectedQueueId} />
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
