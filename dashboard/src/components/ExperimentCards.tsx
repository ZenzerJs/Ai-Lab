import React from 'react';
import { FlaskConical, ChevronRight, BadgeCheck } from 'lucide-react';
import { TaskSummaryItem } from '../types';
import { formatCurrency, formatSignedCurrency, formatTokens } from '../lib/formatters';

interface ExperimentCardsProps {
  tasks: TaskSummaryItem[];
}

interface CardData {
  taskId: string;
  runs: number;
  baselineN: number;
  icmN: number;
  costDelta: number;
  savingsPct: number;
  baseCache: number;
  icmCache: number;
  baseCachePct: number;
  icmCachePct: number;
  baseLatency: number;
  icmLatency: number;
}

function toCardData(t: TaskSummaryItem): CardData {
  const b = t.arms.baseline;
  const i = t.arms.icm;
  const bTotal = (b?.mean_input_tokens ?? 0) + (b?.mean_cache_read_tokens ?? 0);
  const iTotal = (i?.mean_input_tokens ?? 0) + (i?.mean_cache_read_tokens ?? 0);
  return {
    taskId: t.task_id,
    runs: t.total_runs,
    baselineN: b?.n ?? 0,
    icmN: i?.n ?? 0,
    costDelta: t.savings?.mean_savings_usd ?? 0,
    savingsPct: t.savings?.mean_savings_percent ?? 0,
    baseCache: b?.mean_cache_read_tokens ?? 0,
    icmCache: i?.mean_cache_read_tokens ?? 0,
    baseCachePct: bTotal > 0 ? ((b?.mean_cache_read_tokens ?? 0) / bTotal) * 100 : 0,
    icmCachePct: iTotal > 0 ? ((i?.mean_cache_read_tokens ?? 0) / iTotal) * 100 : 0,
    baseLatency: b?.mean_duration_seconds ?? 0,
    icmLatency: i?.mean_duration_seconds ?? 0,
  };
}

export const ExperimentCards: React.FC<ExperimentCardsProps> = ({ tasks }) => {
  if (!tasks || tasks.length === 0) {
    return null;
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-5 font-mono">
      {tasks.map((t) => {
        const d = toCardData(t);
        const cacheLabel =
          d.baseCache > 0 || d.icmCache > 0
            ? `${d.baseCachePct.toFixed(1)}% → ${d.icmCachePct.toFixed(1)}%`
            : '—';
        const savingsPositive = d.savingsPct >= 0;
        return (
          <article
            key={d.taskId}
            className="p-5 rounded-xl bg-surface border border-surface-border flex flex-col justify-between space-y-4"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <FlaskConical className="size-4 text-primary-light" />
                  <h3 className="text-sm font-bold text-white">{d.taskId}</h3>
                  <span className="px-2 py-0.5 rounded text-[10px] bg-card text-primary-light border border-surface-border">
                    {d.runs} Runs Calibrated
                  </span>
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  Baseline n={d.baselineN} · ICM n={d.icmN} (paired runs)
                </p>
              </div>
              <span
                className={`text-xs font-semibold px-2 py-1 rounded border whitespace-nowrap ${
                  savingsPositive
                    ? 'text-sage bg-sage/10 border-sage/30'
                    : 'text-danger bg-danger/10 border-danger/30'
                }`}
              >
                {savingsPositive ? '-' : '+'}
                {Math.abs(d.savingsPct).toFixed(1)}% Cost
              </span>
            </div>

            <div className="grid grid-cols-3 gap-3 text-xs bg-card/70 p-3 rounded-lg border border-surface-border">
              <div>
                <span className="text-muted-foreground block text-[10px] uppercase">Cost Delta</span>
                <span
                  className={`font-semibold tabular-nums ${
                    d.costDelta >= 0 ? 'text-sage' : 'text-danger'
                  }`}
                >
                  {formatSignedCurrency(d.costDelta)}
                </span>
              </div>
              <div>
                <span className="text-muted-foreground block text-[10px] uppercase">Cache Share</span>
                <span className="text-primary-light font-semibold tabular-nums">{cacheLabel}</span>
              </div>
              <div>
                <span className="text-muted-foreground block text-[10px] uppercase">Latency</span>
                <span className="text-white font-semibold tabular-nums">
                  {d.baseLatency.toFixed(1)}s → {d.icmLatency.toFixed(1)}s
                </span>
              </div>
            </div>

            <div className="text-xs text-muted-foreground leading-relaxed flex flex-col gap-1.5">
              <div className="flex justify-between">
                <span>Mean cache read (baseline)</span>
                <span className="text-baseline tabular-nums">{formatTokens(d.baseCache)}</span>
              </div>
              <div className="flex justify-between">
                <span>Mean cache read (ICM)</span>
                <span className="text-primary-light tabular-nums">{formatTokens(d.icmCache)}</span>
              </div>
              <div className="flex justify-between">
                <span>Mean cost (baseline / ICM)</span>
                <span className="text-white tabular-nums">
                  {formatCurrency(t.arms.baseline?.mean_cost_usd ?? 0)} /{' '}
                  {formatCurrency(t.arms.icm?.mean_cost_usd ?? 0)}
                </span>
              </div>
            </div>

            <div className="pt-3 border-t border-surface-border flex items-center justify-between text-[11px] text-muted-foreground">
              <span className="flex items-center gap-1.5">
                <BadgeCheck className="size-3.5 text-sage" />
                Fairness invariants enforced by runner
              </span>
              <span className="flex items-center gap-1 text-primary">
                <ChevronRight className="size-3.5" />
                Raw Evidence tab
              </span>
            </div>
          </article>
        );
      })}
    </div>
  );
};
