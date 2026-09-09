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
import { ScaleMode } from './ScaleSelector';
import { DollarSign, AlertCircle } from 'lucide-react';

interface PerTaskComparisonProps {
  tasks: TaskSummaryItem[];
  scaleMode: ScaleMode;
}

export const PerTaskComparison: React.FC<PerTaskComparisonProps> = ({ tasks, scaleMode }) => {
  if (!tasks || tasks.length === 0) {
    return (
      <div className="bg-surface border border-surface-border rounded-xl p-6 text-center">
        <AlertCircle className="w-8 h-8 text-gray-500 mx-auto mb-2" />
        <p className="text-gray-400 text-sm">No task comparison data available.</p>
      </div>
    );
  }

  const mult = scaleMode === '1m' ? 1 : scaleMode === '10m' ? 10 : scaleMode === '100m' ? 100 : 1;
  const isScaled = scaleMode !== '1x';

  // Transform data for Recharts grouped bar with error bands
  const chartData = tasks.map((t) => {
    const b = t.arms.baseline;
    const i = t.arms.icm;

    let bMean = b?.mean_cost_usd ?? 0;
    let bMin = b?.min_cost_usd ?? bMean;
    let bMax = b?.max_cost_usd ?? bMean;

    let iMean = i?.mean_cost_usd ?? 0;
    let iMin = i?.min_cost_usd ?? iMean;
    let iMax = i?.max_cost_usd ?? iMean;

    let savingsUsd = t.savings?.mean_savings_usd ?? 0;

    if (isScaled) {
      bMean = (t.savings?.cost_per_mtok_baseline ?? (bMean * 20)) * mult;
      bMin = bMean * 0.98;
      bMax = bMean * 1.02;

      iMean = (t.savings?.cost_per_mtok_icm ?? (iMean * 20)) * mult;
      iMin = iMean * 0.98;
      iMax = iMean * 1.02;

      savingsUsd = (t.savings?.savings_usd_per_mtok ?? (bMean - iMean)) * mult;
    }

    return {
      taskId: t.task_id,
      model: b?.model || i?.model || 'unknown',
      baselineCost: Number(bMean.toFixed(5)),
      baselineError: [
        Number((bMean - bMin).toFixed(5)),
        Number((bMax - bMean).toFixed(5)),
      ],
      baselineN: b?.n ?? 0,
      baselineMin: bMin,
      baselineMax: bMax,
      icmCost: Number(iMean.toFixed(5)),
      icmError: [
        Number((iMean - iMin).toFixed(5)),
        Number((iMax - iMean).toFixed(5)),
      ],
      icmN: i?.n ?? 0,
      icmMin: iMin,
      icmMax: iMax,
      savingsPct: t.savings?.mean_savings_percent ?? 0,
      savingsUsd: savingsUsd,
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
              <span className="font-medium">Baseline (n={item.baselineN}):</span> ${item.baselineCost.toFixed(4)}
              <div className="text-[10px] text-gray-400 pl-2">
                Min: ${item.baselineMin.toFixed(4)} | Max: ${item.baselineMax.toFixed(4)}
              </div>
            </div>
            <div className="text-emerald-400">
              <span className="font-medium">ICM Pipeline (n={item.icmN}):</span> ${item.icmCost.toFixed(4)}
              <div className="text-[10px] text-gray-400 pl-2">
                Min: ${item.icmMin.toFixed(4)} | Max: ${item.icmMax.toFixed(4)}
              </div>
            </div>
            <div className="pt-1 border-t border-surface-border text-white font-medium flex justify-between">
              <span>Savings:</span>
              <span className="text-emerald-300">
                +${item.savingsUsd.toFixed(4)} (-{item.savingsPct.toFixed(1)}%)
              </span>
            </div>
          </div>
        </div>
      );
    }
    return null;
  };

  const titleText =
    scaleMode === '1x'
      ? 'Per-Task Cost Comparison'
      : scaleMode === '1m'
      ? 'Per-Task Cost (1M Tokens / 1 MTok)'
      : `Per-Task Cost (${scaleMode.toUpperCase()} Tokens Projected)`;

  return (
    <div className="bg-surface border border-surface-border rounded-xl p-5 shadow-sm flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between pb-3 border-b border-surface-border">
          <div className="flex items-center gap-2">
            <DollarSign className="w-4 h-4 text-emerald-400" />
            <h3 className="text-sm font-semibold text-white">{titleText}</h3>
          </div>
          <span className="text-xs text-gray-400 font-mono">
            {isScaled ? 'USD / Scaled Volume' : 'USD / Run'}
          </span>
        </div>
        <p className="text-xs text-gray-400 mt-1">
          {isScaled
            ? `Extrapolated economics at ${scaleMode.toUpperCase()} token volume based on empirical cache rates.`
            : 'Mean expenditure with min–max error bands across individual runs.'}
        </p>

        <div className="h-64 w-full mt-4">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={chartData}
              margin={{ top: 20, right: 20, left: 0, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#21262d" vertical={false} />
              <XAxis
                dataKey="taskId"
                stroke="#8b949e"
                fontSize={11}
                tickLine={false}
                axisLine={{ stroke: '#30363d' }}
              />
              <YAxis
                stroke="#8b949e"
                fontSize={11}
                tickLine={false}
                axisLine={{ stroke: '#30363d' }}
                tickFormatter={(val) => `$${val >= 1 ? val.toFixed(2) : val.toFixed(3)}`}
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
      </div>

      {/* Per-Task Run Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-4 pt-4 border-t border-surface-border text-xs">
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
                <span className="font-mono text-gray-200">
                  ${d.baselineCost >= 1 ? d.baselineCost.toFixed(2) : d.baselineCost.toFixed(4)}
                </span>
              </div>
              <div className="flex justify-between">
                <span>ICM Pipeline (n={d.icmN}):</span>
                <span className="font-mono text-emerald-400">
                  ${d.icmCost >= 1 ? d.icmCost.toFixed(2) : d.icmCost.toFixed(4)}
                </span>
              </div>
              <div className="flex justify-between pt-1 border-t border-surface-border/50 text-gray-300 font-medium">
                <span>{isScaled ? 'Net Savings/Vol:' : 'Net Savings/Run:'}</span>
                <span className="font-mono text-emerald-300">
                  +${d.savingsUsd >= 1 ? d.savingsUsd.toFixed(2) : d.savingsUsd.toFixed(4)}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
