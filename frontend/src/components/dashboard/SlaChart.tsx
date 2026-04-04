import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Skeleton } from '../ui/skeleton';
import type { SlaCompliance } from '../../api/dashboard';

interface SlaChartProps {
  data: SlaCompliance[];
  loading?: boolean;
}

interface SlaTooltipProps {
  active?: boolean;
  payload?: Array<{ payload: SlaCompliance }>;
  label?: string;
}

function SlaTooltipContent({ active, payload, label }: SlaTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  const item = payload[0].payload;
  const total = item.on_time + item.overdue;
  const onTimePct = total > 0 ? ((item.on_time / total) * 100).toFixed(0) : '0';
  const overduePct = total > 0 ? ((item.overdue / total) * 100).toFixed(0) : '0';
  return (
    <div className="rounded-md border bg-popover p-2 text-sm shadow-md">
      <p className="font-medium mb-1">{label}</p>
      <p>{item.on_time} on-time ({onTimePct}%)</p>
      <p>{item.overdue} overdue ({overduePct}%)</p>
    </div>
  );
}

export function SlaChart({ data, loading }: SlaChartProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-bold">SLA Compliance</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-6" style={{ width: `${85 - i * 15}%` }} />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!data || data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-bold">SLA Compliance</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No activities have SLA time limits configured.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-bold">SLA Compliance</CardTitle>
      </CardHeader>
      <CardContent>
        <div
          role="img"
          aria-label="Stacked bar chart showing SLA compliance per activity"
        >
          <ResponsiveContainer width="100%" height={Math.max(200, data.length * 40 + 60)}>
            <BarChart data={data} layout="vertical" margin={{ left: 10, right: 20 }}>
              <XAxis type="number" label={{ value: 'Work Items', position: 'insideBottom', offset: -5 }} />
              <YAxis type="category" dataKey="activity_name" width={120} tick={{ fontSize: 12 }} />
              <Tooltip content={<SlaTooltipContent />} />
              <Legend verticalAlign="bottom" />
              <Bar dataKey="on_time" stackId="sla" fill="#22c55e" name="On Time" radius={[0, 0, 0, 0]} />
              <Bar dataKey="overdue" stackId="sla" fill="#ef4444" name="Overdue" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
