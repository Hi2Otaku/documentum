import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  Database,
  Server,
  HardDrive,
  RefreshCw,
  Plus,
  Trash2,
} from "lucide-react";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogFooter,
  DialogTitle,
  DialogDescription,
} from "../components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import {
  fetchHealth,
  fetchMetrics,
  fetchAlertRules,
  createAlertRule,
  updateAlertRule,
  deleteAlertRule,
  monitoringKeys,
} from "../api/monitoring";
import type {
  ComponentHealth,
  AlertRuleCreate,
} from "../api/monitoring";

// --- Helpers ---

const STATUS_COLORS: Record<string, string> = {
  healthy: "bg-green-100 text-green-800",
  degraded: "bg-yellow-100 text-yellow-800",
  unhealthy: "bg-red-100 text-red-800",
};

const OVERALL_BANNER: Record<string, { bg: string; text: string }> = {
  healthy: { bg: "bg-green-500", text: "All Systems Operational" },
  degraded: { bg: "bg-yellow-500", text: "Degraded Performance" },
  unhealthy: { bg: "bg-red-500", text: "System Issues Detected" },
};

const COMPONENT_ICONS: Record<string, React.ReactNode> = {
  database: <Database className="h-5 w-5" />,
  redis: <Server className="h-5 w-5" />,
  celery: <Activity className="h-5 w-5" />,
  minio: <HardDrive className="h-5 w-5" />,
};

const METRIC_OPTIONS = [
  { value: "celery_queue_depth", label: "Celery Queue Depth" },
  { value: "db_connection_ok", label: "DB Connection OK" },
  { value: "redis_ping_ok", label: "Redis Ping OK" },
  { value: "minio_health_ok", label: "MinIO Health OK" },
  { value: "celery_workers_active", label: "Celery Workers Active" },
];

const OPERATOR_OPTIONS = [
  { value: "gt", label: "> (greater than)" },
  { value: "lt", label: "< (less than)" },
  { value: "eq", label: "= (equal)" },
  { value: "gte", label: ">= (greater or equal)" },
  { value: "lte", label: "<= (less or equal)" },
];

function operatorLabel(op: string): string {
  const found = OPERATOR_OPTIONS.find((o) => o.value === op);
  return found ? found.value : op;
}

// --- Component ---

