import { type CSSProperties, useMemo, useState } from "react";
import {
  ArrowRight,
  ArrowUpRight,
  ChevronDown,
  CircleHelp,
  Cpu,
  FlaskConical,
  Layers,
  Orbit,
  ShieldCheck,
  Sparkles,
  TrendingDown,
  Zap,
} from "lucide-react";
import {
  DashboardPayload,
  HeadlineStat,
  RunRecord,
  TaskSummaryItem,
} from "../../types";
import { formatArm, formatCurrency, formatTokens } from "../../lib/formatters";
import {
  acuTelemetrySummary,
  computeIdealZoneMetrics,
  formatSignedCostChange,
  IdealZoneSummary,
  isPricedRun,
} from "../../lib/analytics";
import { armNames, experimentNames, finite, governedArm, governedArmName } from "../../lib/workspace";
import AdaptiveICM from "./AdaptiveICM";
import IterationLineage from "./IterationLineage";

type OverviewTab = "cost" | "models";

const METRIC_HELPERS: Record<string, string> = {
  cost_reduction: "Priced API spend vs. plain baseline",
  tokens_per_pass: "Tokens used per solved task (includes failed retries)",
  defect_rate: "Defect rate observed in operational trials",
  cache_hit_rate: "Prompt cache reuse across governed calls",
};

const ORBIT_STAGES = [
  { x: 116, y: 61, t: "Intake" },
  { x: 286, y: 50, t: "Plan" },
  { x: 342, y: 149, t: "Execute" },
  { x: 233, y: 222, t: "Verify" },
  { x: 77, y: 172, t: "Reflect" },
];

function ContextOrbit() {
  return (
    <div className="context-orbit">
      <svg viewBox="0 0 410 260" role="img" aria-labelledby="orbit-title">
        <title id="orbit-title">
          Context organized through five ICM stages: Intake, Plan, Execute,
          Verify, Reflect
        </title>
        <defs>
          <linearGradient id="orbit-line">
            <stop stopColor="#B9ACEF" />
            <stop offset="1" stopColor="#8E7BD8" />
          </linearGradient>
        </defs>
        <g className="orbit-ring-outer">
          <ellipse
            cx="205"
            cy="130"
            rx="132"
            ry="83"
            fill="none"
            stroke="url(#orbit-line)"
            strokeWidth="1.15"
            transform="rotate(-18 205 130)"
          />
        </g>
        <g className="orbit-ring-inner">
          <ellipse
            cx="205"
            cy="130"
            rx="100"
            ry="106"
            fill="none"
            stroke="#CDC3EE"
            strokeWidth="1"
            strokeDasharray="4 6"
            transform="rotate(44 205 130)"
          />
        </g>
        <circle
          className="orbit-core-halo"
          cx="205"
          cy="130"
          r="57"
          fill="#E2DAF8"
        />
        <g className="orbit-core-emblem">
          <circle cx="205" cy="130" r="42" fill="#6955D8" />
          <g fill="none" stroke="#FFF" strokeWidth="1.7">
            <ellipse
              cx="205"
              cy="130"
              rx="22"
              ry="9"
              transform="rotate(-35 205 130)"
            />
            <ellipse
              cx="205"
              cy="130"
              rx="22"
              ry="9"
              transform="rotate(55 205 130)"
            />
          </g>
          <circle cx="205" cy="130" r="3" fill="white" />
        </g>
        <g className="orbit-satellites">
          <circle cx="185" cy="30" r="4" fill="#A495D5" />
          <circle cx="308" cy="202" r="3" fill="#A495D5" />
          <circle cx="67" cy="108" r="3" fill="#A495D5" />
        </g>
        {ORBIT_STAGES.map(({ x, y, t }, idx) => (
          <g
            key={t}
            className="orbit-pill"
            style={{ "--pill-i": idx } as CSSProperties}
          >
            <rect
              x={x - 34}
              y={y - 14}
              width="68"
              height="28"
              rx="14"
              fill="#FBFAFF"
              stroke="#D9D0EF"
            />
            <text
              x={x}
              y={y + 4}
              textAnchor="middle"
              fill="#655680"
              fontSize="11"
              fontFamily="Manrope, sans-serif"
            >
              {t}
            </text>
          </g>
        ))}
      </svg>
      <span>LESS NOISE. MORE SIGNAL.</span>
    </div>
  );
}

