import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Skeleton } from '../ui/skeleton';
import type { BottleneckActivity } from '../../api/dashboard';

interface BottleneckChartProps {
  data: BottleneckActivity[];
  loading?: boolean;
}

export function BottleneckChart({ data, loading }: BottleneckChartProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-bold">Bottleneck Activities</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-6" style={{ width: `${90 - i * 12}%` }} />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  const totalCount = data.length;
  const sorted = [...data]
    .sort((a, b) => b.avg_duration_hours - a.avg_duration_hours)
    .slice(0, 10);

  if (sorted.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-bold">Bottleneck Activities</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">No activity data available.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-bold">Bottleneck Activities</CardTitle>
      </CardHeader>
      <CardContent>
        <div
          role="img"
          aria-label="Bar chart showing average duration per activity in hours"
        >
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={sorted} layout="vertical" margin={{ left: 10, right: 20 }}>
              <XAxis type="number" label={{ value: 'Avg Hours', position: 'insideBottom', offset: -5 }} />
              <YAxis type="category" dataKey="activity_name" width={120} tick={{ fontSize: 12 }} />
              <Tooltip
                formatter={(value: number) => [`${value.toFixed(1)} hrs`, 'Avg Duration']}
              />
              <Bar dataKey="avg_duration_hours" fill="hsl(var(--primary))" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        {totalCount > 10 && (
          <p className="text-sm text-muted-foreground mt-2">
            Showing top 10 of {totalCount}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
