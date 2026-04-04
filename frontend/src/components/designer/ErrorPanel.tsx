import type { ValidationErrorDetail } from '../../types/workflow';

/** Error panel -- stub for Task 1, full implementation in Task 2 */
interface ErrorPanelProps {
  errors: ValidationErrorDetail[];
  onErrorClick: (entityId: string) => void;
}

export function ErrorPanel({ errors }: ErrorPanelProps) {
  if (errors.length === 0) return null;
  return (
    <div className="border-t bg-muted px-4 py-2">
      <span className="text-sm text-muted-foreground">Errors ({errors.length})</span>
    </div>
  );
}
