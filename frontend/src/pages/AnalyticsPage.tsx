import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { RefreshCw, TrendingUp, Clock, Route, Zap } from "lucide-react";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import {
  fetchSummary,
  fetchPaths,
  fetchCycleTimes,
  fetchBottlenecks,
  triggerRefresh,
  analyticsKeys,
} from "../api/analytics";
import type {
  CycleTimeStats,
  BottleneckActivity,
} from "../api/analytics";
import { handle401 } from "../api/handle401";

// --- Helpers ---

function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null || isNaN(seconds)) return "N/A";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) {
    const m = Math.floor(seconds / 60);
    const s = Math.round(seconds % 60);
    return `${m}m ${s}s`;
  }
  const h = Math.floor(seconds / 3600);
  const m = Math.round((seconds % 3600) / 60);
  return `${h}h ${m}m`;
}

function pctColor(pct: number): string {
  if (pct < 20) return "#22c55e"; // green
  if (pct < 40) return "#84cc16"; // lime
  if (pct < 60) return "#eab308"; // yellow
  if (pct < 80) return "#f97316"; // orange
  return "#ef4444"; // red
}

interface TemplateOption {
  id: string;
  name: string;
}

// --- Custom Tooltip for Cycle Time ---

function CycleTimeTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: CycleTimeStats }> }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-white border rounded-md shadow-md p-3 text-sm">
      <p className="font-medium">{d.activity_name ?? d.template_name ?? "Unknown"}</p>
      <p>Avg: {formatDuration(d.avg_seconds)}</p>
      <p>Median: {formatDuration(d.median_seconds)}</p>
      <p>Min: {formatDuration(d.min_seconds)}</p>
      <p>Max: {formatDuration(d.max_seconds)}</p>
      <p>Samples: {d.sample_count}</p>
    </div>
  );
}

// --- Custom Tooltip for Bottleneck ---

function BottleneckTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: BottleneckActivity }> }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-white border rounded-md shadow-md p-3 text-sm">
      <p className="font-medium">{d.activity_name}</p>
      <p>Template: {d.template_name}</p>
      <p>Avg Duration: {formatDuration(d.avg_duration_seconds)}</p>
      <p>Executions: {d.total_executions}</p>
      <p>% of Total: {d.pct_of_total_time.toFixed(1)}%</p>
    </div>
  );
}

// --- Component ---

