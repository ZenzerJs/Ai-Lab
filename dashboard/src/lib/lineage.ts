import {
  DashboardPayload,
  IterationContractMeta,
  IterationLineageEntry,
  RunRecord,
} from "../types";
import { formatArm } from "./formatters";
import { finite } from "./workspace";

export interface LineagePoint {
  version: string;
  arm: string;
  label: string;
  n_runs: number;
  passed_count: number;
  pass_rate: number | null;
  priced_n_runs: number;
  mean_cost_usd: number | null;
  cost_per_passing_patch_usd: number | null;
  mean_tools: number | null;
  mean_input_tokens: number | null;
  mean_cache_read_tokens: number | null;
  mean_output_tokens: number | null;
  mean_llm_calls: number | null;
  mean_cache_hit_ratio: number | null;
  mean_tools_per_call: number | null;
  total_cache_busts: number | null;
  cost_delta_vs_baseline_pct: number | null;
  hypothesis: string | null;
  changes_from_prev: string[];
  parent_version: string | null;
  execution_strategy: string | null;
}

export interface LineageModelCohort {
  model: string;
  hasPricing: boolean;
  totalRuns: number;
  taskCount: number;
  points: LineagePoint[];
}

export interface LineageEdge {
  from: string;
  to: string;
  kind: "spine" | "branch";
}

const VERSION_ORDER: Record<string, number> = {
  baseline: 0,
  icm_v1: 1,
  icm_v2: 2,
  icm_v3: 3,
  icm_staged: 4,
  icm_lite: 5,
};

const ARM_TO_VERSION: Record<string, string> = {
  baseline: "baseline",
  icm: "icm_v1",
  "icm-subagents": "icm_v1",
  delegation: "icm_v1",
  governed: "icm_v1",
  icm_lite: "icm_lite",
  icm_v1: "icm_v1",
  icm_v2: "icm_v2",
  icm_v3: "icm_v3",
  icm_staged: "icm_staged",
};

const FALLBACK_CONTRACTS: Record<
  string,
  {
    hypothesis: string;
    changes_from_prev: string[];
    parent_version: string | null;
    execution_strategy: string | null;
  }
> = {
  baseline: {
    hypothesis:
      "Unconstrained comparison arm without stage contracts, AST pre-mapping, or tool batching rules.",
    changes_from_prev: [],
    parent_version: null,
    execution_strategy: "unconstrained",
  },
  icm_v1: {
    hypothesis:
      "Explicit 5-stage contract enforces intake, planning, diff-only edits, sanitized verification, and retrospective discipline.",
    changes_from_prev: [],
    parent_version: "baseline",
    execution_strategy: "single_session",
  },
  icm_lite: {
    hypothesis:
      "Single-file small-scope tasks suffer net negative ROI from 5-stage ceremony; collapsing to one stage eliminates planning overhead while preserving diff-only discipline.",
    changes_from_prev: [
      "Collapse 5 stage files into a single execution stage",
      "Omit AST map injection for low-LOC single-file targets",
    ],
    parent_version: "icm_v1",
    execution_strategy: "single_session",
  },
  icm_v2: {
    hypothesis:
      "Removing stage-file ceremony and pre-injecting a bounded AST symbol map reduces turn count and redundant file reads while preserving correctness via Repro -> Surgical Diff -> Verify and Loop-Breaker.",
    changes_from_prev: [
      "Prohibit stage files (01_intake.md..04_verify.md) and 05_retro essays",
      "Pre-inject compact AST symbol map (max 600 tokens)",
      "Add 2-failure Loop-Breaker directive and concise test flags",
    ],
    parent_version: "icm_v1",
    execution_strategy: "single_session",
  },
  icm_v3: {
    hypothesis:
      "Enforcing a parallel batch-first 3-turn cadence with a byte-stable static workspace prefix, immediate full-write fallback, and strict containment maximizes prompt prefix caching.",
    changes_from_prev: [
      "Forbid all stage files and tasks/ writes",
      "Enforce parallel batch-first 3-turn cadence",
      "Inject byte-deterministic static context prefix (1200-token AST map + test runner)",
      "Add immediate full-file write fallback on search/replace mismatch",
    ],
    parent_version: "icm_v2",
    execution_strategy: "single_session",
  },
  icm_staged: {
    hypothesis:
      "Splitting multi-file exploration/planning and execution across two fresh-context sessions sheds Phase 1 exploration bloat before Phase 2 edits.",
    changes_from_prev: [
      "Split execution into Phase 1 read-only Explore & Plan and Phase 2 fresh-context Batch Exec & Verify",
      "Pass compact structured plan across context reset boundary",
      "Record phase1_peak_context and tokens_shed telemetry",
    ],
    parent_version: "icm_v3",
    execution_strategy: "two_phase_staged",
  },
};

