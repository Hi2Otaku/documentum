import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent } from "../ui/card";
import { Separator } from "../ui/separator";
import { Skeleton } from "../ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../ui/tabs";
import { WorkflowStateBadge } from "./WorkflowStateBadge";
import { AdminActionBar } from "./AdminActionBar";
import { TerminateDialog } from "./TerminateDialog";
import { WorkflowVariablesList } from "./WorkflowVariablesList";
import { WorkflowProgressGraph } from "./WorkflowProgressGraph";
import { fetchWorkflowDetail } from "../../api/workflows";

interface WorkflowDetailPanelProps {
  workflowId: string | null;
}

export function WorkflowDetailPanel({ workflowId }: WorkflowDetailPanelProps) {
  const [terminateDialogOpen, setTerminateDialogOpen] = useState(false);

  const { data: workflow, isLoading } = useQuery({
    queryKey: ["workflows", workflowId],
    queryFn: () => fetchWorkflowDetail(workflowId!),
    enabled: !!workflowId,
  });

  // No selection state
  if (!workflowId) {
    return (
      <div className="flex flex-col items-center justify-center h-full">
        <h3 className="text-lg font-semibold">Select a workflow</h3>
        <p className="text-sm text-muted-foreground mt-1">
          Click a row in the table to view its details.
        </p>
      </div>
    );
  }

  // Loading state
  if (isLoading || !workflow) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-6 w-[60%]" />
        <Card>
          <CardContent className="p-4 space-y-3">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
          </CardContent>
        </Card>
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-8 w-32" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      {/* Header */}
      <div className="p-6 pb-3">
        <div className="flex items-center gap-2">
          <h2 className="text-base font-semibold">
            {workflow.process_template_id.slice(0, 8)}
          </h2>
          <WorkflowStateBadge state={workflow.state} />
        </div>
      </div>

      {/* Admin Actions */}
      <div className="px-6 pb-3">
        <AdminActionBar
          workflowId={workflowId}
          workflowState={workflow.state}
          onTerminateClick={() => setTerminateDialogOpen(true)}
        />
        <TerminateDialog
          open={terminateDialogOpen}
          onOpenChange={setTerminateDialogOpen}
          workflowId={workflowId}
        />
      </div>

      <div className="px-6">
        <Separator />
      </div>

      {/* Tabs */}
      <div className="px-6 pt-4 flex-1">
        <Tabs defaultValue="details">
          <TabsList>
            <TabsTrigger value="details">Details</TabsTrigger>
            <TabsTrigger value="progress">Progress</TabsTrigger>
          </TabsList>

          <TabsContent value="details" className="mt-4 space-y-4">
            {/* Metadata Card */}
            <Card>
              <CardContent className="p-4">
                <div className="grid grid-cols-2 gap-y-3">
                  <span className="text-xs text-muted-foreground">
                    Template
                  </span>
                  <span className="text-sm">
                    {workflow.process_template_id.slice(0, 8)}
                  </span>

                  <span className="text-xs text-muted-foreground">
                    Started By
                  </span>
                  <span className="text-sm">
                    {workflow.supervisor_id?.slice(0, 8) ?? "\u2014"}
                  </span>

                  <span className="text-xs text-muted-foreground">
                    Started
                  </span>
                  <span className="text-sm">
                    {workflow.started_at
                      ? new Date(workflow.started_at).toLocaleString()
                      : "\u2014"}
                  </span>

                  <span className="text-xs text-muted-foreground">
                    Completed
                  </span>
                  <span className="text-sm">
                    {workflow.completed_at
                      ? new Date(workflow.completed_at).toLocaleString()
                      : "\u2014"}
                  </span>
                </div>
              </CardContent>
            </Card>

            <Separator className="my-4" />

            {/* Process Variables */}
            <div>
              <h3 className="text-base font-semibold mb-3">
                Process Variables
              </h3>
              <WorkflowVariablesList
                variables={workflow.process_variables}
              />
            </div>
          </TabsContent>

          <TabsContent value="progress" className="mt-4">
            <WorkflowProgressGraph workflowId={workflowId!} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