function fmtSignedPct(val: number | null, suffix = "%"): string {
  if (val == null || !Number.isFinite(val)) return "—";
  return `${val >= 0 ? `+${val.toFixed(1)}` : `−${Math.abs(val).toFixed(1)}`}${suffix}`;
}

function fmtSavingsHero(val: number | null): string {
  if (val == null || !Number.isFinite(val)) return "—";
  if (val > 0) return `−${val.toFixed(1)}%`;
  if (val < 0) return `+${Math.abs(val).toFixed(1)}%`;
  return "0.0%";
}

function fmtPct(val: number | null, digits = 1): string {
  return val != null && Number.isFinite(val) ? `${val.toFixed(digits)}%` : "—";
}

function fmtNum(val: number | null, digits = 1): string {
  return val != null && Number.isFinite(val) ? val.toFixed(digits) : "—";
}

function fmtSec(val: number | null): string {
  return val != null && Number.isFinite(val) ? `${val.toFixed(1)}s` : "—";
}

function Metric({ stat }: { stat: HeadlineStat }) {
  const isCost = stat.id === "cost_reduction";
  const isToken = stat.id === "tokens_per_pass";
  const isQuality = stat.id === "defect_rate";
  const Icon = isCost || isToken ? TrendingDown : isQuality ? ShieldCheck : Cpu;
  const label = isCost
    ? "Cost change vs baseline"
    : isToken
      ? "Tokens / solved task"
      : isQuality
        ? "Governed defect rate"
        : "Governed cache hit rate";
  const displayValue = isCost
    ? stat.signed_cost_label ||
      (finite(stat.value) ? formatSignedCostChange(stat.value) : String(stat.value))
    : finite(stat.value)
      ? `${stat.value.toFixed(1)}%`
      : stat.value;
  return (
    <article className="metric-card">
      <div className="metric-top">
        <span>{label}</span>
        <Icon size={19} />
      </div>
      <div
        className={`metric-value ${(isCost || isToken) && finite(stat.value) && stat.value < 0 ? "text-rust" : ""}`}
      >
        {displayValue}
        <span className="metric-tag">
          {isQuality ? "Quality" : isToken ? "All models" : "Recorded"}
        </span>
      </div>
      {METRIC_HELPERS[stat.id] && (
        <p className="metric-helper">{METRIC_HELPERS[stat.id]}</p>
      )}
      <div className="metric-comparison">
        <span>
          Baseline <strong>{stat.baseline}</strong>
        </span>
        <span>
          Governed <strong>{stat.icm}</strong>
        </span>
      </div>
      <div className="metric-foot">
        {stat.source} · {stat.n_tasks} {isToken ? "series" : "tasks"}
        {stat.ci95 && (
          <span className="confidence">
            95% CI: {stat.ci95[0]}% to {stat.ci95[1]}%
          </span>
        )}
      </div>
    </article>
  );
}

