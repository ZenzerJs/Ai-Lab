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
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from './ui/card';
import { Badge } from './ui/badge';
import { Empty, EmptyIcon, EmptyTitle, EmptyDescription } from './ui/empty';
import { Separator } from './ui/separator';
import {
  formatCurrency,
  formatSignedCurrency,
} from '../lib/formatters';

interface PerTaskComparisonProps {
  tasks: TaskSummaryItem[];
  scaleMode: ScaleMode;
}

export const PerTaskComparison: React.FC<PerTaskComparisonProps> = ({ tasks, scaleMode }) => {
  if (!tasks || tasks.length === 0) {
    return (
      <Card>
        <CardContent className="p-0">
          <Empty>
            <EmptyIcon>
              <AlertCircle className="size-6 text-muted-foreground" />
            </EmptyIcon>
            <EmptyTitle>No task comparison data available</EmptyTitle>
            <EmptyDescription>
              Execute benchmark runs across one or more tasks to view side-by-side cost comparisons.
            </EmptyDescription>
          </Empty>
        </CardContent>
      </Card>
    );
  }

  const mult = scaleMode === '1m' ? 1 : scaleMode === '10m' ? 10 : scaleMode === '100m' ? 100 : 1;
  const isScaled = scaleMode !== '1x';

  // Transform data for Recharts grouped bar with empirical error bands
  const chartData = tasks.map((t) => {
    const b = t.arms.baseline;
    const i = t.arms.icm;

    let bMean = b?.mean_cost_usd ?? 0;
    let bMin = b?.min_cost_usd ?? bMean;
    let bMax = b?.max_cost_usd ?? bMean;

    let iMean = i?.mean_cost_usd ?? 0;
    let iMin = i?.min_cost_usd ?? iMean;
    let iMax = i?.max_cost_usd ?? iMean;

    let savingsUsd = t.savings?.mean_savings_usd ?? (bMean - iMean);

    if (isScaled) {
      const rawBMean = b?.mean_cost_usd ?? 0;
      const rawIMean = i?.mean_cost_usd ?? 0;
      const scaledBMean = (t.savings?.cost_per_mtok_baseline ?? (rawBMean * 20)) * mult;
      const scaledIMean = (t.savings?.cost_per_mtok_icm ?? (rawIMean * 20)) * mult;

      const bScaleFactor = rawBMean > 0 ? scaledBMean / rawBMean : mult;
      const iScaleFactor = rawIMean > 0 ? scaledIMean / rawIMean : mult;

      bMean = scaledBMean;
      bMin = b?.min_cost_usd !== undefined ? b.min_cost_usd * bScaleFactor : bMean;
      bMax = b?.max_cost_usd !== undefined ? b.max_cost_usd * bScaleFactor : bMean;

      iMean = scaledIMean;
      iMin = i?.min_cost_usd !== undefined ? i.min_cost_usd * iScaleFactor : iMean;
      iMax = i?.max_cost_usd !== undefined ? i.max_cost_usd * iScaleFactor : iMean;

      savingsUsd = (t.savings?.savings_usd_per_mtok ?? (bMean - iMean)) * mult;
    }

    const baselineErrLow = Math.max(0, Number((bMean - bMin).toFixed(5)));
    const baselineErrHigh = Math.max(0, Number((bMax - bMean).toFixed(5)));
    const icmErrLow = Math.max(0, Number((iMean - iMin).toFixed(5)));
    const icmErrHigh = Math.max(0, Number((iMax - iMean).toFixed(5)));

    return {
      taskId: t.task_id,
      model: b?.model || i?.model || 'unknown',
      baselineCost: Number(bMean.toFixed(5)),
      baselineError: [baselineErrLow, baselineErrHigh],
      baselineN: b?.n ?? 0,
      baselineMin: bMin,
      baselineMax: bMax,
      icmCost: Number(iMean.toFixed(5)),
      icmError: [icmErrLow, icmErrHigh],
      icmN: i?.n ?? 0,
      icmMin: iMin,
      icmMax: iMax,
      savingsPct: t.savings?.mean_savings_percent ?? (bMean > 0 ? ((bMean - iMean) / bMean) * 100 : 0),
      savingsUsd: savingsUsd,
    };
  });

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const item = payload[0].payload;
      return (
        <div className="bg-surface border border-surface-border p-3 rounded-lg shadow-xl text-xs flex flex-col gap-2 min-w-[220px]">
          <div className="font-semibold text-white border-b border-surface-border pb-1">
            Task: {label} ({item.model})
          </div>
          <div className="flex flex-col gap-1">
            <div className="text-red-400">
              <span className="font-medium">Baseline (n={item.baselineN}):</span> {formatCurrency(item.baselineCost)}
              <div className="text-[10px] text-gray-400 pl-2">
                Min: {formatCurrency(item.baselineMin)} | Max: {formatCurrency(item.baselineMax)}
              </div>
            </div>
            <div className="text-emerald-400">
              <span className="font-medium">ICM Pipeline (n={item.icmN}):</span> {formatCurrency(item.icmCost)}
              <div className="text-[10px] text-gray-400 pl-2">
                Min: {formatCurrency(item.icmMin)} | Max: {formatCurrency(item.icmMax)}
              </div>
            </div>
            <div className="pt-1 border-t border-surface-border text-white font-medium flex justify-between">
              <span>Savings:</span>
              <span className={item.savingsUsd >= 0 ? "text-emerald-300 font-mono" : "text-red-300 font-mono"}>
                {formatSignedCurrency(item.savingsUsd)} ({item.savingsPct >= 0 ? `-${item.savingsPct.toFixed(1)}%` : `+${Math.abs(item.savingsPct).toFixed(1)}%`})
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
    <Card className="flex flex-col justify-between">
      <div>
        <CardHeader className="flex flex-col gap-1 pb-3">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <DollarSign className="size-4 text-emerald-400" />
              <CardTitle>{titleText}</CardTitle>
            </div>
            <Badge variant="outline" className="font-normal font-mono text-xs">
              {isScaled ? 'USD / Scaled Volume' : 'USD / Run'}
            </Badge>
          </div>
          <CardDescription>
            {isScaled
              ? `Extrapolated economics at ${scaleMode.toUpperCase()} token volume based on empirical cache rates.`
              : 'Mean expenditure with min–max error bands across individual runs.'}
          </CardDescription>
        </CardHeader>

        <CardContent className="pt-4">
          <div className="min-h-[220px] h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={chartData}
                margin={{ top: 20, right: 20, left: 0, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#1D2433" vertical={false} />
                <XAxis
                  dataKey="taskId"
                  stroke="#75859C"
                  fontSize={11}
                  tickLine={false}
                  axisLine={{ stroke: '#2D3748' }}
                />
                <YAxis
                  stroke="#75859C"
                  fontSize={11}
                  tickLine={false}
                  axisLine={{ stroke: '#2D3748' }}
                  tickFormatter={(val) => formatCurrency(val)}
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
                  fill="#E06C54"
                  radius={[4, 4, 0, 0]}
                >
                  <ErrorBar
                    dataKey="baselineError"
                    width={4}
                    strokeWidth={1.5}
                    stroke="#F1A189"
                    direction="y"
                  />
                </Bar>
                <Bar
                  name="ICM Cost"
                  dataKey="icmCost"
                  fill="#6366F1"
                  radius={[4, 4, 0, 0]}
                >
                  <ErrorBar
                    dataKey="icmError"
                    width={4}
                    strokeWidth={1.5}
                    stroke="#818CF8"
                    direction="y"
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </div>

      {/* Per-Task Run Summary Cards via CardFooter */}
      <CardFooter className="flex-col items-stretch pt-0 pb-5">
        <Separator className="mb-4" />
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs w-full">
          {chartData.map((d) => {
            const isReduced = d.savingsPct > 0.05;
            const isIncreased = d.savingsPct < -0.05;
            const badgeVariant = isReduced ? 'success' : isIncreased ? 'destructive' : 'secondary';
            const badgeLabel = isReduced
              ? `-${d.savingsPct.toFixed(1)}% Cost`
              : isIncreased
              ? `+${Math.abs(d.savingsPct).toFixed(1)}% Cost`
              : '0.0% Delta';

            return (
              <div
                key={d.taskId}
                className="p-3 rounded-lg bg-background/50 border border-surface-border flex flex-col justify-between gap-2"
              >
                <div className="flex justify-between items-center">
                  <span className="font-mono font-medium text-gray-200">{d.taskId}</span>
                  <Badge variant={badgeVariant} className="text-[11px] py-0">
                    {badgeLabel}
                  </Badge>
                </div>
                <div className="flex flex-col gap-1 text-gray-400">
                  <div className="flex justify-between">
                    <span>Baseline (n={d.baselineN}):</span>
                    <span className="font-mono text-gray-200">
                      {formatCurrency(d.baselineCost)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>ICM Pipeline (n={d.icmN}):</span>
                    <span className="font-mono text-emerald-400">
                      {formatCurrency(d.icmCost)}
                    </span>
                  </div>
                  <div className="flex justify-between pt-1 border-t border-surface-border/50 text-gray-300 font-medium">
                    <span>{isScaled ? 'Net Savings/Vol:' : 'Net Savings/Run:'}</span>
                    <span className={d.savingsUsd >= 0 ? "font-mono text-emerald-300" : "font-mono text-red-300"}>
                      {formatSignedCurrency(d.savingsUsd)}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </CardFooter>
    </Card>
  );
};
