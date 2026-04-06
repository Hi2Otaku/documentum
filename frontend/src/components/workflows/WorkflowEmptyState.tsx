export function WorkflowEmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      <h3 className="text-base font-semibold text-foreground">No workflows</h3>
      <p className="text-sm text-muted-foreground mt-2 text-center max-w-sm">
        No workflow instances found. Click &quot;Start Workflow&quot; to launch a new one.
      </p>
    </div>
  );
}