function resolveRunVersion(run: RunRecord): string {
  const cv = typeof run.contract_version === "string" ? run.contract_version.trim() : "";
  if (cv) return cv;
  const arm = String(run.arm || "").trim().toLowerCase();
  return ARM_TO_VERSION[arm] || arm || "unknown";
}

function versionLabel(version: string, arm: string): string {
  if (version === "baseline") return "Baseline";
  if (version === "icm_v1") return "ICM v1";
  const fromVersion = formatArm(version);
  if (fromVersion !== version) return fromVersion;
  return formatArm(arm);
}

function isPricedLineageRun(run: RunRecord): boolean {
  if (!finite(run.cost_usd)) return false;
  const status = String(run.cost_status || "").toLowerCase();
  return status !== "unavailable" && status !== "incomplete" && status !== "unknown";
}

function meanOf(values: (number | null | undefined)[]): number | null {
  const valid = values.filter(finite);
  if (!valid.length) return null;
  return valid.reduce((sum, v) => sum + v, 0) / valid.length;
}

function computeGroupCacheHitRatio(runs: RunRecord[]): number | null {
  let cacheRead = 0;
  let promptTotal = 0;
  let valid = 0;
  for (const r of runs) {
    if (!finite(r.input_tokens) || !finite(r.cache_read_tokens)) continue;
    cacheRead += r.cache_read_tokens;
    promptTotal += r.input_tokens + r.cache_read_tokens;
    valid += 1;
  }
  if (!valid || promptTotal <= 0) return null;
  return cacheRead / promptTotal;
}

function perTaskComparisonMeans(runs: RunRecord[]): Map<string, number> {
  const byTask = new Map<string, number[]>();
  for (const r of runs) {
    if (r.is_comparison_eligible === false || !isPricedLineageRun(r) || !r.task_id) continue;
    const list = byTask.get(r.task_id) || [];
    list.push(r.cost_usd as number);
    byTask.set(r.task_id, list);
  }
  const result = new Map<string, number>();
  for (const [tid, vals] of byTask.entries()) {
    if (vals.length) {
      result.set(tid, vals.reduce((s, v) => s + v, 0) / vals.length);
    }
  }
  return result;
}

function matchedCostDeltaPct(groupRuns: RunRecord[], baseRuns: RunRecord[]): number | null {
  const gMeans = perTaskComparisonMeans(groupRuns);
  const bMeans = perTaskComparisonMeans(baseRuns);
  const common = Array.from(gMeans.keys()).filter((tid) => bMeans.has(tid));
  if (!common.length) return null;
  const gMean = common.reduce((s, tid) => s + (gMeans.get(tid) as number), 0) / common.length;
  const bMean = common.reduce((s, tid) => s + (bMeans.get(tid) as number), 0) / common.length;
  if (bMean <= 0) return null;
  return Number((((gMean - bMean) / bMean) * 100).toFixed(2));
}

function buildRunDerivedSupplement(runs: RunRecord[]) {
  const liveRuns = runs.filter(
    (r) =>
      r.source_kind === "live" &&
      !r.is_simulation &&
      (!r.evidence_status || r.evidence_status === "verified") &&
      Boolean(r.model),
  );
  const byModel = new Map<string, Map<string, RunRecord[]>>();
  for (const r of liveRuns) {
    const model = String(r.model).trim();
    const version = resolveRunVersion(r);
    let versionMap = byModel.get(model);
    if (!versionMap) {
      versionMap = new Map<string, RunRecord[]>();
      byModel.set(model, versionMap);
    }
    const list = versionMap.get(version) || [];
    list.push(r);
    versionMap.set(version, list);
  }
  return byModel;
}

