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
import type { UserWorkload } from '../../api/dashboard';

interface WorkloadChartProps {
  data: UserWorkload[];
  loading?: boolean;
}

export function WorkloadChart({ data, loading }: WorkloadChartProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-bold">Workload by User</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-6" style={{ width: `${80 - i * 10}%` }} />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  // Show top 15 users by total tasks
  const sorted = [...data]
    .sort((a, b) => (b.assigned + b.completed + b.pending) - (a.assigned + a.completed + a.pending))
    .slice(0, 15);

  if (sorted.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-bold">Workload by User</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">No workload data available.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-bold">Workload by User</CardTitle>
      </CardHeader>
      <CardContent>
        <div
          role="img"
          aria-label="Grouped bar chart showing task counts per user"
        >
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={sorted} margin={{ left: 10, right: 20, bottom: 20 }}>
              <XAxis type="category" dataKey="username" tick={{ fontSize: 12 }} />
              <YAxis type="number" label={{ value: 'Tasks', angle: -90, position: 'insideLeft' }} />
              <Tooltip />
              <Legend verticalAlign="bottom" />
              <Bar dataKey="assigned" fill="#3b82f6" name="Assigned" radius={[4, 4, 0, 0]} />
              <Bar dataKey="completed" fill="#22c55e" name="Completed" radius={[4, 4, 0, 0]} />
              <Bar dataKey="pending" fill="#f59e0b" name="Pending" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        {data.length > 15 && (
          <p className="text-sm text-muted-foreground mt-2">
            Showing top 15 of {data.length}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
