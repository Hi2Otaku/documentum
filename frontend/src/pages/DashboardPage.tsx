import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router';
import { fetchDashboardMetrics, listTemplatesForFilter } from '../api/dashboard';
import { useDashboardSSE } from '../hooks/useDashboardSSE';
import { KpiCards } from '../components/dashboard/KpiCards';
import { BottleneckChart } from '../components/dashboard/BottleneckChart';
import { WorkloadChart } from '../components/dashboard/WorkloadChart';
import { SlaChart } from '../components/dashboard/SlaChart';
import { Select } from '../components/ui/select';
import { Separator } from '../components/ui/separator';
import { Skeleton } from '../components/ui/skeleton';
import { Button } from '../components/ui/button';

export function DashboardPage() {
  const [templateId, setTemplateId] = useState<string | undefined>(undefined);

  // Fetch template list for filter dropdown
  const { data: templates } = useQuery({
    queryKey: ['templates'],
    queryFn: listTemplatesForFilter,
    staleTime: 30_000,
  });

  // Fetch initial metrics (chart data)
  const {
    data: metrics,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['dashboard', 'metrics', templateId],
    queryFn: () => fetchDashboardMetrics(templateId),
    staleTime: 30_000,
  });

  // SSE for live KPI updates
  const { metrics: sseMetrics, status: sseStatus } = useDashboardSSE(templateId);

  // Use SSE metrics for KPI cards if available, otherwise fall back to fetched data
  const kpiData = sseMetrics ?? metrics?.kpi ?? null;

  // SSE connection indicator
  const statusDot = {
    connected: 'bg-green-500',
    reconnecting: 'bg-amber-500',
    disconnected: 'bg-red-500',
  }[sseStatus];

  const statusLabel = {
    connected: 'Live',
    reconnecting: 'Reconnecting...',
    disconnected: 'Offline',
  }[sseStatus];

  // Template filter options
  const templateOptions = (templates ?? []).map((t) => ({
    value: t.id,
    label: `${t.name} (v${t.version})`,
  }));

  return (
    <div className="max-w-[1200px] mx-auto p-8">
      {/* Header row */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-lg font-bold">Dashboard</h1>

        <div className="flex items-center gap-4">
          {/* SSE connection indicator */}
          <div className="flex items-center gap-1.5" aria-live="polite">
            <span className={`inline-block h-1.5 w-1.5 rounded-full ${statusDot}`} />
            <span className="text-sm text-muted-foreground">{statusLabel}</span>
          </div>

          {/* Template filter */}
          <Select
            options={templateOptions}
            placeholder="All Templates"
            value={templateId ?? ''}
            onChange={(e) =>
              setTemplateId(e.target.value || undefined)
            }
            className="w-[220px]"
          />
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="text-center py-12">
          <p className="text-destructive mb-4">
            Failed to load dashboard metrics. Check your connection and try again.
          </p>
          <Button variant="outline" onClick={() => refetch()}>
            Retry
          </Button>
        </div>
      )}

      {/* Empty state: no workflow data */}
      {!isLoading && !error && metrics && !metrics.kpi.running && !metrics.kpi.halted && !metrics.kpi.finished && !metrics.kpi.failed && metrics.bottleneck_activities.length === 0 && (
        <div className="text-center py-12">
          <h2 className="text-lg font-semibold mb-2">No workflow data</h2>
          <p className="text-muted-foreground mb-4">
            Start a workflow from an installed template to see metrics here.
          </p>
          <Button variant="outline" asChild>
            <Link to="/templates">Go to Templates</Link>
          </Button>
        </div>
      )}

      {/* KPI Cards */}
      <KpiCards kpi={kpiData} loading={isLoading} />

      <Separator className="my-6" />

      {/* Chart row: two-column grid */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 mb-6">
        {isLoading ? (
          <>
            <div className="rounded-xl border bg-card p-6">
              <Skeleton className="h-5 w-40 mb-4" />
              <Skeleton className="h-[300px]" />
            </div>
            <div className="rounded-xl border bg-card p-6">
              <Skeleton className="h-5 w-40 mb-4" />
              <Skeleton className="h-[300px]" />
            </div>
          </>
        ) : (
          <>
            <BottleneckChart data={metrics?.bottleneck_activities ?? []} />
            <WorkloadChart data={metrics?.workload ?? []} />
          </>
        )}
      </div>

      {/* SLA section: full width */}
      {isLoading ? (
        <div className="rounded-xl border bg-card p-6">
          <Skeleton className="h-5 w-32 mb-4" />
          <Skeleton className="h-[200px]" />
        </div>
      ) : (
        <SlaChart data={metrics?.sla_compliance ?? []} />
      )}
    </div>
  );
}
