import { useMemo, useState } from "react";
import {
  ArrowRight,
  ArrowUpRight,
  ArrowDownRight,
  CircleHelp,
  Cpu,
  FlaskConical,
  Orbit,
  ShieldCheck,
  TrendingDown,
} from "lucide-react";
import {
  DashboardPayload,
  HeadlineStat,
  RunRecord,
  TaskSummaryItem,
} from "../../types";
import { formatArm, formatCurrency, formatTokens } from "../../lib/formatters";
import {
  costSourceBreakdown,
  formatSignedCostChange,
  isPricedRun,
} from "../../lib/analytics";
import { armNames, experimentNames, finite, governedArm, governedArmName } from "../../lib/workspace";
import AdaptiveICM from "./AdaptiveICM";

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
        <ellipse
          cx="205"
          cy="130"
          rx="132"
          ry="83"
          fill="none"
          stroke="url(#orbit-line)"
          strokeWidth="1"
          transform="rotate(-18 205 130)"
        />
        <ellipse
          cx="205"
          cy="130"
          rx="100"
          ry="106"
          fill="none"
          stroke="#CDC3EE"
          strokeWidth="1"
          transform="rotate(44 205 130)"
        />
        <ellipse cx="205" cy="130" rx="57" ry="57" fill="#E2DAF8" />
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
        {[
          { x: 116, y: 61, t: "Intake" },
          { x: 286, y: 50, t: "Plan" },
          { x: 342, y: 149, t: "Execute" },
          { x: 233, y: 222, t: "Verify" },
          { x: 77, y: 172, t: "Reflect" },
        ].map(({ x, y, t }) => (
          <g key={t}>
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
        <circle cx="185" cy="30" r="4" fill="#A495D5" />
        <circle cx="308" cy="202" r="3" fill="#A495D5" />
        <circle cx="67" cy="108" r="3" fill="#A495D5" />
      </svg>
      <span>LESS NOISE. MORE SIGNAL.</span>
    </div>
  );
}

function Metric({ stat }: { stat: HeadlineStat }) {
  const isCost = stat.id === "cost_reduction";
  const isToken = stat.id === "tokens_per_pass";
  const isQuality = stat.id === "defect_rate";
  const Icon = isCost || isToken ? TrendingDown : isQuality ? ShieldCheck : Cpu;
  const label = isCost
    ? "Cost change vs baseline"
    : isToken
      ? "Tokens / passing patch"
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
        {isCost && stat.pooling_method ? ` · ${stat.pooling_method}` : ""}
        {stat.ci95 && (
          <span className="confidence">
            95% CI (exploratory): {stat.ci95[0]}% to {stat.ci95[1]}%
          </span>
        )}
      </div>
    </article>
  );
}

