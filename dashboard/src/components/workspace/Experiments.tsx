import { useMemo, useState } from "react";
import {
  ArrowDownRight,
  ArrowUpRight,
  ChevronDown,
  FlaskConical,
  Search,
} from "lucide-react";
import { DashboardPayload } from "../../types";
import { experimentNames, finite, governedArm } from "../../lib/workspace";
import { formatCurrency, formatTokens } from "../../lib/formatters";

export default function Experiments({ data }: { data: DashboardPayload }) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("all");
  const tasks = useMemo(
    () =>
      (data.tasks || []).filter((task) => {
        const matches = `${task.task_id} ${experimentNames[task.task_id] || ""}`
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
        return (
          matches &&
          (filter === "all" ||
            (finite(delta) && (filter === "savings" ? delta > 0 : delta < 0)))
        );
      }),
    [data.tasks, query, filter],
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
          {data.tasks?.length || 0} experiments
        </span>
      </div>
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
          Show
          <select
            value={filter}
            onChange={(event) => setFilter(event.target.value)}
          >
            <option value="all">All results</option>
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
          const fmtPass = (arm?: typeof baseline) =>
            arm?.verified_count != null && arm?.scheduled_count != null
              ? `${arm.verified_count}/${arm.scheduled_count}`
              : "—";
          const fmtTools = (arm?: typeof baseline) =>
            arm?.total_tool_calls != null
              ? `${arm.total_tool_calls} (${arm.total_tool_errors ?? 0} err)`
              : "—";
          return (
            <article key={task.task_id} className="panel experiment-card">
              <div className="experiment-card-heading">
                <div className="experiment-identity">
                  <span className="experiment-glyph">
                    <FlaskConical size={22} strokeWidth={1.5} />
                  </span>
                  <div>
                    <span className="eyebrow">{task.task_id}</span>
                    <h2>{experimentNames[task.task_id] || task.task_id}</h2>
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
                    <div>
                      <span>Governed tok / pass</span>
                      <strong>{formatTokens(gTok)}</strong>
                    </div>
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
                    <div>
                      <span>Governed cost / run</span>
                      <strong>{formatCurrency(governed?.mean_cost_usd)}</strong>
                    </div>
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
                        <th scope="col">Baseline</th>
                        <th scope="col">Governed</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[
                        ["Pass rate", fmtPass(baseline), fmtPass(governed)],
                        [
                          "Tokens / pass",
                          formatTokens(bTok),
                          formatTokens(gTok),
                        ],
                        [
                          "Input tokens",
                          formatTokens(baseline?.mean_input_tokens),
                          formatTokens(governed?.mean_input_tokens),
                        ],
                        [
                          "Cache read tokens",
                          formatTokens(baseline?.mean_cache_read_tokens),
                          formatTokens(governed?.mean_cache_read_tokens),
                        ],
                        [
                          "Output tokens",
                          formatTokens(baseline?.mean_output_tokens),
                          formatTokens(governed?.mean_output_tokens),
                        ],
                        [
                          "Thinking tokens",
                          formatTokens(baseline?.mean_thinking_tokens),
                          formatTokens(governed?.mean_thinking_tokens),
                        ],
                        ["Duration", fmtDur(baseline), fmtDur(governed)],
                        [
                          "Agent turns",
                          baseline?.mean_num_turns ?? "—",
                          governed?.mean_num_turns ?? "—",
                        ],
                        [
                          "Tool calls (errors)",
                          fmtTools(baseline),
                          fmtTools(governed),
                        ],
                        [
                          "Loop flags",
                          baseline?.loop_runs_count != null
                            ? String(baseline.loop_runs_count)
                            : "—",
                          governed?.loop_runs_count != null
                            ? String(governed.loop_runs_count)
                            : "—",
                        ],
                        [
                          "Model",
                          baseline?.model || "—",
                          governed?.model || "—",
                        ],
                      ].map(([label, b, g]) => (
                        <tr key={label}>
                          <th scope="row">{label}</th>
                          <td>{b}</td>
                          <td>{g}</td>
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
    </>
  );
}
