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
    <Card className="glass-panel border-white/10 rounded-2xl shadow-xl overflow-hidden">
      <CardHeader className="pb-4 border-b border-white/5 bg-white/[0.02]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
              <BarChart3 className="size-4.5" />
            </div>
            <div>
              <CardTitle className="text-base font-bold text-white font-mono tracking-tight">
                Empirical Cost per Run by Task Archetype
              </CardTitle>
              <CardDescription className="text-xs text-gray-400 font-mono mt-0.5">
                Head-to-head live CLI execution costs under prompt-parity constraints.
              </CardDescription>
            </div>
          </div>
          <div className="flex items-center gap-3 text-xs font-mono">
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-sm bg-slate-500" />
              <span className="text-gray-400">Baseline</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-sm bg-indigo-500 shadow-[0_0_8px_rgba(99,102,241,0.6)]" />
              <span className="text-indigo-300 font-semibold">ICM Governed</span>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-5 p-6">
        {chartItems.map((item) => {
          const isSaved = item.savingsPct != null && item.savingsPct > 0;
          const isOverhead = item.savingsPct != null && item.savingsPct < 0;

          return (
            <div key={item.taskId} className="group p-3.5 rounded-xl bg-white/[0.02] border border-white/5 hover:border-white/15 transition-all duration-200">
              <div className="flex items-center justify-between text-xs font-mono mb-2.5">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-white tracking-wide">{item.taskId}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-gray-400">Baseline: <strong className="text-gray-300">{formatCurrency(item.bCost)}</strong></span>
                  <span className="text-gray-400">ICM: <strong className="text-indigo-300">{formatCurrency(item.iCost)}</strong></span>
                  {item.savingsPct != null && (
                    <span className={`px-2 py-0.5 rounded-md text-[11px] font-bold ${
                      isSaved
                        ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                        : isOverhead
                        ? 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
                        : 'bg-white/5 text-gray-400'
                    }`}>
                      {isSaved ? `-${item.savingsPct.toFixed(1)}%` : `+${Math.abs(item.savingsPct).toFixed(1)}%`}
                    </span>
                  )}
                </div>
              </div>

              <div className="space-y-2">
                {/* Baseline bar */}
                <div className="relative flex items-center gap-2">
                  <span className="text-[10px] font-mono text-gray-500 w-16 shrink-0">Baseline</span>
                  <div className="flex-1 h-3.5 bg-black/40 rounded-full overflow-hidden p-0.5 border border-white/5">
                    <div
                      className="h-full bg-slate-500/70 rounded-full transition-all duration-500"
                      style={{ width: `${Math.max(item.bPercent, 3)}%` }}
                    />
                  </div>
                </div>

                {/* ICM bar */}
                <div className="relative flex items-center gap-2">
                  <span className="text-[10px] font-mono text-indigo-400 w-16 shrink-0 font-medium">ICM Arm</span>
                  <div className="flex-1 h-3.5 bg-black/40 rounded-full overflow-hidden p-0.5 border border-indigo-500/20">
                    <div
                      className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full transition-all duration-500 shadow-[0_0_10px_rgba(99,102,241,0.4)]"
                      style={{ width: `${Math.max(item.iPercent, 3)}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
};
