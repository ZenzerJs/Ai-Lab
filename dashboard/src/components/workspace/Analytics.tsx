import { useMemo, useState } from "react";
import { ArrowUpRight, FlaskConical, Sigma } from "lucide-react";
import { DashboardPayload, RunRecord, TaskSummaryItem } from "../../types";
import {
  armNames,
  experimentNames,
  finite,
} from "../../lib/workspace";
import {
  CostScope,
  isPricedRun,
  modelFamilySummaries,
  pairedDiffStats,
  PairedStats,
  pricedShare,
  scopeRuns,
  suitePairs,
} from "../../lib/analytics";
import { formatArm, formatCurrency, formatSignedPercent, formatTokens } from "../../lib/formatters";

const totalTokensMetric = (r: RunRecord) => (finite(r.total_tokens) ? r.total_tokens : null);
const costMetric = (r: RunRecord) => (isPricedRun(r) ? (r.cost_usd as number) : null);

interface SuiteEffectRow {
  task: TaskSummaryItem;
  arm: string;
  metricLabel: "Cost" | "Tokens";
  stats: PairedStats;
}

function EffectBadges({ stats }: { stats: PairedStats }) {
  const dz = stats.cohensDz;
  return (
    <span className="effect-badges">
      {stats.effectSize ? (
        <span className="badge badge-blue">
          d<sub>z</sub> {dz != null ? Math.abs(dz).toFixed(2) : "—"} ·{" "}
          {stats.effectSize}
        </span>
      ) : (
        <span className="badge badge-neutral">effect n/a</span>
      )}
      {stats.significant === null ? (
        <span className="badge badge-neutral">insufficient pairs</span>
      ) : stats.significant ? (
        <span className="badge badge-green">significant</span>
      ) : (
        <span className="badge badge-amber">not significant</span>
      )}
    </span>
  );
}