function deriveSupplementMetrics(gRuns: RunRecord[]) {
  const meanTools = meanOf(gRuns.map((r) => r.tool_calls_count));
  const meanInput = meanOf(gRuns.map((r) => (finite(r.input_tokens) ? r.input_tokens : null)));
  const meanCacheRead = meanOf(
    gRuns.map((r) => (finite(r.cache_read_tokens) ? r.cache_read_tokens : null)),
  );
  const meanOutput = meanOf(gRuns.map((r) => (finite(r.output_tokens) ? r.output_tokens : null)));
  const meanLlmCalls = meanOf(gRuns.map((r) => r.llm_calls_count));
  const meanToolsPerCall = meanOf(gRuns.map((r) => r.tools_per_llm_call));
  const bustVals = gRuns.map((r) => r.cache_bust_count).filter(finite);
  const totalCacheBusts = bustVals.length ? bustVals.reduce((s, v) => s + v, 0) : null;
  const taskIds = new Set(gRuns.map((r) => r.task_id).filter(Boolean));
  return {
    meanTools,
    meanInput,
    meanCacheRead,
    meanOutput,
    meanLlmCalls,
    meanToolsPerCall,
    totalCacheBusts,
    meanCacheHitRatio: computeGroupCacheHitRatio(gRuns),
    taskIds,
  };
}

function comparePoints(a: LineagePoint, b: LineagePoint): number {
  const oa = VERSION_ORDER[a.version] ?? 99;
  const ob = VERSION_ORDER[b.version] ?? 99;
  return oa - ob || a.version.localeCompare(b.version);
}

/**
 * Resolve per-(model, version) iteration lineage cohorts.
 * Uses `data.iteration_lineage.versions` when populated and enriches with
 * run-level token/tool averages, or falls back to deriving directly from
 * verified live runs in `data.runs`.
 */
