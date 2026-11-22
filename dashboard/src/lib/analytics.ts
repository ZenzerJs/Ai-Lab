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

export const MIN_PAIRS_FOR_EFFECT = 5;

export interface PairMatchResult {
  pairs: [number, number][];
  droppedCount: number;
  hashMismatchedCount: number;
  modelMismatchedCount: number;
  unmatchedCount: number;
}

export interface PairedStats {
  n: number;
  meanBaseline: number;
  meanGoverned: number;
  meanDeltaPct: number | null;
  ci95: [number, number] | null;
  ciExploratory: boolean;
  cohensDz: number | null;
  effectSize: EffectSize | null;
  preliminary: boolean;
  displayCohensDz: number | null;
  displayEffectSize: EffectSize | null;
  pValue: number | null;
  fdrAdjustedP?: number | null;
  fdrSignificant?: boolean | null;
  significant: boolean | null;
}

export interface MatchedArmComparison {
  targetArm: string;
  baselineArm: string;
  sharedTaskIds: string[];
  sharedSeriesCount: number;
  excludedUnsharedTaskCount: number;
  tokenPairs: PairMatchResult;
  costPairs: PairMatchResult;
  tokenStats: PairedStats | null;
  costStats: PairedStats | null;
}

/**
 * Unambiguous cost sign label:
 * - negative savingsPct (governed costs more) -> "+X.X% cost"
 * - positive savingsPct (governed costs less) -> "-X.X% savings"
 */
export function formatSignedCostChange(
  savingsPct: number | null | undefined,
  precision = 1,
): string {
  if (!finite(savingsPct)) return "—";
  if (Math.abs(savingsPct) < 0.05) return `0.${"0".repeat(precision)}% cost`;
  if (savingsPct < 0) {
    return `+${Math.abs(savingsPct).toFixed(precision)}% cost`;
  }
  return `-${Math.abs(savingsPct).toFixed(precision)}% savings`;
}

/**
 * Surface tokens as primary effect metric whenever priced coverage < 100%.
 */
export function primaryEffectMetric(
  pricedCoveragePct: number | null,
): "Tokens" | "Cost" {
  if (pricedCoveragePct == null || !Number.isFinite(pricedCoveragePct)) {
    return "Tokens";
  }
  return pricedCoveragePct >= 100 ? "Cost" : "Tokens";
}

function logGamma(z: number): number {
  const coeffs = [
    76.18009172947146,
    -86.50532032941677,
    24.01409824083091,
    -1.231739572450155,
    0.1208650973866179e-2,
    -0.5395239384953e-5,
  ];
  let x = z;
  let y = z;
  let tmp = x + 5.5;
  tmp -= (x + 0.5) * Math.log(tmp);
  let ser = 1.000000000190015;
  for (let j = 0; j < coeffs.length; j++) {
    y += 1;
    ser += coeffs[j] / y;
  }
  return -tmp + Math.log((2.5066282746310005 * ser) / x);
}

function betacf(a: number, b: number, x: number): number {
  const MAXIT = 200;
  const EPS = 3e-12;
  const FPMIN = 1e-30;
  const qab = a + b;
  const qap = a + 1;
  const qam = a - 1;
  let c = 1;
  let d = 1 - (qab * x) / qap;
  if (Math.abs(d) < FPMIN) d = FPMIN;
  d = 1 / d;
  let h = d;
  for (let m = 1; m <= MAXIT; m++) {
    const m2 = 2 * m;
    let aa = (m * (b - m) * x) / ((qam + m2) * (a + m2));
    d = 1 + aa * d;
    if (Math.abs(d) < FPMIN) d = FPMIN;
    c = 1 + aa / c;
    if (Math.abs(c) < FPMIN) c = FPMIN;
    d = 1 / d;
    h *= d * c;
    aa = (-(a + m) * (qab + m) * x) / ((a + m2) * (qap + m2));
    d = 1 + aa * d;
    if (Math.abs(d) < FPMIN) d = FPMIN;
    c = 1 + aa / c;
    if (Math.abs(c) < FPMIN) c = FPMIN;
    d = 1 / d;
    const del = d * c;
    h *= del;
    if (Math.abs(del - 1) < EPS) break;
  }
  return h;
}

