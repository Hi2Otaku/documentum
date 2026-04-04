import { CircleX, CheckCircle, ChevronDown, ChevronUp } from 'lucide-react';
import { useUiStore } from '../../stores/uiStore';
import type { ValidationErrorDetail } from '../../types/workflow';

interface ErrorPanelProps {
  errors: ValidationErrorDetail[];
  onErrorClick: (entityId: string) => void;
}

export function ErrorPanel({ errors, onErrorClick }: ErrorPanelProps) {
  const errorPanelExpanded = useUiStore((s) => s.errorPanelExpanded);
  const setErrorPanelExpanded = useUiStore((s) => s.setErrorPanelExpanded);

  return (
    <div className="border-t shrink-0">
      {/* Header */}
      <button
        onClick={() => setErrorPanelExpanded(!errorPanelExpanded)}
        className="flex w-full items-center justify-between bg-muted px-4 py-2 text-sm font-medium hover:bg-muted/80 transition-colors"
        aria-label={errorPanelExpanded ? 'Collapse error panel' : 'Expand error panel'}
      >
        <span>
          Errors ({errors.length})
        </span>
        {errorPanelExpanded ? (
          <ChevronDown className="w-4 h-4" />
        ) : (
          <ChevronUp className="w-4 h-4" />
        )}
      </button>

      {/* Expanded error list */}
      {errorPanelExpanded && (
        <div className="max-h-[200px] overflow-y-auto bg-background px-4 py-2">
          {errors.length === 0 ? (
            <div className="flex items-center gap-2 py-2 text-sm text-green-600">
              <CheckCircle className="w-4 h-4" />
              <span>Validation passed</span>
            </div>
          ) : (
            <ul role="list" className="space-y-1">
              {errors.map((error, index) => (
                <li
                  key={index}
                  role="listitem"
                  onClick={() =>
                    error.entity_id && onErrorClick(error.entity_id)
                  }
                  className="flex items-start gap-2 py-1.5 px-2 rounded cursor-pointer hover:bg-muted/50 transition-colors"
                >
                  <CircleX className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
                  <span className="text-sm text-red-700">{error.message}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