export function resolveLineageModels(data: DashboardPayload): LineageModelCohort[] {
  const runs = data?.runs || [];
  const runsByModelVersion = buildRunDerivedSupplement(runs);
  const contractMetaById = new Map<string, IterationContractMeta>();
  for (const c of data?.iteration_lineage?.contracts || []) {
    if (c?.id) contractMetaById.set(c.id, c);
  }

  const cohorts = new Map<
    string,
    { points: LineagePoint[]; taskIds: Set<string>; totalRuns: number }
  >();

  const hasExportedLineage = Boolean(
    data?.iteration_lineage?.has_data && data.iteration_lineage.versions?.length,
  );

  if (hasExportedLineage) {
    for (const entry of data.iteration_lineage!.versions as IterationLineageEntry[]) {
      const model = String(entry.model || "").trim();
      if (!model) continue;
      const version = entry.version;
      const gRuns = runsByModelVersion.get(model)?.get(version) || [];
      const sup = deriveSupplementMetrics(gRuns);
      const contractMeta = contractMetaById.get(version);
      const fallback = FALLBACK_CONTRACTS[version];

      const point: LineagePoint = {
        version,
        arm: entry.arm || version,
        label: versionLabel(version, entry.arm || version),
        n_runs: entry.n_runs,
        passed_count: entry.passed_count,
        pass_rate: entry.pass_rate ?? null,
        priced_n_runs: entry.priced_n_runs ?? 0,
        mean_cost_usd: finite(entry.mean_cost_usd) ? entry.mean_cost_usd : null,
        cost_per_passing_patch_usd: finite(entry.cost_per_passing_patch_usd)
          ? entry.cost_per_passing_patch_usd
          : null,
        mean_tools: sup.meanTools,
        mean_input_tokens: sup.meanInput,
        mean_cache_read_tokens: sup.meanCacheRead,
        mean_output_tokens: sup.meanOutput,
        mean_llm_calls: finite(entry.mean_llm_calls) ? entry.mean_llm_calls : sup.meanLlmCalls,
        mean_cache_hit_ratio: finite(entry.mean_cache_hit_ratio)
          ? entry.mean_cache_hit_ratio
          : sup.meanCacheHitRatio,
        mean_tools_per_call: finite(entry.mean_tools_per_call)
          ? entry.mean_tools_per_call
          : sup.meanToolsPerCall,
        total_cache_busts: finite(entry.total_cache_busts)
          ? entry.total_cache_busts
          : sup.totalCacheBusts,
        cost_delta_vs_baseline_pct: finite(entry.cost_delta_vs_baseline_pct)
          ? entry.cost_delta_vs_baseline_pct
          : null,
        hypothesis: entry.hypothesis ?? contractMeta?.hypothesis ?? fallback?.hypothesis ?? null,
        changes_from_prev:
          entry.changes_from_prev && entry.changes_from_prev.length > 0
            ? entry.changes_from_prev
            : contractMeta?.changes_from_prev?.length
              ? contractMeta.changes_from_prev
              : fallback?.changes_from_prev || [],
        parent_version:
          entry.parent_version !== undefined
            ? entry.parent_version
            : contractMeta?.parent_version ?? fallback?.parent_version ?? null,
        execution_strategy:
          entry.execution_strategy ??
          contractMeta?.execution_strategy ??
          fallback?.execution_strategy ??
          null,
      };

      const bucket = cohorts.get(model) || {
        points: [],
        taskIds: new Set<string>(),
        totalRuns: 0,
      };
      bucket.points.push(point);
      bucket.totalRuns += point.n_runs;
      for (const tid of entry.task_ids || []) bucket.taskIds.add(tid);
      for (const tid of sup.taskIds) bucket.taskIds.add(tid);
      cohorts.set(model, bucket);
    }
  } else {
    for (const [model, versionMap] of runsByModelVersion.entries()) {
      const baseRuns = versionMap.get("baseline") || [];
      const bucket = {
        points: [] as LineagePoint[],
        taskIds: new Set<string>(),
        totalRuns: 0,
      };
      for (const [version, gRuns] of versionMap.entries()) {
        const sup = deriveSupplementMetrics(gRuns);
        const nRuns = gRuns.length;
        const passedCount = gRuns.filter(
          (r) => String(r.verification_status || "").toLowerCase() === "passed",
        ).length;
        const passRate = nRuns > 0 ? passedCount / nRuns : null;
        const pricedRuns = gRuns.filter(isPricedLineageRun);
        const pricedNRuns = pricedRuns.length;
        const meanCostUsd =
          pricedNRuns > 0
            ? pricedRuns.reduce((s, r) => s + (r.cost_usd as number), 0) / pricedNRuns
            : null;
        const pricedPassedCount = pricedRuns.filter(
          (r) => String(r.verification_status || "").toLowerCase() === "passed",
        ).length;
        // REP-06: never fake $0.00 when zero priced passes exist.
        const costPerPassingPatchUsd =
          pricedPassedCount > 0
            ? pricedRuns.reduce((s, r) => s + (r.cost_usd as number), 0) / pricedPassedCount
            : null;

        const arm = String(gRuns[0]?.arm || version).toLowerCase();
        const contractMeta = contractMetaById.get(version);
        const fallback = FALLBACK_CONTRACTS[version];

        bucket.points.push({
          version,
          arm,
          label: versionLabel(version, arm),
          n_runs: nRuns,
          passed_count: passedCount,
          pass_rate: passRate,
          priced_n_runs: pricedNRuns,
          mean_cost_usd: meanCostUsd,
          cost_per_passing_patch_usd: costPerPassingPatchUsd,
          mean_tools: sup.meanTools,
          mean_input_tokens: sup.meanInput,
          mean_cache_read_tokens: sup.meanCacheRead,
          mean_output_tokens: sup.meanOutput,
          mean_llm_calls: sup.meanLlmCalls,
          mean_cache_hit_ratio: sup.meanCacheHitRatio,
          mean_tools_per_call: sup.meanToolsPerCall,
          total_cache_busts: sup.totalCacheBusts,
          cost_delta_vs_baseline_pct:
            version === "baseline" ? null : matchedCostDeltaPct(gRuns, baseRuns),
          hypothesis: contractMeta?.hypothesis ?? fallback?.hypothesis ?? null,
          changes_from_prev:
            contractMeta?.changes_from_prev ?? fallback?.changes_from_prev ?? [],
          parent_version:
            contractMeta?.parent_version !== undefined
              ? contractMeta.parent_version
              : fallback?.parent_version ?? null,
          execution_strategy:
            contractMeta?.execution_strategy ?? fallback?.execution_strategy ?? null,
        });
        bucket.totalRuns += nRuns;
        for (const tid of sup.taskIds) bucket.taskIds.add(tid);
      }
      cohorts.set(model, bucket);
    }
  }

  const result: LineageModelCohort[] = Array.from(cohorts.entries()).map(
    ([model, bucket]) => {
      const points = [...bucket.points].sort(comparePoints);
      const hasPricing = points.some(
        (p) => p.priced_n_runs > 0 && finite(p.mean_cost_usd),
      );
      return {
        model,
        hasPricing,
        totalRuns: bucket.totalRuns,
        taskCount: bucket.taskIds.size,
        points,
      };
    },
  );

  result.sort((a, b) => {
    if (a.hasPricing !== b.hasPricing) return a.hasPricing ? -1 : 1;
    if (a.points.length !== b.points.length) return b.points.length - a.points.length;
    if (a.totalRuns !== b.totalRuns) return b.totalRuns - a.totalRuns;
    return a.model.localeCompare(b.model);
  });

  return result;
}

