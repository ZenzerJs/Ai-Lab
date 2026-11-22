import { useMemo, useState } from "react";
import { ArrowUpRight, FlaskConical, Sigma } from "lucide-react";
import { DashboardPayload, RunRecord, TaskSummaryItem } from "../../types";
import {
  armNames,
  experimentNames,
  finite,
} from "../../lib/workspace";
import {
  applyFdrToRows,
  CostScope,
  costSourceBreakdown,
  isPricedRun,
  matchedArmComparison,
  MIN_PAIRS_FOR_EFFECT,
  modelFamilySummaries,
  pairedDiffStats,
  PairedStats,
  PairMatchResult,
  pricedShare,
  primaryEffectMetric,
  scopeRuns,
  suitePairsDetailed,
} from "../../lib/analytics";
import { formatArm, formatCurrency, formatSignedPercent, formatTokens } from "../../lib/formatters";

const totalTokensMetric = (r: RunRecord) => (finite(r.total_tokens) ? r.total_tokens : null);
const costMetric = (r: RunRecord) => (isPricedRun(r) ? (r.cost_usd as number) : null);

interface SuiteEffectRow {
  task: TaskSummaryItem;
  arm: string;
  metricLabel: "Cost" | "Tokens";
  stats: PairedStats;
  pairMatch: PairMatchResult;
  cardKey: string;
  rowModel: string;
}

