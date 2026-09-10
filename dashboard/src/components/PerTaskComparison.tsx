import React, { useMemo } from 'react';
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

interface TaskRowModel {
  taskId: string;
  model: string;
  baselineCost: number;
  baselineN: number;
  icmCost: number;
  icmN: number;
  savingsPct: number;
  savingsUsd: number;
}

/** Horizontal HTML bar meters ported from the code.html prototype (Base vs ICM per task). */
export const PerTaskComparison: React.FC<PerTaskComparisonProps> = ({ tasks, scaleMode }) => {
  const chartData = useMemo<TaskRowModel[]>(() => {
    if (!tasks) return [];
    const mult = scaleMode === '1m' ? 1 : scaleMode === '10m' ? 10 : scaleMode === '100m' ? 100 : 1;
    const isScaled = scaleMode !== '1x';

    return tasks.map((t) => {
      const b = t.arms.baseline;
      const i = t.arms.icm;

      let bMean = b?.mean_cost_usd ?? 0;
      let iMean = i?.mean_cost_usd ?? 0;
      let savingsUsd = t.savings?.mean_savings_usd ?? (bMean - iMean);

      if (isScaled) {
        const rawBMean = b?.mean_cost_usd ?? 0;
        const rawIMean = i?.mean_cost_usd ?? 0;
        const scaledBMean = (t.savings?.cost_per_mtok_baseline ?? (rawBMean * 20)) * mult;
        const scaledIMean = (t.savings?.cost_per_mtok_icm ?? (rawIMean * 20)) * mult;

        bMean = scaledBMean;
        iMean = scaledIMean;
        savingsUsd = (t.savings?.savings_usd_per_mtok ?? (bMean - iMean)) * mult;
      }

      return {
        taskId: t.task_id,
        model: b?.model || i?.model || 'unknown',
        baselineCost: Number(bMean.toFixed(5)),
        baselineN: b?.n ?? 0,
        icmCost: Number(iMean.toFixed(5)),
        icmN: i?.n ?? 0,
        savingsPct: t.savings?.mean_savings_percent ?? (bMean > 0 ? ((bMean - iMean) / bMean) * 100 : 0),
        savingsUsd,
      };
    });
  }, [tasks, scaleMode]);

  const maxCost = useMemo(
    () => Math.max(1e-9, ...chartData.map((d) => Math.max(d.baselineCost, d.icmCost))),
    [chartData],
  );

  const isScaled = scaleMode !== '1x';

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
              <DollarSign className="size-4 text-sage" />
              <CardTitle>{titleText}</CardTitle>
            </div>
            <Badge variant="outline" className="font-normal font-mono text-xs">
              {isScaled ? 'USD / Scaled Volume' : 'USD / Run'}
            </Badge>
          </div>
          <CardDescription>
            {isScaled
              ? `Extrapolated economics at ${scaleMode.toUpperCase()} token volume based on empirical cache rates.`
              : 'Mean expenditure per task across recorded runs.'}
          </CardDescription>
        </CardHeader>

        <CardContent className="pt-4">
          {/* Legend (prototype style) */}
          <div className="flex items-center gap-3.5 text-xs font-mono mb-4">
            <span className="flex items-center gap-1.5 text-baseline">
              <span className="w-2.5 h-2.5 rounded bg-baseline inline-block" /> Baseline Cost
            </span>
            <span className="flex items-center gap-1.5 text-primary-light">
              <span className="w-2.5 h-2.5 rounded bg-primary inline-block" /> ICM Cost
            </span>
          </div>

          {/* Horizontal bar meters (ported from code.html #costTaskRows) */}
          <div className="space-y-4 pt-2">
            {chartData.map((d) => {
              const baseWidthPct = Math.max(2, (d.baselineCost / maxCost) * 100);
              const icmWidthPct = Math.max(2, (d.icmCost / maxCost) * 100);
              const isReduced = d.savingsPct > 0.05;

              return (
                <div
                  key={d.taskId}
                  data-task-id={d.taskId}
                  className="interactive-task-row p-2.5 rounded-lg border border-surface-border/40 cursor-pointer bg-card/50 transition-opacity hover:border-primary/40"
                >
                  <div className="flex justify-between text-xs font-mono mb-1.5 gap-2 flex-wrap">
                    <span className="text-gray-200 font-medium flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-primary-light inline-block" />
                      {d.taskId}
                    </span>
                    <span className="text-sage font-medium tabular-nums">
                      {formatSignedCurrency(d.savingsUsd)}
                      {isReduced ? ` (-${d.savingsPct.toFixed(1)}%)` : ` (+${Math.abs(d.savingsPct).toFixed(1)}%)`}
                    </span>
                  </div>
                  <div className="space-y-1.5">
                    <div className="flex items-center text-[11px] font-mono">
                      <span className="w-12 text-muted-foreground shrink-0">Base</span>
                      <div className="w-full bg-background h-3.5 rounded overflow-hidden border border-surface-border/40">
                        <div
                          className="bg-baseline h-full rounded-sm"
                          style={{ width: `${baseWidthPct}%` }}
                        />
                      </div>
                      <span className="w-20 text-right text-gray-200 ml-2 tabular-nums shrink-0">
                        {formatCurrency(d.baselineCost)}
                      </span>
                    </div>
                    <div className="flex items-center text-[11px] font-mono">
                      <span className="w-12 text-muted-foreground shrink-0">ICM</span>
                      <div className="w-full bg-background h-3.5 rounded overflow-hidden border border-surface-border/40">
                        <div
                          className="bg-primary h-full rounded-sm"
                          style={{ width: `${icmWidthPct}%` }}
                        />
                      </div>
                      <span className="w-20 text-right text-primary-light ml-2 tabular-nums shrink-0">
                        {formatCurrency(d.icmCost)}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
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
                    <span className="font-mono text-sage">
                      {formatCurrency(d.icmCost)}
                    </span>
                  </div>
                  <div className="flex justify-between pt-1 border-t border-surface-border/50 text-gray-300 font-medium">
                    <span>{isScaled ? 'Net Savings/Vol:' : 'Net Savings/Run:'}</span>
                    <span className={d.savingsUsd >= 0 ? 'font-mono text-sage' : 'font-mono text-red-300'}>
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