export function AnalyticsPage() {
  const queryClient = useQueryClient();
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | undefined>(undefined);
  const [cycleTimeGroupBy, setCycleTimeGroupBy] = useState<"activity" | "template">("activity");

  // Fetch template list for filter
  const templatesQuery = useQuery<TemplateOption[]>({
    queryKey: ["templates-list"],
    queryFn: async () => {
      const res = await fetch("/api/v1/templates", {
        headers: {
          "Content-Type": "application/json",
          ...(localStorage.getItem("token")
            ? { Authorization: `Bearer ${localStorage.getItem("token")}` }
            : {}),
        },
      });
      if (res.status === 401) handle401();
      if (!res.ok) throw new Error("Failed to fetch templates");
      const json = await res.json();
      const items = json.data ?? json;
      return (Array.isArray(items) ? items : []).map((t: { id: string; name: string }) => ({
        id: t.id,
        name: t.name,
      }));
    },
  });

  // Analytics queries
  const summaryQuery = useQuery({
    queryKey: analyticsKeys.summary,
    queryFn: fetchSummary,
    refetchInterval: 60_000,
  });

  const pathsQuery = useQuery({
    queryKey: analyticsKeys.paths(selectedTemplateId),
    queryFn: () => fetchPaths(selectedTemplateId, 20),
  });

  const cycleTimesQuery = useQuery({
    queryKey: analyticsKeys.cycleTimes(selectedTemplateId, cycleTimeGroupBy),
    queryFn: () => fetchCycleTimes(selectedTemplateId, cycleTimeGroupBy),
  });

  const bottlenecksQuery = useQuery({
    queryKey: analyticsKeys.bottlenecks(selectedTemplateId),
    queryFn: () => fetchBottlenecks(selectedTemplateId, 10),
  });

  // Refresh mutation
  const refreshMutation = useMutation({
    mutationFn: triggerRefresh,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["analytics"] });
    },
  });

  const summary = summaryQuery.data;
  const paths = pathsQuery.data;
  const cycleTimes = cycleTimesQuery.data;
  const bottlenecks = bottlenecksQuery.data;

  return (
    <div className="p-6 space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-muted-foreground" />
          <h1 className="text-lg font-semibold">Process Analytics</h1>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => refreshMutation.mutate()}
          disabled={refreshMutation.isPending}
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${refreshMutation.isPending ? "animate-spin" : ""}`} />
          {refreshMutation.isPending ? "Refreshing..." : "Refresh Now"}
        </Button>
      </div>

      {/* Section 1: Summary cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-2 mb-1">
              <Route className="h-4 w-4 text-muted-foreground" />
              <p className="text-xs text-muted-foreground">Total Instances</p>
            </div>
            <p className="text-2xl font-bold">
              {summaryQuery.isLoading ? "..." : (summary?.total_instances ?? 0)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-2 mb-1">
              <Zap className="h-4 w-4 text-muted-foreground" />
              <p className="text-xs text-muted-foreground">Completed</p>
            </div>
            <p className="text-2xl font-bold">
              {summaryQuery.isLoading ? "..." : (summary?.completed_instances ?? 0)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-2 mb-1">
              <Clock className="h-4 w-4 text-muted-foreground" />
              <p className="text-xs text-muted-foreground">Avg Completion Time</p>
            </div>
            <p className="text-2xl font-bold">
              {summaryQuery.isLoading ? "..." : formatDuration(summary?.avg_completion_seconds)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-2 mb-1">
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
              <p className="text-xs text-muted-foreground">Paths Discovered</p>
            </div>
            <p className="text-2xl font-bold">
              {summaryQuery.isLoading ? "..." : (summary?.paths_discovered ?? 0)}
            </p>
          </CardContent>
        </Card>
      </div>

      {summary?.last_refreshed && (
        <p className="text-xs text-muted-foreground">
          Last refreshed: {new Date(summary.last_refreshed).toLocaleString()}
        </p>
      )}

      {/* Section 2: Template filter */}
      <div className="flex items-center gap-3">
        <span className="text-sm font-medium">Filter by Template:</span>
        <Select
          value={selectedTemplateId ?? "__all__"}
          onValueChange={(v) => setSelectedTemplateId(v === "__all__" ? undefined : v)}
        >
          <SelectTrigger className="w-[280px]">
            <SelectValue placeholder="All Templates" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__all__">All Templates</SelectItem>
            {(templatesQuery.data ?? []).map((t) => (
              <SelectItem key={t.id} value={t.id}>
                {t.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Section 3: Execution Paths */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <Route className="h-4 w-4" />
            Execution Paths
          </CardTitle>
        </CardHeader>
        <CardContent>
          {pathsQuery.isLoading && (
            <p className="text-sm text-muted-foreground">Loading execution paths...</p>
          )}
          {pathsQuery.isError && (
            <p className="text-sm text-destructive">Failed to load execution paths.</p>
          )}
          {paths && paths.length === 0 && (
            <p className="text-sm text-muted-foreground">No execution paths discovered yet.</p>
          )}
          {paths && paths.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left">
                    <th className="py-2 px-3 font-medium text-muted-foreground">Path</th>
                    <th className="py-2 px-3 font-medium text-muted-foreground text-right">Frequency</th>
                    <th className="py-2 px-3 font-medium text-muted-foreground text-right">Avg Duration</th>
                  </tr>
                </thead>
                <tbody>
                  {paths.map((p, idx) => (
                    <tr key={idx} className="border-b last:border-0 hover:bg-muted/50">
                      <td className="py-2 px-3 font-mono text-xs">
                        {p.path.join(" \u2192 ")}
                      </td>
                      <td className="py-2 px-3 text-right font-mono">{p.frequency}</td>
                      <td className="py-2 px-3 text-right font-mono">
                        {formatDuration(p.avg_total_duration_seconds)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Section 4: Cycle Time Analysis */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm flex items-center gap-2">
              <Clock className="h-4 w-4" />
              Cycle Time Analysis
            </CardTitle>
            <div className="flex gap-1">
              <Button
                variant={cycleTimeGroupBy === "activity" ? "default" : "outline"}
                size="sm"
                onClick={() => setCycleTimeGroupBy("activity")}
              >
                By Activity
              </Button>
              <Button
                variant={cycleTimeGroupBy === "template" ? "default" : "outline"}
                size="sm"
                onClick={() => setCycleTimeGroupBy("template")}
              >
                By Template
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {cycleTimesQuery.isLoading && (
            <p className="text-sm text-muted-foreground">Loading cycle time data...</p>
          )}
          {cycleTimesQuery.isError && (
            <p className="text-sm text-destructive">Failed to load cycle time data.</p>
          )}
          {cycleTimes && cycleTimes.length === 0 && (
            <p className="text-sm text-muted-foreground">No cycle time data available.</p>
          )}
          {cycleTimes && cycleTimes.length > 0 && (
            <ResponsiveContainer width="100%" height={Math.max(300, cycleTimes.length * 40)}>
              <BarChart
                data={cycleTimes}
                layout="vertical"
                margin={{ top: 5, right: 30, left: 120, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  type="number"
                  tickFormatter={(v: number) => formatDuration(v)}
                />
                <YAxis
                  type="category"
                  dataKey={cycleTimeGroupBy === "activity" ? "activity_name" : "template_name"}
                  width={110}
                  tick={{ fontSize: 12 }}
                />
                <Tooltip content={<CycleTimeTooltip />} />
                <Bar
                  dataKey="avg_seconds"
                  fill={cycleTimeGroupBy === "activity" ? "#3b82f6" : "#22c55e"}
                  radius={[0, 4, 4, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {/* Section 5: Bottleneck Analysis */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <Zap className="h-4 w-4" />
            Bottleneck Analysis
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {bottlenecksQuery.isLoading && (
            <p className="text-sm text-muted-foreground">Loading bottleneck data...</p>
          )}
          {bottlenecksQuery.isError && (
            <p className="text-sm text-destructive">Failed to load bottleneck data.</p>
          )}
          {bottlenecks && bottlenecks.length === 0 && (
            <p className="text-sm text-muted-foreground">No bottleneck data available.</p>
          )}
          {bottlenecks && bottlenecks.length > 0 && (
            <>
              {/* Chart */}
              <ResponsiveContainer width="100%" height={Math.max(300, bottlenecks.length * 40)}>
                <BarChart
                  data={bottlenecks}
                  layout="vertical"
                  margin={{ top: 5, right: 30, left: 120, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    type="number"
                    tickFormatter={(v: number) => formatDuration(v)}
                  />
                  <YAxis
                    type="category"
                    dataKey="activity_name"
                    width={110}
                    tick={{ fontSize: 12 }}
                  />
                  <Tooltip content={<BottleneckTooltip />} />
                  <Bar dataKey="avg_duration_seconds" radius={[0, 4, 4, 0]}>
                    {bottlenecks.map((entry, index) => (
                      <Cell key={index} fill={pctColor(entry.pct_of_total_time)} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>

              {/* Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left">
                      <th className="py-2 px-3 font-medium text-muted-foreground">Activity</th>
                      <th className="py-2 px-3 font-medium text-muted-foreground">Template</th>
                      <th className="py-2 px-3 font-medium text-muted-foreground text-right">Avg Duration</th>
                      <th className="py-2 px-3 font-medium text-muted-foreground text-right">Executions</th>
                      <th className="py-2 px-3 font-medium text-muted-foreground text-right">% of Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {bottlenecks.map((b, idx) => (
                      <tr key={idx} className="border-b last:border-0 hover:bg-muted/50">
                        <td className="py-2 px-3 font-medium">{b.activity_name}</td>
                        <td className="py-2 px-3 text-muted-foreground">{b.template_name}</td>
                        <td className="py-2 px-3 text-right font-mono">
                          {formatDuration(b.avg_duration_seconds)}
                        </td>
                        <td className="py-2 px-3 text-right font-mono">{b.total_executions}</td>
                        <td className="py-2 px-3 text-right font-mono">
                          <span
                            className="inline-block px-2 py-0.5 rounded text-xs font-medium"
                            style={{
                              backgroundColor: pctColor(b.pct_of_total_time) + "20",
                              color: pctColor(b.pct_of_total_time),
                            }}
                          >
                            {b.pct_of_total_time.toFixed(1)}%
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
