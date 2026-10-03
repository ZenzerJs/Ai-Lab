import React from 'react';
import { TaskSummaryItem } from '../types';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { formatCurrency } from '../lib/formatters';
import { CheckCircle2, AlertCircle } from 'lucide-react';

interface TaskTableProps {
  tasks: TaskSummaryItem[];
}

export const TaskTable: React.FC<TaskTableProps> = ({ tasks }) => {
  if (!tasks || tasks.length === 0) {
    return null;
  }

  return (
    <Card className="glass-panel border-white/10 rounded-2xl shadow-xl overflow-hidden">
      <CardHeader className="pb-4 border-b border-white/5 bg-white/[0.02]">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base font-bold text-white font-mono tracking-tight">
              Task Execution &amp; Telemetry Matrix
            </CardTitle>
            <CardDescription className="text-xs text-gray-400 font-mono mt-0.5">
              Empirical side-by-side cost breakdown, prompt caching retention, and latency.
            </CardDescription>
          </div>
          <Badge variant="outline" className="font-mono text-xs border-indigo-500/30 text-indigo-300 bg-indigo-500/10">
            {tasks.length} Benchmark Archetypes
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader className="bg-black/30 border-y border-white/5">
              <TableRow className="border-none">
                <TableHead className="text-xs font-mono text-gray-400 font-semibold uppercase">Task ID</TableHead>
                <TableHead className="text-xs font-mono text-gray-400 font-semibold uppercase">Runs (B / ICM)</TableHead>
                <TableHead className="text-xs font-mono text-gray-400 font-semibold uppercase">Baseline Cost</TableHead>
                <TableHead className="text-xs font-mono text-indigo-400 font-semibold uppercase">ICM Cost</TableHead>
                <TableHead className="text-xs font-mono text-gray-400 font-semibold uppercase">Cost Delta</TableHead>
                <TableHead className="text-xs font-mono text-gray-400 font-semibold uppercase">Cache Hit Ratio</TableHead>
                <TableHead className="text-xs font-mono text-gray-400 font-semibold uppercase">Duration</TableHead>
                <TableHead className="text-xs font-mono text-gray-400 font-semibold uppercase">Verification</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody className="divide-y divide-white/5 font-mono">
              {tasks.map((task) => {
                const b = task.arms.baseline;
                const govKey = Object.keys(task.arms).find((k) => k !== 'baseline') || 'icm';
                const i = task.arms[govKey];

                const bCost = b?.mean_cost_usd !== null && b?.mean_cost_usd !== undefined ? formatCurrency(b.mean_cost_usd) : '—';
                const iCost = i?.mean_cost_usd !== null && i?.mean_cost_usd !== undefined ? formatCurrency(i.mean_cost_usd) : '—';

                const savingsPct = task.savings?.mean_savings_percent;
                const isSaved = savingsPct != null && savingsPct > 0;
                const isOverhead = savingsPct != null && savingsPct < 0;

                const bCache = b?.cache_hit_ratio !== undefined ? `${(b.cache_hit_ratio * 100).toFixed(1)}%` : '—';
                const iCache = i?.cache_hit_ratio !== undefined ? `${(i.cache_hit_ratio * 100).toFixed(1)}%` : '—';

                const bDur = b?.mean_duration_seconds !== undefined ? `${b.mean_duration_seconds.toFixed(1)}s` : '—';
                const iDur = i?.mean_duration_seconds !== undefined ? `${i.mean_duration_seconds.toFixed(1)}s` : '—';

                return (
                  <TableRow key={task.task_id} className="hover:bg-white/[0.03] transition-colors border-none">
                    <TableCell className="font-mono text-xs font-bold text-white">
                      {task.task_id}
                    </TableCell>
                    <TableCell className="font-mono text-xs text-gray-400">
                      <span className="text-gray-300 font-medium">{b?.n ?? 0}</span>
                      <span className="text-gray-600 mx-1">/</span>
                      <span className="text-indigo-400 font-medium">{i?.n ?? 0}</span>
                    </TableCell>
                    <TableCell className="font-mono text-xs text-gray-300">
                      {bCost}
                    </TableCell>
                    <TableCell className="font-mono text-xs text-indigo-300 font-bold">
                      {iCost}
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      {savingsPct !== null && savingsPct !== undefined ? (
                        <span className={`px-2 py-0.5 rounded-md text-[11px] font-bold ${
                          isSaved
                            ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                            : isOverhead
                            ? 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
                            : 'bg-white/5 text-gray-400'
                        }`}>
                          {isSaved ? `-${savingsPct.toFixed(1)}%` : `+${Math.abs(savingsPct).toFixed(1)}%`}
                        </span>
                      ) : (
                        <span className="text-gray-500">—</span>
                      )}
                    </TableCell>
                    <TableCell className="font-mono text-xs text-gray-400">
                      <span className="text-gray-400">{bCache}</span>
                      <span className="text-gray-600 mx-1.5">→</span>
                      <span className="text-indigo-300 font-semibold">{iCache}</span>
                    </TableCell>
                    <TableCell className="font-mono text-xs text-gray-400">
                      <span>{bDur}</span>
                      <span className="text-gray-600 mx-1.5">vs</span>
                      <span className="text-indigo-300">{iDur}</span>
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      {task.has_measured_data ? (
                        <div className="flex items-center gap-1.5 text-emerald-400 font-medium">
                          <CheckCircle2 className="size-3.5" />
                          <span>Verified</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1.5 text-amber-400 font-medium">
                          <AlertCircle className="size-3.5" />
                          <span>Simulated</span>
                        </div>
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
