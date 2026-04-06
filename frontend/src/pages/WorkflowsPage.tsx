import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { Button } from "../components/ui/button";
import { WorkflowTable } from "../components/workflows/WorkflowTable";
import { WorkflowDetailPanel } from "../components/workflows/WorkflowDetailPanel";
import { StartWorkflowDialog } from "../components/workflows/StartWorkflowDialog";
import {
  fetchWorkflows,
  fetchWorkflowsAdmin,
} from "../api/workflows";
import { useAuthStore } from "../stores/authStore";

const PAGE_SIZE = 20;

function authHeaders(): HeadersInit {
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function apiFetchGeneric<T>(url: string): Promise<T> {
  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

interface TemplateListItem {
  id: string;
  name: string;
  state: string;
}

export function WorkflowsPage() {
  const isSuperuser = useAuthStore((s) => s.isSuperuser);
  const userId = useAuthStore((s) => s.userId) ?? "";

  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string | null>(
    null,
  );
  const [templateFilter, setTemplateFilter] = useState("all");
  const [stateFilter, setStateFilter] = useState("all");
  const [currentPage, setCurrentPage] = useState(1);
  const [wizardOpen, setWizardOpen] = useState(false);

  // Fetch templates for filter dropdown
  const { data: templatesData } = useQuery({
    queryKey: ["templates"],
    queryFn: () =>
      apiFetchGeneric<{ data: TemplateListItem[] }>("/api/v1/templates/"),
  });

  const installedTemplates = (templatesData?.data ?? [])
    .filter((t) => t.state === "active")
    .map((t) => ({ id: t.id, name: t.name }));

  // Fetch workflows -- admin or regular user
  const adminQuery = useQuery({
    queryKey: [
      "workflows",
      {
        page: currentPage,
        state: stateFilter === "all" ? undefined : stateFilter,
        templateId: templateFilter === "all" ? undefined : templateFilter,
      },
    ],
    queryFn: () =>
      fetchWorkflowsAdmin({
        skip: (currentPage - 1) * PAGE_SIZE,
        limit: PAGE_SIZE,
        state: stateFilter === "all" ? undefined : stateFilter,
        template_id: templateFilter === "all" ? undefined : templateFilter,
      }),
    enabled: isSuperuser,
  });

  const userQuery = useQuery({
    queryKey: ["workflows", { page: currentPage }],
    queryFn: () =>
      fetchWorkflows({
        skip: (currentPage - 1) * PAGE_SIZE,
        limit: PAGE_SIZE,
      }),
    enabled: !isSuperuser,
  });

  const activeQuery = isSuperuser ? adminQuery : userQuery;
  const isLoading = activeQuery.isLoading;

  let workflows = activeQuery.data?.data ?? [];
  const totalPages = activeQuery.data?.meta?.total_pages ?? 1;

  // Client-side filter for regular users
  if (!isSuperuser) {
    workflows = workflows.filter((w) => w.supervisor_id === userId);
  }

  function handleTemplateFilterChange(v: string) {
    setTemplateFilter(v);
    setCurrentPage(1);
    setSelectedWorkflowId(null);
  }

  function handleStateFilterChange(v: string) {
    setStateFilter(v);
    setCurrentPage(1);
    setSelectedWorkflowId(null);
  }

  function handlePageChange(page: number) {
    setCurrentPage(page);
    setSelectedWorkflowId(null);
  }

  return (
    <div className="h-full flex flex-col px-4 pt-4">
      {/* Toolbar */}
      <div className="flex items-center justify-between h-12 mb-2">
        <Button onClick={() => setWizardOpen(true)}>
          <Plus className="w-4 h-4 mr-2" /> Start Workflow
        </Button>
      </div>

      {/* Split pane */}
      <div className="flex h-[calc(100vh-theme(spacing.16)-96px)]">
        {/* Left: Workflow table */}
        <div className="flex-1 min-w-[400px] flex flex-col overflow-hidden">
          <WorkflowTable
            workflows={workflows}
            isLoading={isLoading}
            selectedId={selectedWorkflowId}
            onSelectWorkflow={setSelectedWorkflowId}
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={handlePageChange}
            templateFilter={templateFilter}
            onTemplateFilterChange={handleTemplateFilterChange}
            stateFilter={stateFilter}
            onStateFilterChange={handleStateFilterChange}
            templates={installedTemplates}
            isSuperuser={isSuperuser}
            currentUserId={userId}
          />
        </div>
        {/* Right: Detail panel */}
        <div className="w-[420px] border-l overflow-y-auto hidden lg:block">
          <WorkflowDetailPanel workflowId={selectedWorkflowId} />
        </div>
      </div>

      <StartWorkflowDialog open={wizardOpen} onOpenChange={setWizardOpen} />
    </div>
  );
}
