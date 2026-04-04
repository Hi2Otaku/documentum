import { Play, Pause, CheckCircle, XCircle, Clock } from 'lucide-react';
import { Card, CardContent } from '../ui/card';
import { Skeleton } from '../ui/skeleton';
import type { KpiMetrics } from '../../api/dashboard';

interface KpiCardsProps {
  kpi: KpiMetrics | null;
  loading?: boolean;
}

interface KpiCardDef {
  key: keyof Omit<KpiMetrics, 'avg_completion_hours'> | 'avg_completion_hours';
  label: string;
  borderColor: string;
  valueColor: string;
  icon: React.ReactNode;
  format?: (value: number) => string;
}

const kpiDefs: KpiCardDef[] = [
  {
    key: 'running',
    label: 'Running',
    borderColor: 'border-green-500',
    valueColor: 'text-green-600',
    icon: <Play className="h-4 w-4 text-muted-foreground" />,
  },
  {
    key: 'halted',
    label: 'Halted',
    borderColor: 'border-amber-500',
    valueColor: 'text-amber-600',
    icon: <Pause className="h-4 w-4 text-muted-foreground" />,
  },
  {
    key: 'finished',
    label: 'Finished',
    borderColor: 'border-blue-500',
    valueColor: 'text-blue-600',
    icon: <CheckCircle className="h-4 w-4 text-muted-foreground" />,
  },
  {
    key: 'failed',
    label: 'Failed',
    borderColor: 'border-red-500',
    valueColor: 'text-red-600',
    icon: <XCircle className="h-4 w-4 text-muted-foreground" />,
  },
  {
    key: 'avg_completion_hours',
    label: 'Avg Completion',
    borderColor: 'border-primary',
    valueColor: 'text-foreground',
    icon: <Clock className="h-4 w-4 text-muted-foreground" />,
    format: (v: number) => `${v.toFixed(1)} hrs`,
  },
];

export function KpiCards({ kpi, loading }: KpiCardsProps) {
  if (loading || !kpi) {
    return (
      <div className="flex gap-4 flex-wrap">
        {kpiDefs.map((def) => (
          <Card key={def.key} className={`flex-1 min-w-[180px] border-l-4 ${def.borderColor}`}>
            <CardContent className="p-4">
              <div className="flex items-center gap-1 mb-2">
                <Skeleton className="h-4 w-4 rounded" />
                <Skeleton className="h-4 w-16" />
              </div>
              <Skeleton className="h-8 w-[60%]" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  return (
    <div className="flex gap-4 flex-wrap">
      {kpiDefs.map((def) => {
        const rawValue = kpi[def.key as keyof KpiMetrics];
        const displayValue = def.format
          ? def.format(rawValue)
          : String(rawValue);

        return (
          <Card
            key={def.key}
            className={`flex-1 min-w-[180px] border-l-4 ${def.borderColor}`}
            role="status"
            aria-live="polite"
            aria-label={`${def.label}: ${displayValue}`}
          >
            <CardContent className="p-4">
              <div className="flex items-center gap-1 mb-2">
                {def.icon}
                <span className="text-sm text-muted-foreground">{def.label}</span>
              </div>
              <div className={`text-3xl font-bold ${def.valueColor}`}>
                {displayValue}
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
