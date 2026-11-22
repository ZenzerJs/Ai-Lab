import { ArmName, RunRecord, TaskSummaryItem } from "../types";
import { bootstrapPercentCI, finite } from "./workspace";

/**
 * Cost coverage scope: "priced" runs carry a finite cost_usd (cost-complete),
 * "unpriced" runs are scale runs without a recorded cost (token-only or
 * cost_status unavailable/incomplete). "all" keeps everything.
 */
export type CostScope = "all" | "priced" | "unpriced";

export function isPricedRun(run: RunRecord): boolean {
  return finite(run.cost_usd);
}

export function scopeRuns(
  runs: RunRecord[] | undefined,
  scope: CostScope,
): RunRecord[] {
  const list = runs || [];
  if (scope === "priced") return list.filter(isPricedRun);
  if (scope === "unpriced") return list.filter((r) => !isPricedRun(r));
  return list;
}

export function pricedShare(runs: RunRecord[] | undefined): number | null {
  const list = runs || [];
  if (!list.length) return null;
  return (list.filter(isPricedRun).length / list.length) * 100;
}

/**
 * Vendor family derived from the model id's leading token
 * (claude-sonnet-5-5-low → claude, swe-2-max-lightning → swe).
 */
export function modelFamily(model?: string | null): string {
  const head = model?.trim().toLowerCase().split(/[-\s_]/)[0];
  return head || "unknown";
}

export interface ModelFamilySummary {
  family: string;
  models: string[];
  runs: number;
  pricedRuns: number;
  baselineRuns: number;
  governedRuns: number;
  baselinePassed: number;
  governedPassed: number;
  meanBaselineTokens: number | null;
  meanGovernedTokens: number | null;
  tokenDeltaPct: number | null;
  baselineCostUsd: number | null;
  governedCostUsd: number | null;
  savingsPct: number | null;
}

const runTokens = (r: RunRecord): number | null =>
  finite(r.total_tokens)
    ? r.total_tokens
    : finite(r.input_tokens) || finite(r.output_tokens)
      ? (finite(r.input_tokens) ? r.input_tokens : 0) +
        (finite(r.output_tokens) ? r.output_tokens : 0)
      : null;

export function modelFamilySummaries(
  runs: RunRecord[] | undefined,
  scope: CostScope = "all",
): ModelFamilySummary[] {
  const scoped = scopeRuns(runs, scope).filter(
    (r) => r.source_kind !== "imported",
  );
  const byFamily = new Map<string, RunRecord[]>();
  for (const run of scoped) {
    const family = modelFamily(run.model);
    const list = byFamily.get(family) || [];
    list.push(run);
    byFamily.set(family, list);
  }
  const mean = (values: number[]) =>
    values.length ? values.reduce((a, b) => a + b, 0) / values.length : null;
  const meanCost = (list: RunRecord[]) =>
    mean(list.filter(isPricedRun).map((r) => r.cost_usd as number));
  const passed = (list: RunRecord[]) =>
    list.filter((r) => r.verification_status === "passed").length;
  return Array.from(byFamily.keys())
    .sort()
    .map((family) => {
      const list = byFamily.get(family)!;
      const base = list.filter((r) => r.arm === "baseline");
      const gov = list.filter((r) => r.arm !== "baseline");
      const meanBaselineTokens = mean(
        base.map(runTokens).filter((t): t is number => t != null),
      );
      const meanGovernedTokens = mean(
        gov.map(runTokens).filter((t): t is number => t != null),
      );
      const baselineCostUsd = meanCost(base);
      const governedCostUsd = meanCost(gov);
      return {
        family,
        models: Array.from(new Set(list.map((r) => r.model))).sort(),
        runs: list.length,
        pricedRuns: list.filter(isPricedRun).length,
        baselineRuns: base.length,
        governedRuns: gov.length,
        baselinePassed: passed(base),
        governedPassed: passed(gov),
        meanBaselineTokens,
        meanGovernedTokens,
        tokenDeltaPct:
          meanBaselineTokens != null &&
          meanBaselineTokens > 0 &&
          meanGovernedTokens != null
            ? ((meanBaselineTokens - meanGovernedTokens) / meanBaselineTokens) *
              100
            : null,
        baselineCostUsd,
        governedCostUsd,
        savingsPct:
          baselineCostUsd != null &&
          baselineCostUsd > 0 &&
          governedCostUsd != null
            ? ((baselineCostUsd - governedCostUsd) / baselineCostUsd) * 100
            : null,
      };
    });
}