function regularizedIncompleteBeta(a: number, b: number, x: number): number {
  if (x <= 0) return 0;
  if (x >= 1) return 1;
  const bt = Math.exp(
    logGamma(a + b) -
      logGamma(a) -
      logGamma(b) +
      a * Math.log(x) +
      b * Math.log(1 - x),
  );
  if (x < (a + 1) / (a + b + 2)) {
    return (bt * betacf(a, b, x)) / a;
  }
  return 1 - (bt * betacf(b, a, 1 - x)) / b;
}

/**
 * Exact two-sided Student's t p-value via the regularized incomplete beta function.
 */
export function studentTTwoSidedP(tStat: number, df: number): number | null {
  if (!Number.isFinite(tStat) || !Number.isFinite(df) || df < 1) return null;
  if (tStat === 0) return 1;
  const x = df / (df + tStat * tStat);
  return Math.max(0, Math.min(1, regularizedIncompleteBeta(df / 2, 0.5, x)));
}

/**
 * Benjamini-Hochberg FDR adjustment across a family of tests.
 */
export function benjaminiHochberg(
  pValues: (number | null)[],
  alpha = 0.05,
): { qValues: (number | null)[]; significant: (boolean | null)[] } {
  const qValues: (number | null)[] = pValues.map(() => null);
  const significant: (boolean | null)[] = pValues.map(() => null);
  const valid = pValues
    .map((p, idx) => ({ p, idx }))
    .filter((item): item is { p: number; idx: number } =>
      item.p != null && Number.isFinite(item.p),
    )
    .sort((a, b) => a.p - b.p);
  const m = valid.length;
  if (!m) return { qValues, significant };

  const adjusted = new Array<number>(m);
  for (let i = m - 1; i >= 0; i--) {
    const rank = i + 1;
    const raw = (valid[i].p * m) / rank;
    adjusted[i] = Math.min(1, i === m - 1 ? raw : Math.min(raw, adjusted[i + 1]));
  }
  for (let i = 0; i < m; i++) {
    const q = Math.max(0, Math.min(1, adjusted[i]));
    qValues[valid[i].idx] = q;
    significant[valid[i].idx] = q <= alpha;
  }
  return { qValues, significant };
}

/**
 * Attach Benjamini-Hochberg FDR-adjusted p-values and significance flags
 * across a list of suite comparison rows.
 */
export function applyFdrToRows<T extends { stats: PairedStats }>(
  rows: T[],
  alpha = 0.05,
): T[] {
  const { qValues, significant } = benjaminiHochberg(
    rows.map((r) => r.stats.pValue),
    alpha,
  );
  return rows.map((row, idx) => ({
    ...row,
    stats: {
      ...row.stats,
      fdrAdjustedP: qValues[idx],
      fdrSignificant: significant[idx],
    },
  }));
}

/**
 * Strict pairing of baseline and governed runs of one suite by
 * (task_id, model, run_index, evaluator_hash) on `metric`.
 * Returns both the matched pairs and counts of dropped / hash-mismatched /
 * model-mismatched / unmatched pairs for transparency in the UI.
 */
