import React, { useMemo } from 'react';
import { TaskSummaryItem } from '../types';
import { BarChart3 } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from './ui/card';
import { formatCurrency } from '../lib/formatters';

interface TaskComparisonProps {
  tasks: TaskSummaryItem[];
}

export const TaskComparison: React.FC<TaskComparisonProps> = ({ tasks }) => {
  const chartItems = useMemo(() => {
    if (!tasks) return [];
    return tasks
      .filter((t) => t.has_measured_data)
      .map((t) => {
        const b = t.arms.baseline;
        const govKey = Object.keys(t.arms).find((k) => k !== 'baseline') || 'icm';
        const i = t.arms[govKey];

        const bCost = b?.mean_cost_usd ?? 0;
        const iCost = i?.mean_cost_usd ?? 0;
        const maxVal = Math.max(bCost, iCost, 0.0001);

        return {
          taskId: t.task_id,
          bCost,
          iCost,
          bPercent: (bCost / maxVal) * 100,
          iPercent: (iCost / maxVal) * 100,
          savingsPct: t.savings?.mean_savings_percent,
        };
      });
  }, [tasks]);

  if (chartItems.length === 0) {
    return null;
  }

  return (
    <Card className="border-surface-border bg-surface shadow-sm">
      <CardHeader className="pb-4">
        <div className="flex items-center gap-2">
          <BarChart3 className="size-5 text-primary" />
          <CardTitle className="text-base font-semibold text-white font-mono">
            Per-Task Cost Comparison (Baseline vs. ICM)
          </CardTitle>
        </div>
        <CardDescription className="text-xs text-muted-foreground font-mono">
          Empirical cost per run measured under identical task prompts.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        {chartItems.map((item) => (
          <div key={item.taskId} className="space-y-2">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="font-semibold text-white">{item.taskId}</span>
              <div className="flex items-center gap-3">
                <span className="text-gray-400">Baseline: {formatCurrency(item.bCost)}</span>
                <span className="text-primary-light font-medium">ICM: {formatCurrency(item.iCost)}</span>
                {item.savingsPct !== null && item.savingsPct !== undefined && (
                  <span className={item.savingsPct >= 0 ? 'text-primary' : 'text-danger'}>
                    ({item.savingsPct > 0 ? '-' : '+'}{Math.abs(item.savingsPct).toFixed(1)}%)
                  </span>
                )}
              </div>
            </div>

            <div className="space-y-1.5">
              {/* Baseline bar */}
              <div className="h-4 bg-background rounded overflow-hidden flex items-center p-0.5 border border-surface-border">
                <div
                  className="h-full bg-slate-500/60 rounded transition-all duration-500"
                  style={{ width: `${Math.max(item.bPercent, 2)}%` }}
                />
              </div>

              {/* ICM bar */}
              <div className="h-4 bg-background rounded overflow-hidden flex items-center p-0.5 border border-surface-border">
                <div
                  className="h-full bg-primary rounded transition-all duration-500"
                  style={{ width: `${Math.max(item.iPercent, 2)}%` }}
                />
              </div>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
};
