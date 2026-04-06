import type React from "react";

interface InboxEmptyStateProps {
  heading: string;
  body: string;
  action?: React.ReactNode;
}

export function InboxEmptyState({ heading, body, action }: InboxEmptyStateProps) {
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