export function suitePairsDetailed(
  task: TaskSummaryItem,
  armName: ArmName | string,
  metric: (r: RunRecord) => number | null = (r) =>
    isPricedRun(r) ? (r.cost_usd as number) : null,
  scope: CostScope = "all",
): PairMatchResult {
  const pool = (name: string) =>
    scopeRuns(
      [
        ...(task.arms[name]?.runs || []),
        ...(task.excluded_runs || []).filter((r) => r.arm === name),
      ].filter((r) => r.source_kind !== "imported"),
      scope,
    );

  const normTask = (r: RunRecord) => r.task_id || task.task_id || "";
  const normModel = (r: RunRecord) => r.model || task.model || "";
  const normHash = (r: RunRecord) => r.evaluator_hash ?? "";
  const exactKey = (r: RunRecord) =>
    `${normTask(r)}\0${normModel(r)}\0${r.run_index}\0${normHash(r)}`;
  const taskModelIdxKey = (r: RunRecord) =>
    `${normTask(r)}\0${normModel(r)}\0${r.run_index}`;
  const taskIdxKey = (r: RunRecord) => `${normTask(r)}\0${r.run_index}`;

  const baseRuns = pool("baseline");
  const govRuns = pool(armName);

  const baseByExact = new Map<string, RunRecord>();
  const baseByTaskModelIdx = new Map<string, RunRecord[]>();
  const baseByTaskIdx = new Map<string, RunRecord[]>();

  for (const r of baseRuns) {
    baseByExact.set(exactKey(r), r);
    const tmKey = taskModelIdxKey(r);
    const tmList = baseByTaskModelIdx.get(tmKey) || [];
    tmList.push(r);
    baseByTaskModelIdx.set(tmKey, tmList);
    const tKey = taskIdxKey(r);
    const tList = baseByTaskIdx.get(tKey) || [];
    tList.push(r);
    baseByTaskIdx.set(tKey, tList);
  }

  const pairs: [number, number][] = [];
  let hashMismatchedCount = 0;
  let modelMismatchedCount = 0;
  let unmatchedCount = 0;

  for (const r of govRuns) {
    const exactMatch = baseByExact.get(exactKey(r));
    if (exactMatch) {
      const b = metric(exactMatch);
      const g = metric(r);
      if (b != null && g != null && finite(b) && finite(g)) {
        pairs.push([b, g]);
      } else {
        unmatchedCount += 1;
      }
      continue;
    }
    const sameTaskModelIdx = baseByTaskModelIdx.get(taskModelIdxKey(r));
    if (sameTaskModelIdx && sameTaskModelIdx.length > 0) {
      hashMismatchedCount += 1;
      continue;
    }
    const sameTaskIdx = baseByTaskIdx.get(taskIdxKey(r));
    if (sameTaskIdx && sameTaskIdx.length > 0) {
      modelMismatchedCount += 1;
      continue;
    }
    unmatchedCount += 1;
  }

  return {
    pairs,
    droppedCount: hashMismatchedCount + modelMismatchedCount + unmatchedCount,
    hashMismatchedCount,
    modelMismatchedCount,
    unmatchedCount,
  };
}

/**
 * Pair baseline and governed runs of one suite by
 * (task_id, model, run_index, evaluator_hash) on `metric`
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
  return suitePairsDetailed(task, armName, metric, scope).pairs;
}

/**
 * Paired summary for baseline-vs-governed differences: mean percent change,
 * the deterministic bootstrap 95% CI (labeled exploratory unless FDR-adjusted),
 * Cohen's dz on the paired differences (gated at n >= 5 for display via
 * preliminary / displayCohensDz / displayEffectSize), and two-sided paired t p-value.
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
  let pValue: number | null = null;
  if (n > 1) {
    const variance =
      diffs.reduce((s, d) => s + (d - meanDiff) ** 2, 0) / (n - 1);
    const sd = Math.sqrt(variance);
    if (sd > 0) {
      cohensDz = meanDiff / sd;
      const tStat = meanDiff / (sd / Math.sqrt(n));
      pValue = studentTTwoSidedP(tStat, n - 1);
    } else if (meanDiff === 0) {
      pValue = 1;
    }
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
  const preliminary = n < MIN_PAIRS_FOR_EFFECT;
  return {
    n,
    meanBaseline,
    meanGoverned,
    meanDeltaPct,
    ci95,
    ciExploratory: true,
    cohensDz,
    effectSize,
    preliminary,
    displayCohensDz: preliminary ? null : cohensDz,
    displayEffectSize: preliminary ? null : effectSize,
    pValue,
    significant,
  };
}

/**
 * Compare targetArm (e.g. icm_lite) against baselineArm ONLY on matched shared
 * (task_id, model) tasks so icm_lite is never pooled against harder multi-file
 * suites that did not run icm_lite.
 */
