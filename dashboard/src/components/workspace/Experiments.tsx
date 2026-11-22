import { useMemo, useState } from "react";
import {
  ArrowDownRight,
  ArrowUpRight,
  ChevronDown,
  FlaskConical,
  Search,
} from "lucide-react";
import { ArmStats, DashboardPayload, TaskSummaryItem } from "../../types";
import { armNames, experimentNames, finite, governedArm } from "../../lib/workspace";
import { isPricedRun, pairedDiffStats, suitePairsDetailed } from "../../lib/analytics";
import { formatArm, formatCurrency, formatSignedPercent, formatTokens } from "../../lib/formatters";
import AdaptiveICM from "./AdaptiveICM";

export default function Experiments({ data }: { data: DashboardPayload }) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("all");
  const [model, setModel] = useState("all");
  const models = useMemo(
    () =>
      Array.from(
        new Set(
          (data.tasks || [])
            .map((t) => t.model || t.arms.baseline?.model || governedArm(t)?.model || "")
            .filter(Boolean),
        ),
      ).sort(),
    [data.tasks],
  );
  const uniqueTaskCount = useMemo(
    () => new Set((data.tasks || []).map((t) => t.task_id)).size,
    [data.tasks],
  );
  const governedNames = (task: TaskSummaryItem) =>
    armNames(task).filter((n) => n !== "baseline");
  const tasks = useMemo(
    () =>
      (data.tasks || []).filter((task) => {
        const mdl =
          task.model ||
          task.arms.baseline?.model ||
          governedArm(task)?.model ||
          "";
        const matches = `${task.task_id} ${experimentNames[task.task_id] || ""} ${mdl}`
          .toLowerCase()
          .includes(query.toLowerCase());
        const bTok = task.arms.baseline?.tokens_per_passing_patch;
        const gTok = governedArm(task)?.tokens_per_passing_patch;
        const tokDelta =
          finite(bTok) && bTok > 0 && finite(gTok)
            ? ((bTok - gTok) / bTok) * 100
            : undefined;
        const delta = finite(task.savings?.mean_savings_percent)
          ? task.savings?.mean_savings_percent
          : tokDelta;
        const taskRuns = task.arms.baseline?.runs || [];
        const priced =
          taskRuns.some(isPricedRun) ||
          governedNames(task).some((n) =>
            (task.arms[n]?.runs || []).some(isPricedRun),
          ) ||
          (task.excluded_runs || []).some(isPricedRun);
        return (
          matches &&
          (model === "all" || mdl === model) &&
          (filter === "all" ||
            (filter === "priced" ? priced : filter === "unpriced" ? !priced :
              finite(delta) && (filter === "savings" ? delta > 0 : delta < 0)))
        );
      }),
    [data.tasks, query, filter, model],
  );
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">LOOK CLOSER</div>
          <h1>Every experiment tells a story.</h1>
          <p>
            Same task. Two approaches. Explore the tradeoffs behind each result.
          </p>
        </div>
        <span className="badge badge-purple">
          <FlaskConical size={14} />
          {data.tasks?.length || 0} series · {uniqueTaskCount} tasks
        </span>
      </div>
      <AdaptiveICM data={data} />
      <div className="toolbar">
        <label className="search-field">
          <Search size={18} />
          <span className="sr-only">Search experiments</span>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search experiments…"
          />
        </label>
        <label className="select-field">
          Model
          <select
            value={model}
            onChange={(event) => setModel(event.target.value)}
          >
            <option value="all">All models</option>
            {models.map((mdl) => (
              <option key={mdl} value={mdl}>
                {mdl}
              </option>
            ))}
          </select>
        </label>
        <label className="select-field">
          Show
          <select
            value={filter}
            onChange={(event) => setFilter(event.target.value)}
          >
            <option value="all">All results</option>
            <option value="priced">Priced only</option>
            <option value="unpriced">Unpriced only</option>
            <option value="savings">Cost savings</option>
            <option value="overhead">Cost overhead</option>
          </select>
        </label>
        <span className="result-count" role="status">
          {tasks.length} {tasks.length === 1 ? "result" : "results"}
        </span>
      </div>
      <div className="experiment-list">
        {tasks.map((task) => {
          const baseline = task.arms.baseline,
            governed = governedArm(task),
            reduction = task.savings?.mean_savings_percent;
          const measured =
            !data.is_demo_report &&
            !data.is_simulation &&
            !task.is_simulation &&
            Boolean(task.has_measured_data);
          const isTokenOnly =
            !measured &&
            (finite(baseline?.tokens_per_passing_patch) ||
              finite(governed?.tokens_per_passing_patch));
          const bTok = baseline?.tokens_per_passing_patch;
          const gTok = governed?.tokens_per_passing_patch;
          const tokenReduction =
            finite(bTok) && bTok > 0 && finite(gTok)
              ? ((bTok - gTok) / bTok) * 100
              : undefined;
          const activeDelta = finite(reduction)
            ? reduction
            : isTokenOnly
              ? tokenReduction
              : undefined;
          const lower = finite(activeDelta) && activeDelta > 0;
          const fmtDur = (arm?: typeof baseline) => {
            if (!arm || !finite(arm.mean_duration_seconds)) return "—";
            if (arm.mean_duration_seconds === 0 && !arm.completed_count)
              return "—";
            return `${arm.mean_duration_seconds.toFixed(1)}s`;
          };
          const fmtPass = (arm?: typeof baseline) => {
            const denom = arm?.evaluated_count ?? arm?.scheduled_count;
            return arm?.verified_count != null && denom != null
              ? `${arm.verified_count}/${denom}`
              : "—";
          };
          const fmtTools = (arm?: typeof baseline) =>
            arm?.total_tool_calls != null
              ? `${arm.total_tool_calls} (${arm.total_tool_errors ?? 0} err)`
              : "—";
          const cardModel =
            task.model || baseline?.model || governed?.model || "";
          const cardKey = task.series_id || `${task.task_id}::${cardModel}`;
          const arms = armNames(task);
          const governedNames = arms.filter((n) => n !== "baseline");
          const pairMatchByArm = Object.fromEntries(
            governedNames.map((n) => [
              n,
              suitePairsDetailed(
                task,
                n,
                isTokenOnly
                  ? (r) => (finite(r.total_tokens) ? r.total_tokens : null)
                  : (r) => (isPricedRun(r) ? (r.cost_usd as number) : null),
              ),
            ]),
          );
          const statsByArm = Object.fromEntries(
            governedNames.map((n) => [
              n,
              pairedDiffStats(pairMatchByArm[n].pairs),
            ]),
          );
          const ciByArm = Object.fromEntries(
            governedNames.map((n) => [n, statsByArm[n]?.ci95 ?? null]),
          );
          const armBadges = (name: string) => {
            const st = statsByArm[name];
            const pm = pairMatchByArm[name];
            if (!st) return null;
            return (
              <span className="effect-badges">
                {st.preliminary ? (
                  <span className="badge badge-amber">
                    preliminary (n={st.n})
                  </span>
                ) : st.displayEffectSize ? (
                  <span className="badge badge-blue">
                    d<sub>z</sub>{" "}
                    {st.displayCohensDz != null
                      ? Math.abs(st.displayCohensDz).toFixed(2)
                      : "—"}{" "}
                    · {st.displayEffectSize} (n={st.n})
                  </span>
                ) : null}{" "}
                {st.significant != null && (
                  <span
                    className={`badge ${st.significant ? "badge-green" : "badge-amber"}`}
                  >
                    {st.significant ? "exploratory significant" : "not significant"}
                  </span>
                )}
                {pm && pm.droppedCount > 0 && (
                  <span className="badge badge-neutral">
                    {pm.droppedCount} dropped
                    {pm.hashMismatchedCount > 0
                      ? ` (${pm.hashMismatchedCount} hash mismatch)`
                      : ""}
                  </span>
                )}
              </span>
            );
          };
          return (
            <article key={cardKey} className="panel experiment-card">
              <div className="experiment-card-heading">
                <div className="experiment-identity">
                  <span className="experiment-glyph">
                    <FlaskConical size={22} strokeWidth={1.5} />
                  </span>
                  <div>
                    <span className="eyebrow">
                      {task.task_id}
                      {cardModel ? ` · ${cardModel}` : ""}
                    </span>
                    <h2>{experimentNames[task.task_id] || task.task_id}</h2>
                    <span className="badge badge-neutral">Baseline</span>{" "}
                    {governedNames.map((n) => (
                      <span key={n} className="badge badge-purple">{formatArm(n)}</span>
                    ))}{" "}
                  </div>
                </div>
                <span
                  className={`badge ${measured ? "badge-green" : isTokenOnly ? "badge-blue" : "badge-amber"}`}
                >
                  {measured
                    ? "Measured"
                    : isTokenOnly
                      ? "Token-verified"
                      : "Non-measured"}{" "}
                  · {task.total_runs} runs
                </span>
              </div>
              <div className="experiment-metrics">
                {isTokenOnly ? (
                  <>
                    <div>
                      <span>Baseline tok / pass</span>
                      <strong>{formatTokens(bTok)}</strong>
                    </div>
                    {governedNames.map((name) => (
                      <div key={name}>
                        <span>{formatArm(name)} tok / pass</span>
                        <strong>
                          {formatTokens(task.arms[name]?.tokens_per_passing_patch)}
                        </strong>
                        {armBadges(name)}
                      </div>
                    ))}
                    <div>
                      <span>
                        {lower ? "Token reduction" : "Token overhead"}
                      </span>
                      <strong
                        className={
                          lower
                            ? "text-sea"
                            : finite(activeDelta)
                              ? "text-rust"
                              : ""
                        }
                      >
                        {finite(activeDelta) ? (
                          lower ? (
                            <ArrowDownRight size={20} />
                          ) : (
                            <ArrowUpRight size={20} />
                          )
                        ) : null}
                        {finite(activeDelta)
                          ? ` ${Math.abs(activeDelta).toFixed(1)}%`
                          : "—"}
                      </strong>
                    </div>
                  </>
                ) : (
                  <>
                    <div>
                      <span>Baseline cost / run</span>
                      <strong>{formatCurrency(baseline?.mean_cost_usd)}</strong>
                    </div>
                    {governedNames.map((name) => {
                      const arm = task.arms[name];
                      const ci = ciByArm[name];
                      return (
                        <div key={name}>
                          <span>{formatArm(name)} cost / run</span>
                          <strong>{formatCurrency(arm?.mean_cost_usd)}</strong>
                          {ci && (
                            <span className="confidence">
                              95% CI Δ {formatSignedPercent(ci[0])} to{" "}
                              {formatSignedPercent(ci[1])}
                            </span>
                          )}
                          {armBadges(name)}
                        </div>
                      );
                    })}
                    <div>
                      <span>{lower ? "Cost reduction" : "Cost overhead"}</span>
                      <strong
                        className={
                          lower
                            ? "text-sea"
                            : finite(reduction)
                              ? "text-rust"
                              : ""
                        }
                      >
                        {finite(reduction) ? (
                          lower ? (
                            <ArrowDownRight size={20} />
                          ) : (
                            <ArrowUpRight size={20} />
                          )
                        ) : null}
                        {finite(reduction)
                          ? ` ${Math.abs(reduction).toFixed(1)}%`
                          : "—"}
                      </strong>
                    </div>
                  </>
                )}
              </div>
              <details className="experiment-details">
                <summary>
                  Inspect comparison <ChevronDown size={16} />
                </summary>
                <div
                  className="table-scroll"
                  role="region"
                  aria-label={`${task.task_id} comparison details`}
                  tabIndex={0}
                >
                  <table className="data-table">
                    <caption className="sr-only">
                      {task.task_id} baseline and governed usage
                    </caption>
                    <thead>
                      <tr>
                        <th scope="col">Per-run measure</th>
                        {arms.map((n) => (
                          <th key={n} scope="col">{formatArm(n)}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {([
                        ["Pass rate", (a) => fmtPass(a)],
                        [
                          "Tokens / pass",
                          (a) => formatTokens(a?.tokens_per_passing_patch),
                        ],
                        [
                          "Input tokens",
                          (a) => formatTokens(a?.mean_input_tokens),
                        ],
                        [
                          "Cache read tokens",
                          (a) => formatTokens(a?.mean_cache_read_tokens),
                        ],
                        [
                          "Output tokens",
                          (a) => formatTokens(a?.mean_output_tokens),
                        ],
                        [
                          "Thinking tokens",
                          (a) => formatTokens(a?.mean_thinking_tokens),
                        ],
                        ["Duration", (a) => fmtDur(a)],
                        [
                          "Agent turns",
                          (a) => a?.mean_num_turns ?? "—",
                        ],
                        ["Tool calls (errors)", (a) => fmtTools(a)],
                        [
                          "Loop flags",
                          (a) =>
                            a?.loop_runs_count != null
                              ? String(a.loop_runs_count)
                              : "—",
                        ],
                        ["Model", (a) => a?.model || "—"],
                        [
                          "95% CI cost Δ vs baseline",
                          (_a, name) =>
                            name === "baseline"
                              ? "—"
                              : ciByArm[name]
                                ? `${formatSignedPercent(ciByArm[name][0])} to ${formatSignedPercent(ciByArm[name][1])}`
                                : "—",
                        ],
                      ] as [string, (a: ArmStats | undefined, name: string) => React.ReactNode][]).map(([label, cell]) => (
                        <tr key={label}>
                          <th scope="row">{label}</th>
                          {arms.map((name) => (
                            <td key={name}>
                              {cell(task.arms[name], name)}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {task.exclusion_reasons?.length ? (
                  <p className="notice notice-amber">
                    Excluded: {task.exclusion_reasons.join(", ")}
                  </p>
                ) : null}
                <a className="text-link" href="#audit">
                  Inspect source records <ArrowUpRight size={15} />
                </a>
              </details>
            </article>
          );
        })}
        {!tasks.length && (
          <div className="panel empty-state">
            <Search size={30} />
            <h2>No matching experiments.</h2>
            <p>Try another name or clear the filters.</p>
            <button
              className="button button-outline"
              onClick={() => {
                setQuery("");
                setFilter("all");
                setModel("all");
              }}
            >
              Clear filters
            </button>
          </div>
        )}
      </div>
      {data.operational?.has_data && data.operational.summary && (
        <section className="panel operational-panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">A SEPARATE LENS</span>
              <h2>Operational quality benchmark</h2>
              <p>
                {data.operational.model} · {data.operational.summary.total_runs}{" "}
                runs · {data.operational.provider}
              </p>
            </div>
            <span className="badge badge-purple">Quality & duration</span>
          </div>
          <div className="operational-stats">
            <div>
              <span>Baseline defect runs</span>
              <strong>
                {data.operational.summary.baseline.defect_runs != null
                  ? `${data.operational.summary.baseline.defect_runs} / ${data.operational.summary.baseline.runs}`
                  : "Not tracked"}
              </strong>
            </div>
            <div>
              <span>Governed defect runs</span>
              <strong>
                {data.operational.summary.icm.defect_runs != null
                  ? `${data.operational.summary.icm.defect_runs} / ${data.operational.summary.icm.runs}`
                  : "Not tracked"}
              </strong>
            </div>
            <div>
              <span>Governed duration overhead</span>
              <strong>
                {finite(data.operational.summary.duration_overhead_percent)
                  ? `${data.operational.summary.duration_overhead_percent.toFixed(1)}%`
                  : "—"}
              </strong>
            </div>
          </div>
          <p className="panel-note">
            Provider token counters are unavailable. These results describe
            quality and duration, and are excluded from measured token-cost
            totals.
          </p>
        </section>
      )}
      {data.quality_rubric?.has_data && (
        <section className="panel operational-panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">
                {data.quality_rubric.multi_file_outlines?.length
                  ? "MULTI-FILE REPOSITORY OUTLINES & QUALITY JUDGE"
                  : "5-DIMENSION QUALITY JUDGE"}
              </span>
              <h2>
                5-dimension quality rubric
                {data.quality_rubric.multi_file_outlines?.length
                  ? " & multi-file outlines"
                  : ""}
              </h2>
              <p>
                Pre-registered 0–25 quality scoring across paired benchmark tasks
              </p>
            </div>
            {(() => {
              const norm = data.quality_rubric.quality_ci.normalized_pct;
              const fmtSigned = (v: number, digits = 1) =>
                `${v >= 0 ? "+" : ""}${v.toFixed(digits)}`;
              return norm.mean_delta != null ? (
                <span className="badge badge-green">
                  {fmtSigned(norm.mean_delta)}% quality
                  {norm.ci_95
                    ? ` (95% CI: ${fmtSigned(norm.ci_95[0])}% to ${fmtSigned(norm.ci_95[1])}%)`
                    : ""}
                </span>
              ) : null;
            })()}
          </div>
          {data.quality_rubric.multi_file_outlines?.length ? (
            <div
              className="table-scroll"
              role="region"
              aria-label="Multi-file outline pricing and turn comparison"
              tabIndex={0}
            >
              <table className="data-table">
                <thead>
                  <tr>
                    <th scope="col">Task (Files)</th>
                    <th scope="col">Baseline (Turns · Cost)</th>
                    <th scope="col">ICM Raw (Turns · Cost)</th>
                    <th scope="col">ICM Cold-Normalized</th>
                    <th scope="col">Savings (Raw / Norm)</th>
                  </tr>
                </thead>
                <tbody>
                  {data.quality_rubric.multi_file_outlines.map((item) => (
                    <tr key={item.task_id}>
                      <th scope="row">
                        {item.task_id} — {item.title} ({item.files} files)
                      </th>
                      <td>
                        {item.baseline_turns} turns · {formatCurrency(item.baseline_cost_usd)}
                      </td>
                      <td>
                        {item.icm_turns} turns · {formatCurrency(item.icm_cost_raw_usd)}
                      </td>
                      <td>{formatCurrency(item.icm_cost_normalized_usd)}</td>
                      <td className="text-sea">
                        {item.raw_savings_percent > 0 ? `+${item.raw_savings_percent}%` : `${item.raw_savings_percent}%`} / +{item.normalized_savings_percent}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
          <div
            className="table-scroll"
            role="region"
            aria-label="5-dimension quality rubric scores"
            tabIndex={0}
          >
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">Task</th>
                  <th scope="col">Baseline Quality</th>
                  <th scope="col">Governed (ICM) Quality</th>
                  <th scope="col">Delta</th>
                </tr>
              </thead>
              <tbody>
                {data.quality_rubric.tasks.map((row) => {
                  const delta = +(row.governed.normalized_pct - row.baseline.normalized_pct).toFixed(1);
                  return (
                    <tr key={row.task_id}>
                      <th scope="row">
                        {row.task_id} — {experimentNames[row.task_id] || row.task_id}
                      </th>
                      <td>
                        {row.baseline.total}/{row.baseline.max_possible} ({row.baseline.normalized_pct}%)
                      </td>
                      <td>
                        {row.governed.total}/{row.governed.max_possible} ({row.governed.normalized_pct}%)
                      </td>
                      <td className={delta > 0 ? "text-sea" : ""}>
                        {delta > 0 ? `+${delta}%` : `${delta}%`}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="panel-note">
            Dimensions (0–5 each): Correctness, Engineering Practices,
            Maintainability (AST LOC), Process Discipline (scope & tool
            hygiene), and Design/A11y
            {(() => {
              const designCi = data.quality_rubric.quality_ci.design;
              if (!designCi || designCi.mean_delta == null) return "";
              const fmtPt = (v: number) => `${v >= 0 ? "+" : ""}${v.toFixed(2)}`;
              const ciStr = designCi.ci_95
                ? `, 95% CI: ${fmtPt(designCi.ci_95[0])} to ${fmtPt(designCi.ci_95[1])}`
                : "";
              return ` (${fmtPt(designCi.mean_delta)} pt mean gain${ciStr})`;
            })()}
            .
          </p>
        </section>
      )}
      {(() => {
        const unmeasured = (data.declared_benchmarks || []).filter(
          (b) => b.measured_runs === 0 || b.status === "suite present, unmeasured",
        );
        if (!unmeasured.length) return null;
        return (
          <section
            className="panel operational-panel"
            aria-labelledby="unmeasured-suites-title"
          >
            <div className="panel-heading">
              <div>
                <span className="eyebrow">BENCHMARK INVENTORY</span>
                <h2 id="unmeasured-suites-title">Declared suites without runs</h2>
                <p>
                  Cross-checked against declared benchmark directories; suites
                  with zero measured runs are labeled explicitly.
                </p>
              </div>
              <span className="badge badge-amber">
                {unmeasured.length} unmeasured
              </span>
            </div>
            <div className="adaptive-measured">
              {unmeasured.map((suite) => (
                <span key={suite.task_id} className="adaptive-arm-chip">
                  <strong>{suite.task_id}</strong>{" "}
                  <span className="badge badge-amber">
                    suite present, unmeasured
                  </span>
                </span>
              ))}
            </div>
          </section>
        );
      })()}
    </>
  );
}