export default function Analytics({ data }: { data: DashboardPayload }) {
  const [scope, setScope] = useState<CostScope>("all");
  const runs = data.runs || [];
  const scoped = useMemo(() => scopeRuns(runs, scope), [runs, scope]);
  const pricedCount = useMemo(
    () => runs.filter(isPricedRun).length,
    [runs],
  );
  const share = useMemo(() => pricedShare(runs), [runs]);
  const families = useMemo(
    () => modelFamilySummaries(runs, scope),
    [runs, scope],
  );
  const effectRows = useMemo(() => {
    const rows: SuiteEffectRow[] = [];
    for (const task of data.tasks || []) {
      for (const name of armNames(task).filter((n) => n !== "baseline")) {
        const costStats = pairedDiffStats(
          suitePairs(task, name, costMetric, scope),
        );
        const tokenStats = pairedDiffStats(
          suitePairs(task, name, totalTokensMetric, scope),
        );
        const [stats, label] =
          scope === "priced"
            ? [costStats, "Cost" as const]
            : scope === "unpriced"
              ? [tokenStats, "Tokens" as const]
              : costStats
                ? [costStats, "Cost" as const]
                : [tokenStats, "Tokens" as const];
        if (stats) rows.push({ task, arm: name, metricLabel: label, stats });
      }
    }
    return rows.sort((a, b) => {
      const d = (b.stats.meanDeltaPct ?? 0) - (a.stats.meanDeltaPct ?? 0);
      return d || a.task.task_id.localeCompare(b.task.task_id);
    });
  }, [data.tasks, scope]);
  const significantCount = effectRows.filter(
    (r) => r.stats.significant,
  ).length;

  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">DEEP ANALYTICS</div>
          <h1>Inside the numbers.</h1>
          <p>
            Paired effect sizes, significance, and model families—split cleanly
            between cost-complete and unpriced scale runs.
          </p>
        </div>
        <span className="badge badge-purple">
          <Sigma size={14} />
          {runs.length} runs · {pricedCount} priced
        </span>
      </div>
      <div className="toolbar">
        <label className="select-field">
          Cost coverage
          <select
            value={scope}
            onChange={(event) => setScope(event.target.value as CostScope)}
          >
            <option value="all">All runs</option>
            <option value="priced">Priced only</option>
            <option value="unpriced">Unpriced only</option>
          </select>
        </label>
        <span className="result-count" role="status">
          {scoped.length} {scoped.length === 1 ? "run" : "runs"} in scope
        </span>
      </div>
      <section
        className="ledger-summary"
        aria-label="Cost coverage summary"
      >
        <div>
          <span>Runs in scope</span>
          <strong>{scoped.length}</strong>
        </div>
        <div>
          <span>Priced (cost-complete)</span>
          <strong>{pricedCount}</strong>
        </div>
        <div>
          <span>Unpriced scale runs</span>
          <strong>{runs.length - pricedCount}</strong>
        </div>
        <div>
          <span>Priced share</span>
          <strong>
            {share != null ? `${share.toFixed(1)}%` : "—"}
          </strong>
        </div>
      </section>
      <section
        className="panel operational-panel"
        aria-labelledby="suite-effects-title"
      >
        <div className="panel-heading">
          <div>
            <span className="eyebrow">PAIRED EFFECT SIZE</span>
            <h2 id="suite-effects-title">
              Per-suite deltas vs baseline
            </h2>
            <p>
              Runs paired by run_index · deterministic bootstrap 95% CI ·
              Cohen&apos;s d<sub>z</sub> on paired differences
            </p>
          </div>
          <span className={`badge ${significantCount ? "badge-green" : "badge-neutral"}`}>
            {effectRows.length} comparisons · {significantCount} significant
          </span>
        </div>
        <div
          className="table-scroll"
          role="region"
          aria-label="Per-suite paired effect sizes"
          tabIndex={0}
        >
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">Suite · arm</th>
                <th scope="col">Metric</th>
                <th scope="col">Pairs</th>
                <th scope="col">Baseline → governed</th>
                <th scope="col">Mean Δ</th>
                <th scope="col">95% CI Δ</th>
                <th scope="col">Effect · significance</th>
              </tr>
            </thead>
            <tbody>
              {effectRows.map(({ task, arm, metricLabel: label, stats }) => (
                <tr key={`${task.series_id || task.task_id}::${arm}`}>
                  <th scope="row">
                    {task.task_id}
                    <span className="cell-subtitle">
                      {experimentNames[task.task_id] || "Experiment"} ·{" "}
                      {formatArm(arm)}
                    </span>
                  </th>
                  <td>{label}</td>
                  <td>{stats.n}</td>
                  <td>
                    {label === "Cost"
                      ? `${formatCurrency(stats.meanBaseline)} → ${formatCurrency(stats.meanGoverned)}`
                      : `${formatTokens(stats.meanBaseline)} → ${formatTokens(stats.meanGoverned)}`}
                  </td>
                  <td
                    className={
                      stats.meanDeltaPct != null && stats.meanDeltaPct <= 0
                        ? "text-sea"
                        : "text-rust"
                    }
                  >
                    {stats.meanDeltaPct != null
                      ? formatSignedPercent(stats.meanDeltaPct)
                      : "—"}
                  </td>
                  <td>
                    {stats.ci95
                      ? `${formatSignedPercent(stats.ci95[0])} to ${formatSignedPercent(stats.ci95[1])}`
                      : "—"}
                  </td>
                  <td>
                    <EffectBadges stats={stats} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!effectRows.length && (
          <p className="empty-inline">
            No paired runs in this scope.
          </p>
        )}
        <p className="panel-note">
          Significant means the bootstrap CI excludes zero; pairs below two
          runs report a mean delta only. Cohen&apos;s d<sub>z</sub> uses the
          standard deviation of paired differences; 0.2 / 0.5 / 0.8 mark
          small, medium, and large effects.
        </p>
      </section>
      <section
        className="panel operational-panel"
        aria-labelledby="model-family-title"
      >
        <div className="panel-heading">
          <div>
            <span className="eyebrow">MODEL FAMILIES</span>
            <h2 id="model-family-title">
              Breakdown by model family
            </h2>
            <p>
              Live non-imported runs grouped by vendor prefix; priced totals
              only count cost-complete runs in scope.
            </p>
          </div>
          <span className="badge badge-purple">
            {families.length} families
          </span>
        </div>
        <div
          className="table-scroll"
          role="region"
          aria-label="Model family breakdown"
          tabIndex={0}
        >
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">Family</th>
                <th scope="col">Models</th>
                <th scope="col">Runs (priced)</th>
                <th scope="col">Pass (Base / Gov)</th>
                <th scope="col">Mean tokens (Base → Gov)</th>
                <th scope="col">Δ tokens</th>
                <th scope="col">Priced USD (Base → Gov)</th>
                <th scope="col">Savings</th>
              </tr>
            </thead>
            <tbody>
              {families.map((f) => (
                <tr key={f.family}>
                  <th scope="row">{f.family}</th>
                  <td>
                    <span className="cell-subtitle">
                      {f.models.join(", ")}
                    </span>
                  </td>
                  <td>
                    {f.runs}
                    <span className="cell-subtitle">
                      {f.pricedRuns} priced
                    </span>
                  </td>
                  <td>
                    {f.baselinePassed}/{f.baselineRuns} / {f.governedPassed}/
                    {f.governedRuns}
                  </td>
                  <td>
                    {formatTokens(f.meanBaselineTokens)} →{" "}
                    {formatTokens(f.meanGovernedTokens)}
                  </td>
                  <td>
                    {f.tokenDeltaPct != null ? (
                      <span
                        className={
                          f.tokenDeltaPct >= 0 ? "text-sea" : "text-rust"
                        }
                      >
                        {formatSignedPercent(-f.tokenDeltaPct)}
                      </span>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td>
                    {f.baselineCostUsd != null && f.governedCostUsd != null
                      ? `${formatCurrency(f.baselineCostUsd)} → ${formatCurrency(f.governedCostUsd)}`
                      : "Unpriced"}
                  </td>
                  <td>
                    {f.savingsPct != null ? (
                      <span
                        className={f.savingsPct >= 0 ? "text-sea" : "text-rust"}
                      >
                        {formatSignedPercent(f.savingsPct)}
                      </span>
                    ) : (
                      "—"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!families.length && (
          <p className="empty-inline">
            No live runs in this cost scope.
          </p>
        )}
      </section>
      <p className="panel-note">
        <FlaskConical size={13} /> Pairing is by run_index within each suite
        and arm; imported records are excluded from family totals. Inspect
        per-run provenance in the{" "}
        <a className="text-link" href="#audit">
          evidence ledger <ArrowUpRight size={13} />
        </a>
        .
      </p>
    </>
  );
}