export function matchedArmComparison(
  tasks: TaskSummaryItem[] | undefined,
  targetArm: ArmName | string = "icm_lite",
  baselineArm: ArmName | string = "baseline",
  scope: CostScope = "all",
): MatchedArmComparison {
  const list = tasks || [];
  const sharedTasks: TaskSummaryItem[] = [];
  const allBaselineTaskIds = new Set<string>();

  for (const task of list) {
    const hasBase =
      Boolean(task.arms?.[baselineArm]?.runs?.length) ||
      Boolean((task.excluded_runs || []).some((r) => r.arm === baselineArm));
    const hasTarget =
      Boolean(task.arms?.[targetArm]?.runs?.length) ||
      Boolean((task.excluded_runs || []).some((r) => r.arm === targetArm));
    if (hasBase) allBaselineTaskIds.add(task.task_id);
    if (hasBase && hasTarget) {
      sharedTasks.push(task);
    }
  }

  const sharedTaskIds = Array.from(
    new Set(sharedTasks.map((t) => t.task_id)),
  ).sort();
  const excludedUnsharedTaskCount = Math.max(
    0,
    allBaselineTaskIds.size - sharedTaskIds.length,
  );

  const tokenMetric = (r: RunRecord) => runTokens(r);
  const costMetric = (r: RunRecord) =>
    isPricedRun(r) ? (r.cost_usd as number) : null;

  const mergeResults = (
    metricFn: (r: RunRecord) => number | null,
  ): PairMatchResult => {
    const merged: PairMatchResult = {
      pairs: [],
      droppedCount: 0,
      hashMismatchedCount: 0,
      modelMismatchedCount: 0,
      unmatchedCount: 0,
    };
    for (const task of sharedTasks) {
      const res = suitePairsDetailed(task, targetArm, metricFn, scope);
      merged.pairs.push(...res.pairs);
      merged.droppedCount += res.droppedCount;
      merged.hashMismatchedCount += res.hashMismatchedCount;
      merged.modelMismatchedCount += res.modelMismatchedCount;
      merged.unmatchedCount += res.unmatchedCount;
    }
    return merged;
  };

  const tokenPairs = mergeResults(tokenMetric);
  const costPairs = mergeResults(costMetric);

  return {
    targetArm,
    baselineArm,
    sharedTaskIds,
    sharedSeriesCount: sharedTasks.length,
    excludedUnsharedTaskCount,
    tokenPairs,
    costPairs,
    tokenStats: pairedDiffStats(tokenPairs.pairs),
    costStats: pairedDiffStats(costPairs.pairs),
  };
}

/**
 * Cross-check declared benchmark IDs against measured runs and label any 0-run
 * suite as "suite present, unmeasured".
 */
export function crossCheckBenchmarks(
  declaredIds: string[],
  tasks: TaskSummaryItem[] | undefined,
  runs?: RunRecord[] | undefined,
): { task_id: string; measured_runs: number; status: string }[] {
  const counts = new Map<string, number>();
  if (runs && runs.length > 0) {
    for (const r of runs) {
      if (r.task_id && r.source_kind !== "imported") {
        counts.set(r.task_id, (counts.get(r.task_id) || 0) + 1);
      }
    }
  } else {
    for (const t of tasks || []) {
      if (t.task_id) {
        counts.set(t.task_id, (counts.get(t.task_id) || 0) + (t.total_runs || 0));
      }
    }
  }
  return Array.from(new Set(declaredIds))
    .sort()
    .map((task_id) => {
      const measured_runs = counts.get(task_id) || 0;
      return {
        task_id,
        measured_runs,
        status: measured_runs > 0 ? "measured" : "suite present, unmeasured",
      };
    });
}
