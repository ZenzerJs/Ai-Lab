import React from 'react';
import { FlaskConical, ChevronRight, BadgeCheck, AlertTriangle } from 'lucide-react';
import { TaskSummaryItem } from '../types';
import { formatCurrency, formatSignedCurrency, formatTokens } from '../lib/formatters';

interface ExperimentCardsProps {
  tasks: TaskSummaryItem[];
}

export const ExperimentCards: React.FC<ExperimentCardsProps> = ({ tasks }) => {
  if (!tasks || tasks.length === 0) {
    return null;
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-5 font-mono">
      {tasks.map((t) => {
        const b = t.arms.baseline;
        const comparisonArmKey = Object.keys(t.arms).find((k) => k !== 'baseline') || 'icm';
        const i = t.arms[comparisonArmKey];
        const comparisonLabel =
          comparisonArmKey === 'icm'
            ? 'ICM'
            : comparisonArmKey === 'icm-subagents'
            ? 'ICM Subagents'
            : comparisonArmKey;

        const bTotal = (b?.mean_input_tokens ?? 0) + (b?.mean_cache_read_tokens ?? 0);
        const iTotal = (i?.mean_input_tokens ?? 0) + (i?.mean_cache_read_tokens ?? 0);

        const baseCache = b?.mean_cache_read_tokens ?? 0;
        const icmCache = i?.mean_cache_read_tokens ?? 0;
        const baseCachePct = bTotal > 0 ? (baseCache / bTotal) * 100 : 0;
        const icmCachePct = iTotal > 0 ? (icmCache / iTotal) * 100 : 0;

        const baseLatency = b?.mean_duration_seconds ?? 0;
        const icmLatency = i?.mean_duration_seconds ?? 0;

        const cacheLabel =
          baseCache > 0 || icmCache > 0
            ? `${baseCachePct.toFixed(1)}% → ${icmCachePct.toFixed(1)}%`
            : '—';

        const hasSavings =
          t.savings?.mean_savings_percent !== null &&
          t.savings?.mean_savings_percent !== undefined &&
          Number.isFinite(t.savings.mean_savings_percent);
        const savingsPct = hasSavings ? (t.savings?.mean_savings_percent as number) : null;
        const savingsPositive = savingsPct !== null && savingsPct >= 0;

        const costDelta =
          t.savings?.mean_savings_usd !== null &&
          t.savings?.mean_savings_usd !== undefined &&
          Number.isFinite(t.savings.mean_savings_usd)
            ? t.savings.mean_savings_usd
            : null;

        const sourceKinds = t.source_kinds || (t.is_demo_report ? ['fixture'] : ['live']);
        const evidenceStatuses = t.evidence_statuses || ['verified'];
        const exclusionReasons = t.exclusion_reasons || [];

        return (
          <article
            key={t.task_id}
            data-testid={`card-${t.task_id}`}
            className="p-5 rounded-xl bg-surface border border-surface-border flex flex-col justify-between space-y-4"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <FlaskConical className="size-4 text-primary-light" />
                  <h3 className="text-sm font-bold text-white">{t.task_id}</h3>
                  <span className="px-2 py-0.5 rounded text-[10px] bg-card text-primary-light border border-surface-border">
                    {t.cost_eligible_count ?? t.total_runs} Eligible / {t.scheduled_count ?? t.total_runs} Sched
                  </span>
                  {sourceKinds.map((src) => (
                    <span
                      key={src}
                      className={`px-1.5 py-0.5 rounded text-[10px] border ${
                        src === 'live'
                          ? 'bg-sage/10 text-sage border-sage/30'
                          : src === 'fixture'
                          ? 'bg-warning/10 text-warning border-warning/30'
                          : 'bg-card text-muted-foreground border-surface-border'
                      }`}
                    >
                      {src}
                    </span>
                  ))}
                  {evidenceStatuses.map((ev) => (
                    <span
                      key={ev}
                      className={`px-1.5 py-0.5 rounded text-[10px] border ${
                        ev === 'verified'
                          ? 'bg-sage/10 text-sage border-sage/30'
                          : 'bg-danger/10 text-danger border-danger/30'
                      }`}
                    >
                      {ev}
                    </span>
                  ))}
                </div>

                {/* Per-Arm Accounting Detail */}
                <div className="text-[11px] text-muted-foreground mt-2 space-y-0.5 font-mono">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="text-gray-300 font-medium">Baseline:</span>
                    <span>eligible n={b?.n ?? 0}</span>
                    <span>·</span>
                    <span>sched={b?.scheduled_count ?? b?.n ?? 0}</span>
                    <span>·</span>
                    <span>verified={b?.verified_count ?? b?.n ?? 0}</span>
                    {((b?.excluded_count ?? 0) > 0 || (b?.failed_count ?? 0) > 0) && (
                      <span className="text-warning">
                        (failed={b?.failed_count ?? 0}, excl={b?.excluded_count ?? 0})
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="text-primary-light font-medium">{comparisonLabel}:</span>
                    <span>eligible n={i?.n ?? 0}</span>
                    <span>·</span>
                    <span>sched={i?.scheduled_count ?? i?.n ?? 0}</span>
                    <span>·</span>
                    <span>verified={i?.verified_count ?? i?.n ?? 0}</span>
                    {((i?.excluded_count ?? 0) > 0 || (i?.failed_count ?? 0) > 0) && (
                      <span className="text-warning">
                        (failed={i?.failed_count ?? 0}, excl={i?.excluded_count ?? 0})
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {savingsPct !== null ? (
                <span
                  className={`text-xs font-semibold px-2 py-1 rounded border whitespace-nowrap ${
                    savingsPositive
                      ? 'text-sage bg-sage/10 border-sage/30'
                      : 'text-danger bg-danger/10 border-danger/30'
                  }`}
                >
                  {savingsPositive ? '-' : '+'}
                  {Math.abs(savingsPct).toFixed(1)}% Cost
                </span>
              ) : (
                <span className="text-xs font-mono px-2 py-1 rounded border bg-card text-muted-foreground border-surface-border whitespace-nowrap">
                  — Cost Delta
                </span>
              )}
            </div>

            {/* Exclusion Reasons Tags if any */}
            {exclusionReasons.length > 0 && (
              <div className="p-2 rounded bg-warning/5 border border-warning/20 flex items-center gap-2 flex-wrap text-[11px] text-warning">
                <AlertTriangle className="size-3.5 shrink-0" />
                <span className="font-semibold">Exclusions:</span>
                {exclusionReasons.map((r) => (
                  <span
                    key={r}
                    className="px-1.5 py-0.5 rounded bg-warning/10 border border-warning/30 font-mono text-[10px]"
                  >
                    {r}
                  </span>
                ))}
              </div>
            )}

            <div className="grid grid-cols-3 gap-3 text-xs bg-card/70 p-3 rounded-lg border border-surface-border">
              <div>
                <span className="text-muted-foreground block text-[10px] uppercase">Cost Delta</span>
                <span
                  className={`font-semibold tabular-nums ${
                    costDelta !== null && costDelta >= 0
                      ? 'text-sage'
                      : costDelta !== null
                      ? 'text-danger'
                      : 'text-muted-foreground'
                  }`}
                >
                  {costDelta !== null ? formatSignedCurrency(costDelta) : '—'}
                </span>
              </div>
              <div>
                <span className="text-muted-foreground block text-[10px] uppercase">Cache Share</span>
                <span className="text-primary-light font-semibold tabular-nums">{cacheLabel}</span>
              </div>
              <div>
                <span className="text-muted-foreground block text-[10px] uppercase">Latency</span>
                <span className="text-white font-semibold tabular-nums">
                  {baseLatency > 0 || icmLatency > 0
                    ? `${baseLatency.toFixed(1)}s → ${icmLatency.toFixed(1)}s`
                    : '—'}
                </span>
              </div>
            </div>

            <div className="text-xs text-muted-foreground leading-relaxed flex flex-col gap-1.5">
              <div className="flex justify-between">
                <span>Mean cache read (baseline)</span>
                <span className="text-baseline tabular-nums">{formatTokens(baseCache)}</span>
              </div>
              <div className="flex justify-between">
                <span>Mean cache read ({comparisonLabel})</span>
                <span className="text-primary-light tabular-nums">{formatTokens(icmCache)}</span>
              </div>
              <div className="flex justify-between">
                <span>Mean cost (baseline / {comparisonLabel})</span>
                <span className="text-white tabular-nums">
                  {formatCurrency(b?.mean_cost_usd ?? null)} /{' '}
                  {formatCurrency(i?.mean_cost_usd ?? null)}
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