function EffectBadges({ stats }: { stats: PairedStats }) {
  const dz = stats.displayCohensDz;
  const fdrSig = stats.fdrSignificant;
  return (
    <span className="effect-badges">
      {stats.preliminary ? (
        <span className="badge badge-amber">
          preliminary (n={stats.n})
        </span>
      ) : stats.displayEffectSize ? (
        <span className="badge badge-blue">
          d<sub>z</sub> {dz != null ? Math.abs(dz).toFixed(2) : "—"} ·{" "}
          {stats.displayEffectSize} (n={stats.n})
        </span>
      ) : (
        <span className="badge badge-neutral">effect n/a (n={stats.n})</span>
      )}
      {fdrSig != null ? (
        <span className={`badge ${fdrSig ? "badge-green" : "badge-amber"}`}>
          {fdrSig ? "FDR significant" : "FDR not significant"}
          {stats.fdrAdjustedP != null ? ` (q=${stats.fdrAdjustedP.toFixed(3)})` : ""}
        </span>
      ) : stats.significant === null ? (
        <span className="badge badge-neutral">insufficient pairs</span>
      ) : stats.significant ? (
        <span className="badge badge-green">exploratory significant</span>
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
  const costBreakdown = useMemo(() => costSourceBreakdown(runs), [runs]);
  const share = useMemo(() => pricedShare(runs), [runs]);
  const primaryMetric = useMemo(() => primaryEffectMetric(share), [share]);
  const families = useMemo(
    () => modelFamilySummaries(runs, scope),
    [runs, scope],
  );
  const liteComparison = useMemo(
    () => matchedArmComparison(data.tasks, "icm_lite", "baseline", scope),
    [data.tasks, scope],
  );
  const { effectRows, totalDroppedPairs, totalHashMismatched } = useMemo(() => {
    const rows: SuiteEffectRow[] = [];
    let dropped = 0;
    let hashMismatched = 0;
    for (const task of data.tasks || []) {
      const rowModel =
        task.model ||
        task.arms.baseline?.model ||
        armNames(task)
          .map((n) => task.arms[n]?.model)
          .find(Boolean) ||
        "";
      for (const name of armNames(task).filter((n) => n !== "baseline")) {
        const cardKey = task.series_id || `${task.task_id}::${rowModel}`;
        const costMatch = suitePairsDetailed(task, name, costMetric, scope);
        const tokenMatch = suitePairsDetailed(task, name, totalTokensMetric, scope);
        const costStats = pairedDiffStats(costMatch.pairs);
        const tokenStats = pairedDiffStats(tokenMatch.pairs);
        let chosen: [PairedStats | null, PairMatchResult, "Cost" | "Tokens"];
        if (scope === "priced" || scope === "billed_direct" || scope === "estimated_acu_derived") {
          chosen = [costStats, costMatch, "Cost"];
        } else if (scope === "unpriced") {
          chosen = [tokenStats, tokenMatch, "Tokens"];
        } else if (primaryMetric === "Tokens") {
          chosen = tokenStats
            ? [tokenStats, tokenMatch, "Tokens"]
            : costStats
              ? [costStats, costMatch, "Cost"]
              : [null, tokenMatch, "Tokens"];
        } else {
          chosen = costStats
            ? [costStats, costMatch, "Cost"]
            : tokenStats
              ? [tokenStats, tokenMatch, "Tokens"]
              : [null, costMatch, "Cost"];
        }
        const [stats, pairMatch, label] = chosen;
        dropped += pairMatch.droppedCount;
        hashMismatched += pairMatch.hashMismatchedCount;
        if (stats) {
          rows.push({ task, arm: name, metricLabel: label, stats, pairMatch, cardKey, rowModel });
        }
      }
    }
    const sorted = rows.sort((a, b) => {
      const d = (b.stats.meanDeltaPct ?? 0) - (a.stats.meanDeltaPct ?? 0);
      return d || a.task.task_id.localeCompare(b.task.task_id);
    });
    return {
      effectRows: applyFdrToRows(sorted),
      totalDroppedPairs: dropped,
      totalHashMismatched: hashMismatched,
    };
  }, [data.tasks, scope, primaryMetric]);
  const significantCount = effectRows.filter(
    (r) => r.stats.fdrSignificant === true,
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
            <option value="priced">Priced only (Direct + ACU)</option>
            <option value="billed_direct">Direct Billed only</option>
            <option value="estimated_acu_derived">ACU Derived only</option>
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
          <span>Direct Billed</span>
          <strong>{costBreakdown.directBilled}</strong>
        </div>
        <div>
          <span>ACU Derived</span>
          <strong>
            {costBreakdown.acuDerived}
            {costBreakdown.totalAcus > 0
              ? ` (${costBreakdown.totalAcus.toFixed(2)} ACU)`
              : ""}
          </strong>
        </div>
        <div>
          <span>Unpriced scale runs</span>
          <strong>{costBreakdown.unpriced}</strong>
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
              Strict pairing on (task_id, model, run_index, evaluator_hash) ·
              primary metric: <strong>{primaryMetric}</strong>
              {primaryMetric === "Tokens" && share != null && share < 100
                ? ` (priced coverage ${share.toFixed(1)}% < 100%)`
                : ""}{" "}
              · Benjamini-Hochberg FDR across suites · unadjusted 95% CIs are exploratory
            </p>
          </div>
          <span className={`badge ${significantCount ? "badge-green" : "badge-neutral"}`}>
            {effectRows.length} comparisons · {significantCount} FDR significant
            {totalDroppedPairs > 0
              ? ` · ${totalDroppedPairs} dropped (${totalHashMismatched} hash mismatch)`
              : " · 0 dropped pairs"}
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
                <th scope="col">Pairs (dropped)</th>
                <th scope="col">Baseline → governed</th>
                <th scope="col">Mean Δ</th>
                <th scope="col">95% CI Δ (exploratory)</th>
                <th scope="col">Effect · BH FDR significance</th>
              </tr>
            </thead>
            <tbody>
              {effectRows.map(({ task, arm, metricLabel: label, stats, pairMatch, cardKey, rowModel }) => (
                <tr key={`${cardKey}::${arm}`}>
                  <th scope="row">
                    {task.task_id}
                    <span className="cell-subtitle">
                      {experimentNames[task.task_id] || "Experiment"} ·{" "}
                      {formatArm(arm)}
                      {rowModel ? ` · ${rowModel}` : ""}
                    </span>
                  </th>
                  <td>{label}</td>
                  <td>
                    n={stats.n}
                    {pairMatch.droppedCount > 0 && (
                      <span className="cell-subtitle">
                        {pairMatch.droppedCount} dropped
                        {pairMatch.hashMismatchedCount > 0
                          ? ` (${pairMatch.hashMismatchedCount} hash mismatch)`
                          : ""}
                      </span>
                    )}
                  </td>
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
          Cohen&apos;s d<sub>z</sub> requires n ≥ {MIN_PAIRS_FOR_EFFECT} matched pairs; suites below{" "}
          {MIN_PAIRS_FOR_EFFECT} pairs are marked preliminary. Significance uses
          Benjamini-Hochberg FDR across suites; bootstrap 95% CIs are unadjusted
          and exploratory.
        </p>
      </section>
      {liteComparison.sharedTaskIds.length > 0 && (
        <section
          className="panel operational-panel"
          aria-labelledby="icm-lite-matched-title"
        >
          <div className="panel-heading">
            <div>
              <span className="eyebrow">MATCHED ARM COMPARISON</span>
              <h2 id="icm-lite-matched-title">
                ICM-Lite vs Baseline (matched shared tasks only)
              </h2>
              <p>
                Restricted to the {liteComparison.sharedTaskIds.length} shared tasks
                ({liteComparison.sharedTaskIds.join(", ")}) where both arms ran;{" "}
                {liteComparison.excludedUnsharedTaskCount} unshared baseline tasks excluded.
              </p>
            </div>
            <span className="badge badge-purple">
              {liteComparison.sharedSeriesCount} shared series ·{" "}
              {liteComparison.tokenPairs.pairs.length} token pairs
              {liteComparison.tokenPairs.droppedCount > 0
                ? ` · ${liteComparison.tokenPairs.droppedCount} dropped`
                : ""}
            </span>
          </div>
          <div className="ledger-summary" aria-label="Matched ICM-Lite summary">
            <div>
              <span>Matched token delta</span>
              <strong>
                {liteComparison.tokenStats?.meanDeltaPct != null
                  ? formatSignedPercent(liteComparison.tokenStats.meanDeltaPct)
                  : "—"}
              </strong>
              <span>n={liteComparison.tokenStats?.n ?? 0}</span>
            </div>
            <div>
              <span>Matched cost delta</span>
              <strong>
                {liteComparison.costStats?.meanDeltaPct != null
                  ? formatSignedPercent(liteComparison.costStats.meanDeltaPct)
                  : "Unpriced"}
              </strong>
              <span>n={liteComparison.costStats?.n ?? 0}</span>
            </div>
            <div>
              <span>Token effect</span>
              <strong>
                {liteComparison.tokenStats
                  ? liteComparison.tokenStats.preliminary
                    ? `preliminary (n=${liteComparison.tokenStats.n})`
                    : liteComparison.tokenStats.displayEffectSize
                      ? `dz ${Math.abs(liteComparison.tokenStats.displayCohensDz!).toFixed(2)} · ${liteComparison.tokenStats.displayEffectSize} (n=${liteComparison.tokenStats.n})`
                      : `n/a (n=${liteComparison.tokenStats.n})`
                  : "—"}
              </strong>
            </div>
          </div>
        </section>
      )}
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
                <th scope="col">Cost basis</th>
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
                    <span
                      className={`badge ${
                        f.costBasis === "Direct Billed"
                          ? "badge-green"
                          : f.costBasis === "ACU Derived"
                            ? "badge-blue"
                            : f.costBasis === "Direct Billed + ACU Derived"
                              ? "badge-purple"
                              : "badge-neutral"
                      }`}
                    >
                      {f.costBasis}
                    </span>
                    {f.totalAcus > 0 && (
                      <span className="cell-subtitle">
                        {f.totalAcus.toFixed(2)} ACU
                      </span>
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
        <FlaskConical size={13} /> Pairing requires matching (task_id, model,
        run_index, evaluator_hash) within each suite and arm; imported records
        are excluded from family totals. Inspect per-run provenance in the{" "}
        <a className="text-link" href="#audit">
          evidence ledger <ArrowUpRight size={13} />
        </a>
        .
      </p>
    </>
  );
}
