import React from 'react';
import { TaskSummaryItem } from '../types';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { formatCurrency } from '../lib/formatters';

interface TaskTableProps {
  tasks: TaskSummaryItem[];
}

export const TaskTable: React.FC<TaskTableProps> = ({ tasks }) => {
  if (!tasks || tasks.length === 0) {
    return null;
  }

  return (
    <Card className="border-surface-border bg-surface shadow-sm">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base font-semibold text-white font-mono">
              Task Execution & Telemetry Breakdown
            </CardTitle>
            <CardDescription className="text-xs text-muted-foreground font-mono mt-0.5">
              Side-by-side performance, cost economics, and duration across benchmark tasks.
            </CardDescription>
          </div>
          <Badge variant="outline" className="font-mono text-xs">
            {tasks.length} Tasks
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader className="bg-background/50 border-y border-surface-border">
              <TableRow className="border-none">
                <TableHead className="text-xs font-mono">Task ID</TableHead>
                <TableHead className="text-xs font-mono">Runs (B / ICM)</TableHead>
                <TableHead className="text-xs font-mono">Baseline Cost</TableHead>
                <TableHead className="text-xs font-mono">ICM Cost</TableHead>
                <TableHead className="text-xs font-mono">Cost Delta</TableHead>
                <TableHead className="text-xs font-mono">Prompt Cache %</TableHead>
                <TableHead className="text-xs font-mono">Avg Duration</TableHead>
                <TableHead className="text-xs font-mono">Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {tasks.map((task) => {
                const b = task.arms.baseline;
                const govKey = Object.keys(task.arms).find((k) => k !== 'baseline') || 'icm';
                const i = task.arms[govKey];

                const bCost = b?.mean_cost_usd !== null && b?.mean_cost_usd !== undefined ? formatCurrency(b.mean_cost_usd) : '—';
                const iCost = i?.mean_cost_usd !== null && i?.mean_cost_usd !== undefined ? formatCurrency(i.mean_cost_usd) : '—';

                const savingsPct = task.savings?.mean_savings_percent;
                const savingsText = savingsPct !== null && savingsPct !== undefined
                  ? `${savingsPct > 0 ? '-' : '+'}${Math.abs(savingsPct).toFixed(1)}%`
                  : '—';

                const bCache = b?.cache_hit_ratio !== undefined ? `${(b.cache_hit_ratio * 100).toFixed(1)}%` : '—';
                const iCache = i?.cache_hit_ratio !== undefined ? `${(i.cache_hit_ratio * 100).toFixed(1)}%` : '—';

                const bDur = b?.mean_duration_seconds !== undefined ? `${b.mean_duration_seconds.toFixed(1)}s` : '—';
                const iDur = i?.mean_duration_seconds !== undefined ? `${i.mean_duration_seconds.toFixed(1)}s` : '—';

                return (
                  <TableRow key={task.task_id} className="border-b border-surface-border hover:bg-background/40">
                    <TableCell className="font-mono text-xs font-semibold text-white">
                      {task.task_id}
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {b?.n ?? 0} / {i?.n ?? 0}
                    </TableCell>
                    <TableCell className="font-mono text-xs text-gray-300">
                      {bCost}
                    </TableCell>
                    <TableCell className="font-mono text-xs text-primary-light font-medium">
                      {iCost}
                    </TableCell>
                    <TableCell className="font-mono text-xs font-medium">
                      {savingsPct !== null && savingsPct !== undefined ? (
                        <span className={savingsPct >= 0 ? 'text-primary' : 'text-danger'}>
                          {savingsText}
                        </span>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {bCache} → {iCache}
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {bDur} vs {iDur}
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      {task.has_measured_data ? (
                        <span className="text-emerald-400 font-medium">Verified</span>
                      ) : (
                        <span className="text-amber-400">Unverified</span>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
};