export function Overview({ data }: { data: DashboardPayload }) {
  const [activeTab, setActiveTab] = useState<OverviewTab>("cost");
  const [showAllPriced, setShowAllPriced] = useState(false);
  const measured =
    !data.is_demo_report &&
    !data.is_simulation &&
    Boolean(data.cumulative?.has_measured_data);
  const tasks = data.tasks || [];
  const taskModel = (task: TaskSummaryItem) =>
    task.model || task.arms.baseline?.model || governedArm(task)?.model || "";
  const taskKey = (task: TaskSummaryItem) =>
    task.series_id || `${task.task_id}::${taskModel(task)}`;
  const multiModelTasks = new Set(
    tasks
      .filter((t) => tasks.filter((o) => o.task_id === t.task_id).length > 1)
      .map((t) => t.task_id),
  );
  const pricedTasks = tasks.filter(
    (task) =>
      finite(task.arms.baseline?.mean_cost_usd) ||
      finite(governedArm(task)?.mean_cost_usd),
  );
  const idealZones = useMemo(
    () => computeIdealZoneMetrics(data.runs || []),
    [data.runs],
  );
  const modelSummaries = useMemo(() => {
    const byModel = new Map<string, RunRecord[]>();
    for (const run of data.runs || []) {
      if (run.source_kind === "imported" || !run.model) continue;
      const list = byModel.get(run.model) || [];
      list.push(run);
      byModel.set(run.model, list);
    }
    const runTokens = (r: RunRecord) =>
      finite(r.total_tokens)
        ? r.total_tokens
        : (finite(r.input_tokens) ? r.input_tokens : 0) +
          (finite(r.output_tokens) ? r.output_tokens : 0);
    const hasTokens = (r: RunRecord) =>
      finite(r.total_tokens) ||
      finite(r.input_tokens) ||
      finite(r.output_tokens);
    // Runs without token telemetry are left out, so a cohort with none shows "—", not 0.
    const tokensPerPass = (runs: RunRecord[]) => {
      const metered = runs.filter(hasTokens);
      const passed = metered.filter(
        (r) => r.verification_status === "passed",
      ).length;
      return passed > 0
        ? metered.reduce((s, r) => s + runTokens(r), 0) / passed
        : null;
    };
    const sumUsd = (runs: RunRecord[]) => {
      const priced = runs.filter(
        (r) => r.is_comparison_eligible && finite(r.cost_usd),
      );
      return priced.length > 0
        ? priced.reduce((s, r) => s + (r.cost_usd as number), 0)
        : null;
    };
    return Array.from(byModel.keys())
      .sort()
      .map((model) => {
        const runs = byModel.get(model)!;
        const baseRuns = runs.filter((r) => r.arm === "baseline");
        const govRuns = runs.filter((r) => r.arm !== "baseline");
        const basePassed = baseRuns.filter(
          (r) => r.verification_status === "passed",
        ).length;
        const govPassed = govRuns.filter(
          (r) => r.verification_status === "passed",
        ).length;
        const baseTokPass = tokensPerPass(baseRuns);
        const govTokPass = tokensPerPass(govRuns);
        const tokDeltaPct =
          baseTokPass != null && baseTokPass > 0 && govTokPass != null
            ? ((baseTokPass - govTokPass) / baseTokPass) * 100
            : null;
        const baseTools = baseRuns.reduce(
          (s, r) => s + (finite(r.tool_calls_count) ? r.tool_calls_count : 0),
          0,
        );
        const baseErrors = baseRuns.reduce(
          (s, r) => s + (finite(r.tool_errors_count) ? r.tool_errors_count : 0),
          0,
        );
        const govTools = govRuns.reduce(
          (s, r) => s + (finite(r.tool_calls_count) ? r.tool_calls_count : 0),
          0,
        );
        const govErrors = govRuns.reduce(
          (s, r) => s + (finite(r.tool_errors_count) ? r.tool_errors_count : 0),
          0,
        );
        const acu = acuTelemetrySummary(runs);
        return {
          model,
          liveRuns: runs.length,
          baseTotal: baseRuns.length,
          basePassed,
          govTotal: govRuns.length,
          govPassed,
          baseTokPass,
          govTokPass,
          tokDeltaPct,
          baseTools,
          baseErrors,
          govTools,
          govErrors,
          baseUsd: sumUsd(baseRuns),
          govUsd: sumUsd(govRuns),
          acuRuns: acu.runsWithAcus,
          totalAcus: acu.totalAcus,
        };
      });
  }, [data.runs]);
  const maxCost = Math.max(
    0.001,
    ...pricedTasks
      .flatMap((task) =>
        armNames(task).map((n) => task.arms[n]?.mean_cost_usd),
      )
      .filter(finite),
  );
  const legendArms = Array.from(
    new Set(
      pricedTasks.flatMap((task) =>
        armNames(task).filter((n) => n !== "baseline"),
      ),
    ),
  );
  const stats = measured ? data.headline?.stats || [] : [];
  const totalRunsCount = data.runs?.length ?? data.cumulative?.total_runs ?? 0;
  const pricedRunsCount = (data.runs || []).filter(isPricedRun).length;
  const uniqueTasksCount = new Set(tasks.map((t) => t.task_id)).size;
  const unmeasuredSuites = (data.declared_benchmarks || []).filter(
    (b) => b.measured_runs === 0 || b.status === "suite present, unmeasured",
  );
  const archivedRunsCount = (data.runs || []).filter(
    (run) => run.source_kind === "imported",
  ).length;
  const liveRunsCount = totalRunsCount - archivedRunsCount;
  const headlineScope = data.headline?.scope;
  const shownPricedTasks = showAllPriced ? pricedTasks : pricedTasks.slice(0, 5);
  const lite: IdealZoneSummary = idealZones.icm_lite;
  const v3: IdealZoneSummary = idealZones.icm_v3;
  const staged: IdealZoneSummary = idealZones.icm_staged;
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">THE BIG PICTURE</div>
          <h1>Your lab, at a glance.</h1>
          <p>
            Does structured context make coding agents cheaper and more reliable
            against plain baselines?
          </p>
        </div>
        <span className={`badge ${measured ? "badge-green" : "badge-amber"}`}>
          {measured ? <ShieldCheck size={13} /> : <CircleHelp size={13} />}
          {measured
            ? "Measured results"
            : data.is_demo_report
              ? "Demo snapshot"
              : data.is_simulation
                ? "Simulation snapshot"
                : "Measurements unavailable"}
        </span>
      </div>

      {/* Beat 1: Airy Hero Stage with Animated Context Orbit SVG */}
      <section className="thesis-panel hero-stage">
        <div className="thesis-copy hero-copy">
          <div className="eyebrow">
            <Orbit size={14} /> INTERPRETABLE CONTEXT METHODOLOGY
          </div>
          <h2>
            Better context.
            <br />
            <span>Measurable impact.</span>
          </h2>
          <p>
            AI-Lab tests plain baseline prompts head-to-head against structured{" "}
            <strong>ICM workflows</strong> on identical multi-file tasks—graded
            automatically by hidden test suites.
          </p>
          <div className="hero-actions">
            <a href="#tasks" className="button button-primary">
              Browse {uniqueTasksCount} tasks <ArrowRight size={17} />
            </a>
            <a href="#analytics" className="button button-outline">
              Deep analytics <ArrowUpRight size={16} />
            </a>
          </div>
        </div>
        <div className="hero-orbit-stage">
          <ContextOrbit />
        </div>
      </section>

      {/* Beat 2: Ideal Workflow Zones — strictly each ICM tier vs. matched Baseline */}
      <section className="ideal-zones" aria-labelledby="ideal-zones-title">
        <div className="section-heading results-heading">
          <div>
            <div className="eyebrow">IDEAL WORKFLOW ZONES</div>
            <h2 id="ideal-zones-title">
              Each ICM tier vs. its matched baseline
            </h2>
            <p className="section-subcopy">
              Every card benchmarks one ICM workflow strictly against matched
              Baseline runs on the same task and model—never against other ICM
              versions.
            </p>
          </div>
          <span>
            {totalRunsCount} runs · {uniqueTasksCount} tasks
          </span>
        </div>

        <div className="ideal-zones-grid">
          <article className="zone-card">
            <div className="zone-card-head">
              <div>
                <h3>ICM-Lite</h3>
                <p>Micro-tasks &amp; focused edits</p>
              </div>
              <span className="badge badge-purple">
                <Zap size={12} /> Fast loop
              </span>
            </div>
            <div className="zone-kpi">
              <strong
                className={
                  lite.toolSavingsPct != null && lite.toolSavingsPct >= 0
                    ? "text-sea"
                    : "text-rust"
                }
              >
                {fmtSavingsHero(lite.toolSavingsPct)}
              </strong>
              <span>tool calls vs. baseline</span>
            </div>
            <p className="zone-kpi-sub">
              {fmtNum(lite.govMeanTools)} vs {fmtNum(lite.baseMeanTools)} avg
              tool calls
            </p>
            <dl className="zone-ledger">
              <div>
                <dt>Verified pass rate</dt>
                <dd>
                  {fmtPct(lite.govPassRate, 0)} ({lite.govPassed}/{lite.govRuns}
                  ) vs {fmtPct(lite.basePassRate, 0)} ({lite.basePassed}/
                  {lite.baseRuns})
                </dd>
              </div>
              <div>
                <dt>Mean runtime</dt>
                <dd>
                  {fmtSec(lite.govMeanDuration)} vs{" "}
                  {fmtSec(lite.baseMeanDuration)} (
                  {fmtSavingsHero(lite.durationSavingsPct)})
                </dd>
              </div>
            </dl>
            <div className="zone-card-foot">
              {lite.matchedSeries} matched series vs. Baseline · Skips heavy
              planning when edits stay local.
            </div>
          </article>

          <article className="zone-card zone-card-featured">
            <div className="zone-card-head">
              <div>
                <h3>ICM v3</h3>
                <p>Multi-file engineering</p>
              </div>
              <span className="badge badge-green">
                <Sparkles size={12} /> Cost sweet spot
              </span>
            </div>
            <div className="zone-kpi">
              <strong
                className={
                  v3.costPerPassSavingsPct != null &&
                  v3.costPerPassSavingsPct >= 0
                    ? "text-sea"
                    : "text-rust"
                }
              >
                {fmtSavingsHero(v3.costPerPassSavingsPct)}
              </strong>
              <span>cost / verified pass vs. baseline</span>
            </div>
            <p className="zone-kpi-sub">
              {formatCurrency(v3.govCostPerPass)} vs{" "}
              {formatCurrency(v3.baseCostPerPass)} per solved task
            </p>
            <dl className="zone-ledger">
              <div>
                <dt>Mean run spend</dt>
                <dd>
                  {formatCurrency(v3.govMeanCost)} vs{" "}
                  {formatCurrency(v3.baseMeanCost)} (
                  {fmtSavingsHero(v3.runCostSavingsPct)})
                </dd>
              </div>
              <div>
                <dt>Runtime &amp; tools</dt>
                <dd>
                  {fmtSec(v3.govMeanDuration)} vs {fmtSec(v3.baseMeanDuration)}{" "}
                  · {fmtSavingsHero(v3.toolSavingsPct)} tools
                </dd>
              </div>
            </dl>
            <div className="zone-card-foot">
              {v3.pricedSeries} priced series ({v3.matchedSeries} matched vs.
              Baseline) · Batched reads cut token waste.
            </div>
          </article>

          <article className="zone-card">
            <div className="zone-card-head">
              <div>
                <h3>ICM Staged</h3>
                <p>Complex multi-step suites</p>
              </div>
              <span className="badge badge-purple">
                <Layers size={12} /> Reliability guard
              </span>
            </div>
            <div className="zone-kpi">
              <strong
                className={
                  staged.passDeltaPp != null && staged.passDeltaPp >= 0
                    ? "text-sea"
                    : "text-rust"
                }
              >
                {fmtSignedPct(staged.passDeltaPp, " pp")}
              </strong>
              <span>pass rate vs. baseline</span>
            </div>
            <p className="zone-kpi-sub">
              {fmtPct(staged.govPassRate)} ({staged.govPassed}/{staged.govRuns})
              vs {fmtPct(staged.basePassRate)} ({staged.basePassed}/
              {staged.baseRuns})
            </p>
            <dl className="zone-ledger">
              <div>
                <dt>Cost / verified pass</dt>
                <dd>
                  {formatCurrency(staged.govCostPerPass)} vs{" "}
                  {formatCurrency(staged.baseCostPerPass)} (
                  {fmtSavingsHero(staged.costPerPassSavingsPct)})
                </dd>
              </div>
              <div>
                <dt>Mean run spend</dt>
                <dd>
                  {formatCurrency(staged.govMeanCost)} vs{" "}
                  {formatCurrency(staged.baseMeanCost)}
                </dd>
              </div>
            </dl>
            <div className="zone-card-foot">
              {staged.matchedSeries} matched series vs. Baseline · Progressive
              gates catch errors early.
            </div>
          </article>
        </div>

        <details className="scope-disclosure">
          <summary>
            <span>
              Pooled headline stats, dataset scope &amp; 3-tier routing details (
              {totalRunsCount} runs · {uniqueTasksCount} tasks)
            </span>
            <ChevronDown size={15} />
          </summary>
          <div className="scope-disclosure-body">
            {stats.length ? (
              <section
                className="metrics-grid"
                aria-label="Recorded benchmark metrics"
              >
                {stats.map((stat) => (
                  <Metric key={stat.id} stat={stat} />
                ))}
              </section>
            ) : (
              <div className="panel empty-state">
                <FlaskConical size={30} />
                <h2>Measurements start with evidence.</h2>
                <p>
                  {measured
                    ? "No headline statistics in this snapshot. Inspect individual experiments below."
                    : "This snapshot has no measured headline results. Explore the available records or refresh after adding verified runs."}
                </p>
                <a href="#audit" className="text-link">
                  Inspect evidence <ArrowRight size={16} />
                </a>
              </div>
            )}
            <p className="scope-disclosure-note">
              {headlineScope
                ? `${headlineScope.unique_task_count} tasks · ${headlineScope.total_run_count} runs · ${headlineScope.priced_run_count} priced runs · ${headlineScope.pooling_note || headlineScope.pooling_method}`
                : `${uniqueTasksCount} tasks · ${totalRunsCount} runs · ${pricedRunsCount} priced runs · pooled_sum (macro_average noted per task)`}
              {archivedRunsCount > 0
                ? ` (${liveRunsCount} live · ${archivedRunsCount} archived)`
                : ""}
              {unmeasuredSuites.length > 0
                ? ` · ${unmeasuredSuites.length} suite present, unmeasured`
                : ""}
            </p>
            <AdaptiveICM data={data} />
          </div>
        </details>
      </section>

      {/* Beat 3: Signature Interactive Pareto / Evolution Graph */}
      <IterationLineage data={data} />

      {/* Beat 4: Light Preview Panel (Cost by Task & Model Summary) */}
      <section className="panel overview-hub" aria-labelledby="hub-title">
        <div className="panel-heading overview-hub-head">
          <div>
            <span className="eyebrow">EXPLORE THE DATA</span>
            <h2 id="hub-title">Cost per task &amp; model summary</h2>
          </div>
          <div
            className="segmented-control"
            role="tablist"
            aria-label="Overview chart sections"
          >
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === "cost"}
              aria-pressed={activeTab === "cost"}
              onClick={() => setActiveTab("cost")}
            >
              Cost by task ({pricedTasks.length})
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === "models"}
              aria-pressed={activeTab === "models"}
              onClick={() => setActiveTab("models")}
            >
              By model ({modelSummaries.length})
            </button>
          </div>
        </div>

        {activeTab === "cost" && (
          <div className="hub-tab-body">
            <section
              className="comparison-panel hub-panel-inner"
              aria-labelledby="comparison-title"
            >
              <div className="panel-heading">
                <div>
                  <h3 id="comparison-title">Cost per run by task</h3>
                  <p>
                    Average USD per run — shorter bars mean lower spend.
                  </p>
                </div>
                <div className="chart-legend">
                  <span>
                    <i className="legend-baseline" />
                    Baseline
                  </span>
                  {legendArms.map((n) => (
                    <span key={n}>
                      <i className="legend-governed" />
                      {formatArm(n)}
                    </span>
                  ))}
                </div>
              </div>
              <div
                className="cost-chart"
                role="group"
                aria-label="Cost comparison in US dollars. Values for baseline and governed runs are labeled on each row."
              >
                {shownPricedTasks.map((task) => {
                  const baseline = task.arms.baseline?.mean_cost_usd;
                  const mdl = taskModel(task);
                  return (
                    <div className="chart-row" key={taskKey(task)}>
                      <a href="#tasks" className="chart-label">
                        {task.task_id}
                        <span>
                          {experimentNames[task.task_id] || "Experiment"}
                          {multiModelTasks.has(task.task_id) && mdl
                            ? ` · ${mdl}`
                            : ""}
                        </span>
                        <span className="badge badge-purple chart-arm-badge">{formatArm(governedArmName(task))}</span>
                      </a>
                      <div className="chart-bars">
                        <div className="bar-line">
                          <span
                            className="bar bar-baseline"
                            style={{
                              width: finite(baseline)
                                ? `${Math.max(1, (baseline / maxCost) * 100)}%`
                                : "0%",
                            }}
                          />
                          <span className="bar-value">
                            <span className="sr-only">Baseline </span>
                            {formatCurrency(baseline)}
                          </span>
                        </div>
                        {armNames(task)
                          .filter((n) => n !== "baseline")
                          .map((name) => {
                            const cost = task.arms[name]?.mean_cost_usd;
                            return (
                              <div className="bar-line" key={name}>
                                <span
                                  className="bar bar-governed"
                                  style={{
                                    width: finite(cost)
                                      ? `${Math.max(1, (cost / maxCost) * 100)}%`
                                      : "0%",
                                  }}
                                />
                                <span className="bar-value">
                                  <span className="sr-only">{formatArm(name)} </span>
                                  {formatCurrency(cost)}
                                </span>
                              </div>
                            );
                          })}
                      </div>
                    </div>
                  );
                })}
                {!pricedTasks.length && (
                  <p className="empty-inline">
                    No priced experiment comparisons available.
                  </p>
                )}
              </div>
              {pricedTasks.length > 5 && (
                <div className="hub-show-more">
                  <button
                    type="button"
                    className="button button-outline"
                    onClick={() => setShowAllPriced((cur) => !cur)}
                  >
                    {showAllPriced
                      ? "Show fewer tasks"
                      : `Show all ${pricedTasks.length} priced tasks`}
                  </button>
                </div>
              )}
              <div className="panel-bottom">
                <span>
                  USD per run ·{" "}
                  {measured
                    ? "Recorded usage estimates"
                    : "Demo / non-measured data"}
                </span>
                <a className="text-link" href="#tasks">
                  View all tasks <ArrowUpRight size={15} />
                </a>
              </div>
            </section>
          </div>
        )}

        {activeTab === "models" && (
          <div className="hub-tab-body" aria-labelledby="cross-model-title">
            <div className="panel-heading">
              <div>
                <h3 id="cross-model-title">
                  Performance &amp; token efficiency by model
                </h3>
                <p>
                  Every live model tested so far. Priced models report estimated
                  USD spend; unpriced models track pass rate, tokens, or tool
                  calls.
                </p>
              </div>
              <span className="badge badge-purple">
                {modelSummaries.length} models · {liveRunsCount} live runs
              </span>
            </div>
            {modelSummaries.length > 0 ? (
              <div
                className="table-scroll"
                role="region"
                aria-label="Cross-model performance summary"
                tabIndex={0}
              >
                <table className="data-table">
                  <thead>
                    <tr>
                      <th scope="col">Model</th>
                      <th scope="col">Live runs</th>
                      <th scope="col">Pass (Base / Gov)</th>
                      <th scope="col">Tokens / pass (Base → Gov)</th>
                      <th scope="col">Δ Tokens</th>
                      <th scope="col">Tool calls (err)</th>
                      <th scope="col">ACU (metadata)</th>
                      <th scope="col">Priced USD (Base → Gov)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {modelSummaries.map((m) => (
                      <tr key={m.model}>
                        <th scope="row">{m.model}</th>
                        <td>{m.liveRuns}</td>
                        <td>
                          {m.basePassed}/{m.baseTotal} / {m.govPassed}/{m.govTotal}
                        </td>
                        <td>
                          {m.baseTokPass != null ? formatTokens(m.baseTokPass) : "—"}{" "}
                          → {m.govTokPass != null ? formatTokens(m.govTokPass) : "—"}
                        </td>
                        <td>
                          {m.tokDeltaPct != null ? (
                            <span
                              className={
                                m.tokDeltaPct >= 0 ? "text-sea" : "text-rust"
                              }
                            >
                              {m.tokDeltaPct >= 0
                                ? `−${m.tokDeltaPct.toFixed(1)}%`
                                : `+${Math.abs(m.tokDeltaPct).toFixed(1)}%`}
                            </span>
                          ) : (
                            "—"
                          )}
                        </td>
                        <td>
                          {m.baseTools} ({m.baseErrors}) / {m.govTools} ({m.govErrors})
                        </td>
                        <td>
                          {m.acuRuns > 0 ? `${m.totalAcus.toFixed(2)} ACU` : "—"}
                        </td>
                        <td>
                          {m.baseUsd != null && m.govUsd != null
                            ? `${formatCurrency(m.baseUsd)} → ${formatCurrency(m.govUsd)}`
                            : "Unpriced"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="empty-inline">No live model runs in this snapshot.</p>
            )}
          </div>
        )}
      </section>

      {/* Block 5: Compact Next-Step Strip */}
      <section className="explore-strip">
        <div className="explore-strip-icon">
          <SlidersIcon />
        </div>
        <div>
          <span className="eyebrow">NEXT STEPS</span>
          <h2>Test another rate card or inspect the raw logs</h2>
          <p>
            Reprice the recorded token workload on other models, or audit every
            run in the ledger.
          </p>
        </div>
        <div className="explore-strip-actions">
          <a href="#simulator" className="button button-outline">
            Open simulator <ArrowUpRight size={17} />
          </a>
          <a href="#audit" className="button button-primary">
            Evidence ledger <ArrowRight size={17} />
          </a>
        </div>
      </section>
    </>
  );
}

function SlidersIcon() {
  return <Cpu size={24} strokeWidth={1.5} />;
}
