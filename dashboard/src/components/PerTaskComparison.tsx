import React, { useState, useMemo } from 'react';
import { TaskSummaryItem } from '../types';
import { ScaleMode } from './ScaleSelector';
import { DollarSign, AlertCircle, Layers, BarChart2 } from 'lucide-react';
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
  comparisonArmName: string;
  model: string;
  baselineCost: number;
  baselineN: number;
  governedCost: number;
  governedN: number;
  savingsPct: number | null;
  savingsUsd: number | null;
}

/** Horizontal HTML bar meters ported from the code.html prototype (Base vs Governed per task). */
export const PerTaskComparison: React.FC<PerTaskComparisonProps> = ({ tasks, scaleMode }) => {
  const [viewMode, setViewMode] = useState<'task' | 'pooled'>('task');

  const chartData = useMemo<TaskRowModel[]>(() => {
    if (!tasks) return [];
    const mult = scaleMode === '1m' ? 1 : scaleMode === '10m' ? 10 : scaleMode === '100m' ? 100 : 1;
    const isScaled = scaleMode !== '1x';

    return tasks.map((t) => {
      const b = t.arms.baseline;
      const comparisonArmKey = Object.keys(t.arms).find((k) => k !== 'baseline') || 'icm';
      const i = t.arms[comparisonArmKey];
      const comparisonArmName =
        comparisonArmKey === 'icm'
          ? 'ICM'
          : comparisonArmKey === 'icm-subagents'
          ? 'ICM Subagents'
          : comparisonArmKey;

      const hasBothArms = Boolean(
        b &&
        i &&
        (b.n ?? 0) > 0 &&
        (i.n ?? 0) > 0 &&
        b.mean_cost_usd !== null &&
        b.mean_cost_usd !== undefined &&
        i.mean_cost_usd !== null &&
        i.mean_cost_usd !== undefined
      );

      let bMean = b?.mean_cost_usd ?? 0;
      let iMean = i?.mean_cost_usd ?? 0;
      let savingsUsd: number | null = null;
      let savingsPct: number | null = null;

      if (hasBothArms) {
        savingsUsd =
          t.savings?.mean_savings_usd !== null && t.savings?.mean_savings_usd !== undefined
            ? t.savings.mean_savings_usd
            : bMean - iMean;

        if (isScaled) {
          const rawBMean = b?.mean_cost_usd ?? 0;
          const rawIMean = i?.mean_cost_usd ?? 0;
          const scaledBMean = (t.savings?.cost_per_mtok_baseline ?? (rawBMean * 20)) * mult;
          const scaledIMean = (t.savings?.cost_per_mtok_icm ?? (rawIMean * 20)) * mult;

          bMean = scaledBMean;
          iMean = scaledIMean;
          savingsUsd =
            t.savings?.savings_usd_per_mtok !== null && t.savings?.savings_usd_per_mtok !== undefined
              ? t.savings.savings_usd_per_mtok * mult
              : (bMean - iMean);
        }

        if (
          t.savings?.mean_savings_percent !== null &&
          t.savings?.mean_savings_percent !== undefined &&
          Number.isFinite(t.savings.mean_savings_percent)
        ) {
          savingsPct = t.savings.mean_savings_percent;
        } else if (bMean > 0) {
          savingsPct = ((bMean - iMean) / bMean) * 100;
        }
      } else {
        // Missing arm: savings is undefined; do not invent 100% savings or zero baseline
        savingsUsd = null;
        savingsPct = null;
        if (isScaled) {
          const rawBMean = b?.mean_cost_usd ?? 0;
          const rawIMean = i?.mean_cost_usd ?? 0;
          bMean = (t.savings?.cost_per_mtok_baseline ?? (rawBMean * 20)) * mult;
          iMean = (t.savings?.cost_per_mtok_icm ?? (rawIMean * 20)) * mult;
        }
      }

      return {
        taskId: t.task_id,
        comparisonArmName,
        model: b?.model || i?.model || 'unknown',
        baselineCost: Number(bMean.toFixed(5)),
        baselineN: b?.n ?? 0,
        governedCost: Number(iMean.toFixed(5)),
        governedN: i?.n ?? 0,
        savingsPct,
        savingsUsd,
      };
    });
  }, [tasks, scaleMode]);

  // Explicit Pooled Summary calculations - pools strictly paired tasks
  const pooledSummary = useMemo(() => {
    let totalBaseCost = 0;
    let totalGovCost = 0;
    let totalBaseRuns = 0;
    let totalGovRuns = 0;
    let pairedTaskCount = 0;

    for (const d of chartData) {
      totalBaseRuns += d.baselineN;
      totalGovRuns += d.governedN;
      // Only pool costs for tasks where BOTH arms are present and evaluated
      if (d.baselineN > 0 && d.governedN > 0 && d.savingsUsd !== null) {
        totalBaseCost += d.baselineCost;
        totalGovCost += d.governedCost;
        pairedTaskCount += 1;
      }
    }

    const netSavingsUsd = pairedTaskCount > 0 ? (totalBaseCost - totalGovCost) : null;
    const netSavingsPct =
      pairedTaskCount > 0 && totalBaseCost > 0 ? (netSavingsUsd! / totalBaseCost) * 100 : null;

    return {
      totalBaseCost,
      totalGovCost,
      totalBaseRuns,
      totalGovRuns,
      netSavingsUsd,
      netSavingsPct,
      taskCount: chartData.length,
      pairedTaskCount,
    };
  }, [chartData]);

  const maxCost = useMemo(
    () => Math.max(1e-9, ...chartData.map((d) => Math.max(d.baselineCost, d.governedCost))),
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
    <Card className="h-full flex flex-col font-mono">
      <div className="flex flex-col flex-1">
        <CardHeader className="flex flex-col gap-2 pb-3">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <DollarSign className="size-4 text-sage" />
              <CardTitle>{titleText}</CardTitle>
            </div>
            <div className="flex items-center gap-2">
              {/* View Toggle */}
              <div className="inline-flex p-0.5 rounded-lg bg-surface border border-surface-border text-xs">
                <button
                  type="button"
                  onClick={() => setViewMode('task')}
                  className={`px-2.5 py-1 rounded text-xs font-mono transition-colors flex items-center gap-1.5 ${
                    viewMode === 'task'
                      ? 'bg-card text-white font-semibold shadow-sm'
                      : 'text-muted-foreground hover:text-white'
                  }`}
                >
                  <BarChart2 className="size-3" />
                  <span>Tasks ({chartData.length})</span>
                </button>
                <button
                  type="button"
                  onClick={() => setViewMode('pooled')}
                  className={`px-2.5 py-1 rounded text-xs font-mono transition-colors flex items-center gap-1.5 ${
                    viewMode === 'pooled'
                      ? 'bg-card text-white font-semibold shadow-sm'
                      : 'text-muted-foreground hover:text-white'
                  }`}
                >
                  <Layers className="size-3" />
                  <span>Pooled Summary</span>
                </button>
              </div>

              <Badge variant="outline" className="font-normal font-mono text-xs">
                {isScaled ? 'USD / Scaled Volume' : 'USD / Run'}
              </Badge>
            </div>
          </div>
          <CardDescription>
            {isScaled
              ? `Extrapolated economics at ${scaleMode.toUpperCase()} token volume based on empirical cache rates.`
              : 'Mean expenditure per task across recorded runs.'}
          </CardDescription>
        </CardHeader>

        <CardContent className="pt-2">
          {viewMode === 'pooled' ? (
            /* Explicit Pooled Summary View */
            <div className="space-y-4 py-2" data-testid="pooled-summary-view">
              <div className="p-4 rounded-xl bg-card border border-surface-border space-y-3">
                <div className="flex items-center justify-between border-b border-surface-border pb-2.5">
                  <div className="flex items-center gap-2">
                    <Layers className="size-4 text-primary-light" />
                    <span className="font-bold text-white text-sm">
                      Pooled Cross-Task Financial Summary
                    </span>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {pooledSummary.taskCount} tasks · {pooledSummary.totalBaseRuns + pooledSummary.totalGovRuns} paired runs
                  </span>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-1">
                  <div className="p-2.5 rounded-lg bg-surface border border-surface-border">
                    <span className="text-[10px] text-muted-foreground uppercase block">Total Baseline Cost</span>
                    <span className="text-white font-bold text-sm">
                      {formatCurrency(pooledSummary.totalBaseCost)}
                    </span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-surface border border-surface-border">
                    <span className="text-[10px] text-muted-foreground uppercase block">Total Governed Cost</span>
                    <span className="text-primary-light font-bold text-sm">
                      {formatCurrency(pooledSummary.totalGovCost)}
                    </span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-surface border border-surface-border">
                    <span className="text-[10px] text-muted-foreground uppercase block">Pooled Net Savings</span>
                    <span className={`font-bold text-sm ${pooledSummary.netSavingsUsd !== null && pooledSummary.netSavingsUsd >= 0 ? 'text-sage' : (pooledSummary.netSavingsUsd !== null ? 'text-danger' : 'text-muted-foreground')}`}>
                      {formatSignedCurrency(pooledSummary.netSavingsUsd)}
                    </span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-surface border border-surface-border">
                    <span className="text-[10px] text-muted-foreground uppercase block">Pooled Savings %</span>
                    <span className={`font-bold text-sm ${pooledSummary.netSavingsPct !== null && pooledSummary.netSavingsPct >= 0 ? 'text-sage' : 'text-danger'}`}>
                      {pooledSummary.netSavingsPct !== null ? `${pooledSummary.netSavingsPct.toFixed(1)}%` : '—'}
                    </span>
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-surface/70 border border-surface-border text-xs text-muted-foreground space-y-1">
                  <strong className="text-gray-300 block">Explicit Pooling Methodology:</strong>
                  <p className="leading-relaxed text-[11px]">
                    Ratio-of-sums aggregation: <code>(Σ Cost_Baseline − Σ Cost_Governed) / Σ Cost_Baseline</code>, weighting each task by its empirical token volume rather than computing an unweighted arithmetic mean of per-task percentages.
                  </p>
                </div>
              </div>
            </div>
          ) : (
            /* Task-Level Bar View */
            <div className="space-y-4">
              {/* Legend */}
              <div className="flex items-center gap-3.5 text-xs mb-3">
                <span className="flex items-center gap-1.5 text-baseline">
                  <span className="w-2.5 h-2.5 rounded bg-baseline inline-block" /> Baseline Cost
                </span>
                <span className="flex items-center gap-1.5 text-primary-light">
                  <span className="w-2.5 h-2.5 rounded bg-primary inline-block" /> Governed Cost
                </span>
              </div>

              {/* Horizontal bar meters */}
              <div className="space-y-4 pt-1">
                {chartData.map((d) => {
                  const baseWidthPct = Math.max(2, (d.baselineCost / maxCost) * 100);
                  const govWidthPct = Math.max(2, (d.governedCost / maxCost) * 100);
                  const isReduced = d.savingsPct !== null && d.savingsPct > 0.05;

                  return (
                    <div
                      key={d.taskId}
                      data-task-id={d.taskId}
                      className="interactive-task-row p-2.5 rounded-lg border border-surface-border/40 bg-card/50 transition-opacity hover:border-primary/40"
                    >
                      <div className="flex justify-between text-xs mb-1.5 gap-2 flex-wrap">
                        <span className="text-gray-200 font-medium flex items-center gap-2">
                          <span className="w-1.5 h-1.5 rounded-full bg-primary-light inline-block" />
                          {d.taskId}
                        </span>
                        <span className="text-sage font-medium tabular-nums">
                          {d.savingsUsd !== null ? formatSignedCurrency(d.savingsUsd) : '—'}
                          {d.savingsPct !== null ? (
                            isReduced ? ` (-${d.savingsPct.toFixed(1)}%)` : ` (+${Math.abs(d.savingsPct).toFixed(1)}%)`
                          ) : (
                            ' (—)'
                          )}
                        </span>
                      </div>
                      <div className="space-y-1.5">
                        <div className="flex items-center text-[11px]">
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
                        <div className="flex items-center text-[11px]">
                          <span className="w-12 text-muted-foreground shrink-0">{d.comparisonArmName}</span>
                          <div className="w-full bg-background h-3.5 rounded overflow-hidden border border-surface-border/40">
                            <div
                              className="bg-primary h-full rounded-sm"
                              style={{ width: `${govWidthPct}%` }}
                            />
                          </div>
                          <span className="w-20 text-right text-primary-light ml-2 tabular-nums shrink-0">
                            {formatCurrency(d.governedCost)}
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </CardContent>
      </div>

      {/* Per-Task Run Summary Cards via CardFooter */}
      <CardFooter className="flex-col items-stretch pt-0 pb-5 mt-auto">
        <Separator className="mb-4" />
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs w-full">
          {chartData.map((d) => {
            const isReduced = d.savingsPct !== null && d.savingsPct > 0.05;
            const isIncreased = d.savingsPct !== null && d.savingsPct < -0.05;
            const badgeVariant = isReduced ? 'success' : isIncreased ? 'destructive' : 'secondary';
            const badgeLabel =
              d.savingsPct !== null
                ? isReduced
                  ? `-${d.savingsPct.toFixed(1)}% Cost`
                  : isIncreased
                  ? `+${Math.abs(d.savingsPct).toFixed(1)}% Cost`
                  : '0.0% Delta'
                : '— Delta';

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
                    <span>{d.comparisonArmName} (n={d.governedN}):</span>
                    <span className="font-mono text-sage">
                      {formatCurrency(d.governedCost)}
                    </span>
                  </div>
                  <div className="flex justify-between pt-1 border-t border-surface-border/50 text-gray-300 font-medium">
                    <span>{isScaled ? 'Net Savings/Vol:' : 'Net Savings/Run:'}</span>
                    <span className={d.savingsUsd !== null && d.savingsUsd >= 0 ? 'font-mono text-sage' : 'font-mono text-red-300'}>
                      {d.savingsUsd !== null ? formatSignedCurrency(d.savingsUsd) : '—'}
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