export type EffectSize = "large" | "medium" | "small" | "negligible";

export interface PairedStats {
  n: number;
  meanBaseline: number;
  meanGoverned: number;
  meanDeltaPct: number | null;
  ci95: [number, number] | null;
  cohensDz: number | null;
  effectSize: EffectSize | null;
  significant: boolean | null;
}

/**
 * Pair baseline and governed runs of one suite by run_index on `metric`
 * (e.g. cost_usd, total_tokens). The pool is the arm's listed runs plus the
 * task's excluded_runs for that arm — excluded records carry the unpriced
 * scale runs (cost_unavailable) and failed attempts — filtered to `scope`.
 * Imported (superseded) records are never paired: their contaminated
 * baselines would reverse the reported direction of savings.
 * Only pairs where both sides carry a finite metric value are kept.
 */
export function suitePairs(
  task: TaskSummaryItem,
  armName: ArmName | string,
  metric: (r: RunRecord) => number | null = (r) =>
    isPricedRun(r) ? (r.cost_usd as number) : null,
  scope: CostScope = "all",
): [number, number][] {
  const pool = (name: string) =>
    scopeRuns(
      [
        ...(task.arms[name]?.runs || []),
        ...(task.excluded_runs || []).filter((r) => r.arm === name),
      ].filter((r) => r.source_kind !== "imported"),
      scope,
    );
  const pairs: [number, number][] = [];
  const baseByIdx = new Map(
    pool("baseline").map((r) => [r.run_index, metric(r)]),
  );
  for (const r of pool(armName)) {
    const b = baseByIdx.get(r.run_index);
    const g = metric(r);
    if (b != null && g != null && finite(b) && finite(g)) pairs.push([b, g]);
  }
  return pairs;
}

/**
 * Paired summary for baseline-vs-governed differences: mean percent change,
 * the deterministic bootstrap 95% CI, Cohen's dz on the paired differences,
 * its conventional size class, and whether the CI excludes zero.
 */
export function pairedDiffStats(
  pairs: [number, number][],
): PairedStats | null {
  const n = pairs.length;
  if (!n) return null;
  const meanBaseline = pairs.reduce((s, [b]) => s + b, 0) / n;
  const meanGoverned = pairs.reduce((s, [, g]) => s + g, 0) / n;
  const meanDeltaPct =
    meanBaseline !== 0
      ? ((meanGoverned - meanBaseline) / Math.abs(meanBaseline)) * 100
      : null;
  const diffs = pairs.map(([b, g]) => b - g);
  const meanDiff = diffs.reduce((a, b) => a + b, 0) / n;
  let cohensDz: number | null = null;
  if (n > 1) {
    const variance =
      diffs.reduce((s, d) => s + (d - meanDiff) ** 2, 0) / (n - 1);
    const sd = Math.sqrt(variance);
    if (sd > 0) cohensDz = meanDiff / sd;
  }
  const ci95 = bootstrapPercentCI(pairs);
  const significant = ci95 ? ci95[0] > 0 || ci95[1] < 0 : null;
  const abs = cohensDz == null ? null : Math.abs(cohensDz);
  const effectSize: EffectSize | null =
    abs == null
      ? null
      : abs >= 0.8
        ? "large"
        : abs >= 0.5
          ? "medium"
          : abs >= 0.2
            ? "small"
            : "negligible";
  return {
    n,
    meanBaseline,
    meanGoverned,
    meanDeltaPct,
    ci95,
    cohensDz,
    effectSize,
    significant,
  };
}
