interface DocumentEmptyStateProps {
  heading?: string;
  body?: string;
  action?: React.ReactNode;
}

export function DocumentEmptyState({
  heading = "No documents",
  body = "No documents have been uploaded yet. Drag files to the upload area above or click Browse to get started.",
  action,
}: DocumentEmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      <h3 className="text-lg font-semibold text-foreground">{heading}</h3>
      <p className="text-sm text-muted-foreground mt-2 text-center max-w-sm">
        {body}
      </p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