/**
 * Compute non-dominated Pareto frontier versions minimizing xAccessor(p) and
 * maximizing pass_rate. Points with null/non-finite x or pass_rate are ignored.
 */
export function computeParetoFrontier<
  T extends Pick<LineagePoint, "version" | "pass_rate">,
>(
  points: T[],
  xAccessor: (point: T) => number | null | undefined,
): Set<string> {
  const valid = points
    .map((point) => ({
      point,
      x: xAccessor(point),
      y: point.pass_rate,
    }))
    .filter(
      (item): item is { point: T; x: number; y: number } =>
        finite(item.x) && finite(item.y),
    );

  const frontier = new Set<string>();
  for (const candidate of valid) {
    const dominated = valid.some(
      (other) =>
        other !== candidate &&
        other.x <= candidate.x &&
        other.y >= candidate.y &&
        (other.x < candidate.x || other.y > candidate.y),
    );
    if (!dominated) {
      frontier.add(candidate.point.version);
    }
  }
  return frontier;
}

/**
 * Connect ordered lineage transitions across existing nodes in a model cohort:
 * main spine (baseline -> icm_v1 -> icm_v2 -> icm_v3 -> icm_staged) and
 * lite branch (icm_v1 -> icm_lite, or baseline -> icm_lite if icm_v1 absent).
 */
export function lineageEdges(points: LineagePoint[]): LineageEdge[] {
  const present = new Set(points.map((p) => p.version));
  const spineOrder = ["baseline", "icm_v1", "icm_v2", "icm_v3", "icm_staged"];
  const activeSpine = spineOrder.filter((v) => present.has(v));
  const edges: LineageEdge[] = [];
  const seen = new Set<string>();

  const pushEdge = (from: string, to: string, kind: "spine" | "branch") => {
    const key = `${from}->${to}`;
    if (from === to || seen.has(key)) return;
    seen.add(key);
    edges.push({ from, to, kind });
  };

  for (let i = 0; i < activeSpine.length - 1; i++) {
    pushEdge(activeSpine[i], activeSpine[i + 1], "spine");
  }

  if (present.has("icm_lite")) {
    const branchParent = present.has("icm_v1")
      ? "icm_v1"
      : present.has("baseline")
        ? "baseline"
        : null;
    if (branchParent) pushEdge(branchParent, "icm_lite", "branch");
  }

  for (const p of points) {
    if (
      p.parent_version &&
      present.has(p.parent_version) &&
      p.version !== "icm_lite" &&
      !spineOrder.includes(p.version)
    ) {
      pushEdge(p.parent_version, p.version, "spine");
    }
  }

  return edges;
}