export function MonitoringPage() {
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState<AlertRuleCreate>({
    name: "",
    metric_name: "celery_queue_depth",
    operator: "gt",
    threshold: 0,
    notification_message: "",
  });

  // Queries
  const healthQuery = useQuery({
    queryKey: monitoringKeys.health,
    queryFn: fetchHealth,
    refetchInterval: 30000,
  });

  const metricsQuery = useQuery({
    queryKey: monitoringKeys.metrics,
    queryFn: fetchMetrics,
    refetchInterval: 30000,
  });

  const alertsQuery = useQuery({
    queryKey: monitoringKeys.alerts,
    queryFn: fetchAlertRules,
  });

  // Mutations
  const createMutation = useMutation({
    mutationFn: (data: AlertRuleCreate) => createAlertRule(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: monitoringKeys.alerts });
      setDialogOpen(false);
      setForm({
        name: "",
        metric_name: "celery_queue_depth",
        operator: "gt",
        threshold: 0,
        notification_message: "",
      });
    },
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      updateAlertRule(id, { enabled }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: monitoringKeys.alerts });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteAlertRule(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: monitoringKeys.alerts });
    },
  });

  function handleRefresh() {
    queryClient.invalidateQueries({ queryKey: monitoringKeys.health });
    queryClient.invalidateQueries({ queryKey: monitoringKeys.metrics });
    queryClient.invalidateQueries({ queryKey: monitoringKeys.alerts });
  }

  function handleDelete(id: string, name: string) {
    if (window.confirm(`Delete alert rule "${name}"?`)) {
      deleteMutation.mutate(id);
    }
  }

  function handleCreateSubmit(e: React.FormEvent) {
    e.preventDefault();
    createMutation.mutate(form);
  }

  const health = healthQuery.data;
  const metrics = metricsQuery.data;
  const alerts = alertsQuery.data;

  const overallStatus = health?.status ?? "healthy";
  const banner = OVERALL_BANNER[overallStatus] ?? OVERALL_BANNER.healthy;

  return (
    <div className="p-6 space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="h-5 w-5 text-muted-foreground" />
          <h1 className="text-lg font-semibold">System Monitoring</h1>
        </div>
        <Button variant="outline" size="sm" onClick={handleRefresh}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Overall status banner */}
      {health && (
        <div className={`${banner.bg} text-white px-4 py-2 rounded-md text-sm font-medium`}>
          {banner.text}
          <span className="ml-2 text-xs opacity-75">
            Last checked: {new Date(health.checked_at).toLocaleTimeString()}
          </span>
        </div>
      )}

      {/* Health Status section */}
      <div>
        <h2 className="text-sm font-medium text-muted-foreground mb-3">Health Status</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {health?.components.map((comp: ComponentHealth) => (
            <Card key={comp.name}>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  {COMPONENT_ICONS[comp.name] ?? <Server className="h-5 w-5" />}
                  {comp.name.charAt(0).toUpperCase() + comp.name.slice(1)}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Badge className={STATUS_COLORS[comp.status] ?? ""}>
                  {comp.status}
                </Badge>
                {comp.latency_ms != null && (
                  <p className="text-xs text-muted-foreground mt-2">
                    Latency: {comp.latency_ms.toFixed(1)} ms
                  </p>
                )}
                {comp.details && (
                  <p className="text-xs text-muted-foreground mt-1">{comp.details}</p>
                )}
              </CardContent>
            </Card>
          ))}
          {healthQuery.isLoading && (
            <p className="text-sm text-muted-foreground col-span-full">Loading health data...</p>
          )}
          {healthQuery.isError && (
            <p className="text-sm text-destructive col-span-full">
              Failed to load health data.
            </p>
          )}
        </div>
      </div>

      {/* Queue & Workers section */}
      <div>
        <h2 className="text-sm font-medium text-muted-foreground mb-3">Queues & Workers</h2>

        {/* Summary stats */}
        {metrics && (
          <div className="grid grid-cols-2 gap-4 mb-4">
            <Card>
              <CardContent className="pt-4">
                <p className="text-xs text-muted-foreground">Active Tasks</p>
                <p className="text-2xl font-bold">{metrics.total_active_tasks}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4">
                <p className="text-xs text-muted-foreground">Scheduled Tasks</p>
                <p className="text-2xl font-bold">{metrics.total_scheduled_tasks}</p>
              </CardContent>
            </Card>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Queue Depths */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Queue Depths</CardTitle>
            </CardHeader>
            <CardContent>
              {metrics && metrics.queues.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Queue</TableHead>
                      <TableHead className="text-right">Depth</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {metrics.queues.map((q) => (
                      <TableRow key={q.queue_name}>
                        <TableCell className="font-mono text-sm">{q.queue_name}</TableCell>
                        <TableCell className="text-right font-mono">{q.depth}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <p className="text-sm text-muted-foreground">
                  {metricsQuery.isLoading ? "Loading..." : "No queue data available."}
                </p>
              )}
            </CardContent>
          </Card>

          {/* Worker Status */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Worker Status</CardTitle>
            </CardHeader>
            <CardContent>
              {metrics && metrics.workers.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Hostname</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Active</TableHead>
                      <TableHead className="text-right">Processed</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {metrics.workers.map((w) => (
                      <TableRow key={w.hostname}>
                        <TableCell className="font-mono text-sm">{w.hostname}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{w.status}</Badge>
                        </TableCell>
                        <TableCell className="text-right font-mono">{w.active_tasks}</TableCell>
                        <TableCell className="text-right font-mono">{w.processed}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <p className="text-sm text-muted-foreground">
                  {metricsQuery.isLoading ? "Loading..." : "No worker data available."}
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Alert Rules section */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-medium text-muted-foreground">Alert Rules</h2>
          <Button size="sm" onClick={() => setDialogOpen(true)}>
            <Plus className="h-4 w-4 mr-1" />
            Add Rule
          </Button>
        </div>

        <Card>
          <CardContent className="pt-4">
            {alerts && alerts.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Metric</TableHead>
                    <TableHead>Condition</TableHead>
                    <TableHead>Enabled</TableHead>
                    <TableHead className="w-[60px]"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {alerts.map((rule) => (
                    <TableRow key={rule.id}>
                      <TableCell className="font-medium">{rule.name}</TableCell>
                      <TableCell className="font-mono text-sm">{rule.metric_name}</TableCell>
                      <TableCell className="font-mono text-sm">
                        {operatorLabel(rule.operator)} {rule.threshold}
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() =>
                            toggleMutation.mutate({
                              id: rule.id,
                              enabled: !rule.enabled,
                            })
                          }
                        >
                          <Badge
                            className={
                              rule.enabled
                                ? "bg-green-100 text-green-800"
                                : "bg-gray-100 text-gray-600"
                            }
                          >
                            {rule.enabled ? "On" : "Off"}
                          </Badge>
                        </Button>
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDelete(rule.id, rule.name)}
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <p className="text-sm text-muted-foreground">
                {alertsQuery.isLoading ? "Loading..." : "No alert rules configured."}
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Add Rule Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Alert Rule</DialogTitle>
            <DialogDescription>
              Configure a threshold-based alert for a system metric.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCreateSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="rule-name">Name</Label>
              <Input
                id="rule-name"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="e.g. High queue depth"
                required
              />
            </div>

            <div className="space-y-2">
              <Label>Metric</Label>
              <Select
                value={form.metric_name}
                onValueChange={(v) => setForm({ ...form, metric_name: v })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {METRIC_OPTIONS.map((m) => (
                    <SelectItem key={m.value} value={m.value}>
                      {m.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Operator</Label>
                <Select
                  value={form.operator}
                  onValueChange={(v) => setForm({ ...form, operator: v })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {OPERATOR_OPTIONS.map((op) => (
                      <SelectItem key={op.value} value={op.value}>
                        {op.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="rule-threshold">Threshold</Label>
                <Input
                  id="rule-threshold"
                  type="number"
                  value={form.threshold}
                  onChange={(e) =>
                    setForm({ ...form, threshold: parseFloat(e.target.value) || 0 })
                  }
                  required
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="rule-message">Notification Message (optional)</Label>
              <Input
                id="rule-message"
                value={form.notification_message ?? ""}
                onChange={(e) =>
                  setForm({ ...form, notification_message: e.target.value || undefined })
                }
                placeholder="Custom alert message..."
              />
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setDialogOpen(false)}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? "Creating..." : "Create Rule"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