export function Overview({ data }: { data: DashboardPayload }) {
  const [benchModel, setBenchModel] = useState("all");
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
  const tokenBenchTasks = tasks.filter(
    (task) =>
      !pricedTasks.includes(task) &&
      (finite(task.arms.baseline?.tokens_per_passing_patch) ||
        finite(governedArm(task)?.tokens_per_passing_patch)),
  );
  const unpricedModels = useMemo(
    () =>
      Array.from(
        new Set(tokenBenchTasks.map(taskModel).filter(Boolean)),
      ).sort(),
    [tokenBenchTasks],
  );
  const visibleTokenBenchTasks =
    benchModel === "all"
      ? tokenBenchTasks
      : tokenBenchTasks.filter((task) => taskModel(task) === benchModel);
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
        const baseTokPass =
          basePassed > 0
            ? baseRuns.reduce((s, r) => s + runTokens(r), 0) / basePassed
            : null;
        const govTokPass =
          govPassed > 0
            ? govRuns.reduce((s, r) => s + runTokens(r), 0) / govPassed
            : null;
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
        const breakdown = costSourceBreakdown(runs);
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
          costBasis: breakdown.costBasisLabel,
          totalAcus: breakdown.totalAcus,
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
  const maxBenchTokens = Math.max(
    1,
    ...visibleTokenBenchTasks
      .flatMap((task) => [
        task.arms.baseline?.tokens_per_passing_patch,
        governedArm(task)?.tokens_per_passing_patch,
      ])
      .filter(finite),
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
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">THE BIG PICTURE</div>
          <h1>Your lab, at a glance.</h1>
          <p>
            A clearer view of what your agents spend—and what better context
            changes.
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
      <section className="thesis-panel">
        <div className="thesis-copy">
          <div className="eyebrow">
            <Orbit size={14} /> THE CONTEXT ADVANTAGE
          </div>
          <h2>
            Better context.
            <br />
            <span>Measurable impact.</span>
          </h2>
          <p>
            Compare unconstrained agents with a structured approach. Follow the
            costs, inspect the work, and make up your own mind.
          </p>
          <a href="#tasks" className="button button-primary">
            Explore experiments <ArrowRight size={17} />
          </a>
        </div>
        <ContextOrbit />
      </section>
      <AdaptiveICM data={data} />
      <div className="section-heading results-heading">
        <h2>What the evidence says</h2>
        <span>
          {headlineScope
            ? `${headlineScope.unique_task_count} tasks · ${headlineScope.total_run_count} runs · ${headlineScope.priced_run_count} priced runs · ${headlineScope.pooling_note || headlineScope.pooling_method}`
            : `${uniqueTasksCount} tasks · ${totalRunsCount} runs · ${pricedRunsCount} priced runs · pooled_sum (macro_average noted per task)`}
          {archivedRunsCount > 0
            ? ` (${liveRunsCount} live · ${archivedRunsCount} archived)`
            : ""}
          {unmeasuredSuites.length > 0
            ? ` · ${unmeasuredSuites.length} suite present, unmeasured`
            : ""}
        </span>
      </div>
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
      <div className="overview-grid">
        <section
          className="panel comparison-panel"
          aria-labelledby="comparison-title"
        >
          <div className="panel-heading">
            <div>
              <h2 id="comparison-title">The cost of context</h2>
              <p>Average cost per run, by experiment</p>
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
            {pricedTasks.map((task) => {
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
          <div className="panel-bottom">
            <span>
              USD per run ·{" "}
              {measured
                ? "Recorded usage estimates"
                : "Demo / non-measured data"}
            </span>
            <a className="text-link" href="#tasks">
              View breakdown <ArrowUpRight size={15} />
            </a>
          </div>
        </section>
        <aside className="reading-panel">
          <span className="reading-icon">
            <CircleHelp size={22} />
          </span>
          <div className="eyebrow">READING THE RESULTS</div>
          <h2>
            The whole picture.
            <br />
            Not just the headline.
          </h2>
          <p>
            Structure has a cost, too. Planning and verification can outweigh
            the savings on small tasks.
          </p>
          <div className="reading-divider" />
          <div className="reading-point">
            <ArrowDownRight size={20} />
            <div>
              <strong>Complex work benefits most</strong>
              <p>Compare each task before generalizing the aggregate result.</p>
            </div>
          </div>
          <div className="reading-point">
            <ShieldCheck size={20} />
            <div>
              <strong>Quality is its own measure</strong>
              <p>Defect rates come from a separate operational benchmark.</p>
            </div>
          </div>
          <div className="reading-point">
            <Cpu size={20} />
            <div>
              <strong>Projections stay separate</strong>
              <p>
                Model repricing estimates cost. It does not test another model.
              </p>
            </div>
          </div>
          <a className="text-link" href="#audit">
            Follow the evidence <ArrowRight size={16} />
          </a>
        </aside>
      </div>
      {modelSummaries.length > 1 && (
        <section
          className="panel operational-panel"
          aria-labelledby="cross-model-title"
        >
          <div className="panel-heading">
            <div>
              <span className="eyebrow">CROSS-MODEL BREAKDOWN</span>
              <h2 id="cross-model-title">
                Performance & token efficiency by model
              </h2>
              <p>
                Live non-imported runs grouped by model; tokens/pass includes
                tokens spent on failed runs.
              </p>
            </div>
            <span className="badge badge-purple">
              {modelSummaries.length} models · {liveRunsCount} live runs
            </span>
          </div>
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
                  <th scope="col">Cost basis</th>
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
                      {m.baseTools} ({m.baseErrors}) / {m.govTools} ({m.govErrors}
                      )
                    </td>
                    <td>
                      <span
                        className={`badge ${
                          m.costBasis === "Direct Billed"
                            ? "badge-green"
                            : m.costBasis === "ACU Derived"
                              ? "badge-blue"
                              : m.costBasis === "Direct Billed + ACU Derived"
                                ? "badge-purple"
                                : "badge-neutral"
                        }`}
                      >
                        {m.costBasis}
                      </span>
                      {m.totalAcus > 0 && (
                        <span className="cell-subtitle">
                          {m.totalAcus.toFixed(2)} ACU
                        </span>
                      )}
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
        </section>
      )}
      {tokenBenchTasks.length > 0 && (
        <section
          className="panel operational-panel comparison-panel"
          aria-labelledby="token-bench-title"
        >
          <div className="panel-heading">
            <div>
              <h2 id="token-bench-title">Multi-file benchmarks</h2>
              <p>
                Tokens per passing patch (unpriced{" "}
                {unpricedModels.length > 1 ? "models" : "model"})
              </p>
            </div>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "14px",
                flexWrap: "wrap",
              }}
            >
              {unpricedModels.length > 1 && (
                <label className="select-field">
                  Model
                  <select
                    value={benchModel}
                    onChange={(event) => setBenchModel(event.target.value)}
                  >
                    <option value="all">All models</option>
                    {unpricedModels.map((mdl) => (
                      <option key={mdl} value={mdl}>
                        {mdl}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              <div className="chart-legend">
                <span>
                  <i className="legend-baseline" />
                  Baseline
                </span>
                <span>
                  <i className="legend-governed" />
                  Governed
                </span>
              </div>
            </div>
          </div>
          <div
            className="cost-chart cost-chart-tokens"
            role="group"
            aria-label="Tokens per passing patch comparison for multi-file benchmarks."
          >
            {visibleTokenBenchTasks.map((task) => {
              const bArm = task.arms.baseline,
                gArm = governedArm(task);
              const bTok = bArm?.tokens_per_passing_patch,
                gTok = gArm?.tokens_per_passing_patch;
              const bDenom = bArm?.evaluated_count ?? bArm?.scheduled_count;
              const gDenom = gArm?.evaluated_count ?? gArm?.scheduled_count;
              const bPass =
                bArm?.verified_count != null && bDenom != null
                  ? ` (${bArm.verified_count}/${bDenom})`
                  : "";
              const gPass =
                gArm?.verified_count != null && gDenom != null
                  ? ` (${gArm.verified_count}/${gDenom})`
                  : "";
              const mdl = taskModel(task);
              return (
                <div className="chart-row" key={taskKey(task)}>
                  <a href="#tasks" className="chart-label">
                    {task.task_id}
                    <span>
                      {experimentNames[task.task_id] || "Benchmark"}
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
                          width: finite(bTok)
                            ? `${Math.max(1, (bTok / maxBenchTokens) * 100)}%`
                            : "0%",
                        }}
                      />
                      <span className="bar-value">
                        <span className="sr-only">Baseline </span>
                        {formatTokens(bTok)}
                        {bPass}
                      </span>
                    </div>
                    <div className="bar-line">
                      <span
                        className="bar bar-governed"
                        style={{
                          width: finite(gTok)
                            ? `${Math.max(1, (gTok / maxBenchTokens) * 100)}%`
                            : "0%",
                        }}
                      />
                      <span className="bar-value">
                        <span className="sr-only">{formatArm(governedArmName(task))} </span>
                        {formatTokens(gTok)}
                        {gPass}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
          <div className="panel-bottom">
            <span>
              Tokens per passing patch · rate card unpriced (excluded from USD totals)
            </span>
            <a className="text-link" href="#tasks">
              View breakdown <ArrowUpRight size={15} />
            </a>
          </div>
        </section>
      )}
      {data.quality_rubric?.has_data &&
        (() => {
          const rubric = data.quality_rubric;
          const pctCi = rubric.quality_ci.normalized_pct;
          const outlines = rubric.multi_file_outlines;
          const outlineSummary =
            outlines && outlines.length > 0
              ? (() => {
                  const totalBase = outlines.reduce(
                    (acc, item) => acc + item.baseline_cost_usd,
                    0,
                  );
                  const totalNorm = outlines.reduce(
                    (acc, item) => acc + item.icm_cost_normalized_usd,
                    0,
                  );
                  const totalRaw = outlines.reduce(
                    (acc, item) => acc + item.icm_cost_raw_usd,
                    0,
                  );
                  const normPct =
                    totalBase > 0
                      ? ((totalBase - totalNorm) / totalBase) * 100
                      : null;
                  const rawPct =
                    totalBase > 0
                      ? ((totalBase - totalRaw) / totalBase) * 100
                      : null;
                  return {
                    count: outlines.length,
                    totalBase,
                    totalNorm,
                    normPct,
                    rawPct,
                  };
                })()
              : null;
          const fmtSigned = (v: number, digits = 1) =>
            `${v >= 0 ? "+" : ""}${v.toFixed(digits)}`;
          const ciAboveZero = Boolean(pctCi.ci_95 && pctCi.ci_95[0] > 0);
          return (
            <section
              className="panel operational-panel"
              aria-labelledby="quality-rubric-title"
            >
              <div className="panel-heading">
                <div>
                  <span className="eyebrow">
                    5-DIMENSION QUALITY & BREAK-EVEN
                  </span>
                  <h2 id="quality-rubric-title">
                    Beyond token cost: quality CIs
                    {outlineSummary ? " & multi-file outlines" : ""}
                  </h2>
                  <p>
                    {rubric.quality_ci.sample_count} paired tasks ·
                    Pre-registered 0–25 rubric
                    {outlineSummary ? " & multi-file outlines" : ""}
                  </p>
                </div>
                {ciAboveZero && (
                  <span className="badge badge-green">
                    <ShieldCheck size={13} />
                    95% CI above zero
                  </span>
                )}
              </div>
              <div className="operational-stats">
                <div>
                  <span>Mean quality gain (ICM vs Baseline)</span>
                  <strong className="text-sea">
                    {pctCi.mean_delta != null
                      ? `${fmtSigned(pctCi.mean_delta)}%`
                      : "—"}
                  </strong>
                  {pctCi.ci_95 && (
                    <span>
                      95% CI: {fmtSigned(pctCi.ci_95[0])}% to{" "}
                      {fmtSigned(pctCi.ci_95[1])}%
                    </span>
                  )}
                </div>
                {outlineSummary && (
                  <div>
                    <span>
                      Multi-file outline savings ({outlineSummary.count} tasks)
                    </span>
                    <strong className="text-sea">
                      {outlineSummary.normPct !== null
                        ? `${fmtSigned(outlineSummary.normPct)}%`
                        : "—"}
                    </strong>
                    <span>
                      Normalized ({formatCurrency(outlineSummary.totalBase)} →{" "}
                      {formatCurrency(outlineSummary.totalNorm)}
                      {outlineSummary.rawPct !== null
                        ? ` · ${fmtSigned(outlineSummary.rawPct)}% raw`
                        : ""}
                      )
                    </span>
                  </div>
                )}
                {!outlineSummary &&
                  tokenBenchTasks.length > 0 &&
                  (() => {
                    const bTpps = tokenBenchTasks
                      .map((t) => t.arms.baseline?.tokens_per_passing_patch)
                      .filter(finite);
                    const gTpps = tokenBenchTasks
                      .map((t) => governedArm(t)?.tokens_per_passing_patch)
                      .filter(finite);
                    const bAvg = bTpps.length
                      ? bTpps.reduce((a, b) => a + b, 0) / bTpps.length
                      : null;
                    const gAvg = gTpps.length
                      ? gTpps.reduce((a, b) => a + b, 0) / gTpps.length
                      : null;
                    const deltaPct =
                      bAvg != null && bAvg > 0 && gAvg != null
                        ? ((bAvg - gAvg) / bAvg) * 100
                        : null;
                    const bPass = tokenBenchTasks.reduce(
                      (s, t) => s + (t.arms.baseline?.verified_count ?? 0),
                      0,
                    );
                    const bSched = tokenBenchTasks.reduce(
                      (s, t) =>
                        s +
                        (t.arms.baseline?.evaluated_count ??
                          t.arms.baseline?.scheduled_count ??
                          0),
                      0,
                    );
                    const gPass = tokenBenchTasks.reduce(
                      (s, t) => s + (governedArm(t)?.verified_count ?? 0),
                      0,
                    );
                    const gSched = tokenBenchTasks.reduce(
                      (s, t) =>
                        s +
                        (governedArm(t)?.evaluated_count ??
                          governedArm(t)?.scheduled_count ??
                          0),
                      0,
                    );
                    return (
                      <div>
                        <span>
                          Multi-file token efficiency ({tokenBenchTasks.length}{" "}
                          tasks)
                        </span>
                        <strong
                          className={
                            deltaPct != null && deltaPct >= 0
                              ? "text-sea"
                              : "text-rust"
                          }
                        >
                          {deltaPct != null ? `${fmtSigned(deltaPct)}%` : "—"}
                        </strong>
                        <span>
                          {formatTokens(bAvg)} → {formatTokens(gAvg)} tok/pass
                          {bSched > 0 && gSched > 0
                            ? ` · ${gPass}/${gSched} ICM vs ${bPass}/${bSched} base`
                            : ""}
                        </span>
                      </div>
                    );
                  })()}
                {rubric.tool_errors != null && (
                  <div>
                    <span>Tool & path execution errors</span>
                    <strong>
                      {rubric.tool_errors.icm} vs {rubric.tool_errors.baseline}
                    </strong>
                    <span>
                      {rubric.tool_errors.reduction_percent != null
                        ? `${rubric.tool_errors.reduction_percent.toFixed(1)}% reduction in DB-linked NDJSON logs`
                        : "Tracked in DB-linked NDJSON logs"}
                    </span>
                  </div>
                )}
              </div>
            </section>
          );
        })()}
      <section className="explore-strip">
        <div className="explore-strip-icon">
          <SlidersIcon />
        </div>
        <div>
          <span className="eyebrow">YOUR NEXT QUESTION</span>
          <h2>What would this cost on another model?</h2>
          <p>Use the same token workload. Explore a different rate card.</p>
        </div>
        <a href="#simulator" className="button button-outline">
          Open simulator <ArrowUpRight size={17} />
        </a>
      </section>
    </>
  );
}

function SlidersIcon() {
  return <Cpu size={24} strokeWidth={1.5} />;
}
