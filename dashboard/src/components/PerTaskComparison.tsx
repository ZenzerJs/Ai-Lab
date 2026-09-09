import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
  ErrorBar,
} from 'recharts';
import { TaskSummaryItem } from '../types';
import { DollarSign, AlertCircle } from 'lucide-react';

interface PerTaskComparisonProps {
  tasks: TaskSummaryItem[];
}

export const PerTaskComparison: React.FC<PerTaskComparisonProps> = ({ tasks }) => {
  if (!tasks || tasks.length === 0) {
    return (
      <div className="bg-surface border border-surface-border rounded-xl p-6 text-center">
        <AlertCircle className="w-8 h-8 text-gray-500 mx-auto mb-2" />
        <p className="text-gray-400 text-sm">No task comparison data available.</p>
      </div>
    );
  }

  // Transform data for Recharts grouped bar with error bands
  const chartData = tasks.map((t) => {
    const b = t.arms.baseline;
    const i = t.arms.icm;

    const bMean = b?.mean_cost_usd ?? 0;
    const bMin = b?.min_cost_usd ?? bMean;
    const bMax = b?.max_cost_usd ?? bMean;

    const iMean = i?.mean_cost_usd ?? 0;
    const iMin = i?.min_cost_usd ?? iMean;
    const iMax = i?.max_cost_usd ?? iMean;

    return {
      taskId: t.task_id,
      model: b?.model || i?.model || 'unknown',
      baselineCost: Number(bMean.toFixed(6)),
      baselineError: [
        Number((bMean - bMin).toFixed(6)),
        Number((bMax - bMean).toFixed(6)),
      ],
      baselineN: b?.n ?? 0,
      baselineMin: bMin,
      baselineMax: bMax,
      icmCost: Number(iMean.toFixed(6)),
      icmError: [
        Number((iMean - iMin).toFixed(6)),
        Number((iMax - iMean).toFixed(6)),
      ],
      icmN: i?.n ?? 0,
      icmMin: iMin,
      icmMax: iMax,
      savingsPct: t.savings?.mean_savings_percent ?? 0,
      savingsUsd: t.savings?.mean_savings_usd ?? 0,
    };
  });

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const item = payload[0].payload;
      return (
        <div className="bg-surface-hover border border-surface-border p-3 rounded-lg shadow-xl text-xs space-y-2">
          <div className="font-semibold text-white border-b border-surface-border pb-1">
            Task: {label} ({item.model})
          </div>
          <div className="space-y-1">
            <div className="text-red-400">
              <span className="font-medium">Baseline (n={item.baselineN}):</span> ${item.baselineCost.toFixed(5)}
              <div className="text-[10px] text-gray-400 pl-2">
                Min: ${item.baselineMin.toFixed(5)} | Max: ${item.baselineMax.toFixed(5)}
              </div>
            </div>
            <div className="text-emerald-400">
              <span className="font-medium">ICM Pipeline (n={item.icmN}):</span> ${item.icmCost.toFixed(5)}
              <div className="text-[10px] text-gray-400 pl-2">
                Min: ${item.icmMin.toFixed(5)} | Max: ${item.icmMax.toFixed(5)}
              </div>
            </div>
          </div>
          {item.savingsPct !== 0 && (
            <div className="pt-1 border-t border-surface-border text-emerald-300 font-medium">
              Net Savings: ${item.savingsUsd.toFixed(5)} ({item.savingsPct.toFixed(1)}%)
            </div>
          )}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="bg-surface border border-surface-border rounded-xl p-5 shadow-sm">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-4 border-b border-surface-border gap-2">
        <div>
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <DollarSign className="w-4 h-4 text-primary" />
            Per-Task Mean Cost Comparison
          </h2>
          <p className="text-xs text-gray-400">
            Baseline vs. ICM pipeline mean cost in USD per run with min–max observed error bars.
          </p>
        </div>
        <div className="flex items-center gap-3 text-xs">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-sm bg-red-500/80 inline-block"></span>
            <span className="text-gray-300">Baseline Arm</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-sm bg-emerald-500/80 inline-block"></span>
            <span className="text-gray-300">ICM Arm</span>
          </div>
        </div>
      </div>

      <div className="h-72 w-full mt-4">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={chartData}
            margin={{ top: 20, right: 30, left: 10, bottom: 5 }}
            barCategoryGap="25%"
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#21262d" vertical={false} />
            <XAxis
              dataKey="taskId"
              stroke="#8b949e"
              fontSize={12}
              tickLine={false}
              axisLine={{ stroke: '#30363d' }}
            />
            <YAxis
              stroke="#8b949e"
              fontSize={12}
              tickLine={false}
              axisLine={{ stroke: '#30363d' }}
              tickFormatter={(v) => `$${v.toFixed(3)}`}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              verticalAlign="top"
              align="right"
              wrapperStyle={{ paddingBottom: '10px', fontSize: '11px' }}
              formatter={(value, entry: any) => {
                const isBase = entry.dataKey === 'baselineCost';
                const nList = chartData.map((d) => (isBase ? d.baselineN : d.icmN));
                const allEqual = nList.every((val) => val === nList[0]);
                const nLabel = allEqual ? `n=${nList[0] || 0}` : 'per-task n in tooltip';
                return (
                  <span className="text-gray-300">
                    {value} ({nLabel})
                  </span>
                );
              }}
            />
            <Bar
              name="Baseline Cost"
              dataKey="baselineCost"
              fill="#f85149"
              radius={[4, 4, 0, 0]}
            >
              <ErrorBar
                dataKey="baselineError"
                width={4}
                strokeWidth={1.5}
                stroke="#ffa198"
                direction="y"
              />
            </Bar>
            <Bar
              name="ICM Cost"
              dataKey="icmCost"
              fill="#2ea043"
              radius={[4, 4, 0, 0]}
            >
              <ErrorBar
                dataKey="icmError"
                width={4}
                strokeWidth={1.5}
                stroke="#7ee787"
                direction="y"
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Per-Task Run Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 mt-4 pt-4 border-t border-surface-border text-xs">
        {chartData.map((d) => (
          <div
            key={d.taskId}
            className="p-3 rounded-lg bg-background/50 border border-surface-border flex flex-col justify-between"
          >
            <div className="flex justify-between items-center mb-1.5">
              <span className="font-mono font-medium text-gray-200">{d.taskId}</span>
              <span className="px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-semibold text-[11px] border border-emerald-500/20">
                -{d.savingsPct.toFixed(1)}% Cost
              </span>
            </div>
            <div className="space-y-1 text-gray-400">
              <div className="flex justify-between">
                <span>Baseline (n={d.baselineN}):</span>
                <span className="font-mono text-gray-200">${d.baselineCost.toFixed(5)}</span>
              </div>
              <div className="flex justify-between">
                <span>ICM Pipeline (n={d.icmN}):</span>
                <span className="font-mono text-emerald-400">${d.icmCost.toFixed(5)}</span>
              </div>
              <div className="flex justify-between pt-1 border-t border-surface-border/50 text-gray-300 font-medium">
                <span>Net Savings/Run:</span>
                <span className="font-mono text-emerald-300">+${d.savingsUsd.toFixed(5)}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
