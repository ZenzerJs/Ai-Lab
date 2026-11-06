import { useMemo, useState } from "react";
import {
  ArrowDownToLine,
  ArrowDownUp,
  ChevronLeft,
  ChevronRight,
  Search,
  ShieldCheck,
  ShieldAlert,
} from "lucide-react";
import { DashboardPayload } from "../../types";
import { downloadJson, snapshotDate } from "../../lib/workspace";
import { formatCurrency, formatTokens } from "../../lib/formatters";
import { ProviderIcon } from "./ProviderIcon";

export default function Evidence({ data }: { data: DashboardPayload }) {
  const [query, setQuery] = useState("");
  const [task, setTask] = useState("all");
  const [arm, setArm] = useState("all");
  const [source, setSource] = useState("all");
  const [evidence, setEvidence] = useState("all");
  const [ascending, setAscending] = useState(true);
  const [page, setPage] = useState(1);
  const [exported, setExported] = useState(false);
  const filtered = useMemo(
    () =>
      (data.runs || [])
        .filter(
          (run) =>
            (task === "all" || run.task_id === task) &&
            (arm === "all" || run.arm === arm) &&
            (source === "all" || (run.source_kind || "unknown") === source) &&
            (evidence === "all" ||
              (run.evidence_status || "missing") === evidence) &&
            `${run.id} ${run.task_id} ${run.model} ${run.evidence_ref || ""} ${run.notes || ""}`
              .toLowerCase()
              .includes(query.toLowerCase()),
        )
        .sort((a, b) => (ascending ? a.id - b.id : b.id - a.id)),
    [data.runs, query, task, arm, source, evidence, ascending],
  );
  const pages = Math.max(1, Math.ceil(filtered.length / 10));
  const currentPage = Math.min(page, pages);
  const rows = filtered.slice((currentPage - 1) * 10, currentPage * 10);
  const reset = () => {
    setQuery("");
    setTask("all");
    setArm("all");
    setSource("all");
    setEvidence("all");
    setPage(1);
  };
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">SHOW YOUR WORK</div>
          <h1>Evidence, down to the run.</h1>
          <p>
            Trace every number to its source. Filter, inspect, and take the
            records with you.
          </p>
        </div>
        <span className="badge badge-purple">
          <ShieldCheck size={14} />
          Provenance ledger
        </span>
      </div>
      <section className="ledger-summary">
        <div>
          <span>Total records</span>
          <strong>{data.runs?.length || 0}</strong>
        </div>
        <div>
          <span>Verified evidence</span>
          <strong>
            {data.runs?.filter((run) => run.evidence_status === "verified")
              .length || 0}
          </strong>
        </div>
        <div>
          <span>Comparison eligible</span>
          <strong>
            {data.runs?.filter((run) => run.is_comparison_eligible).length || 0}
          </strong>
        </div>
        <div>
          <span>Snapshot</span>
          <strong className="date-value">
            {snapshotDate(data.generated_at)}
          </strong>
        </div>
      </section>
      <section className="panel">
        <div className="ledger-toolbar">
          <label className="search-field">
            <Search size={18} />
            <span className="sr-only">Search evidence</span>
            <input
              placeholder="Search task, model, or evidence…"
              value={query}
              onChange={(event) => {
                setQuery(event.target.value);
                setPage(1);
              }}
            />
          </label>
          <button
            className="button button-outline"
            onClick={() => {
              downloadJson(
                {
                  generated_at: data.generated_at,
                  build_identity: data.build_identity,
                  filters: { query, task, arm, source, evidence },
                  runs: filtered,
                },
                "ai-lab-evidence.json",
              );
              setExported(true);
            }}
          >
            <ArrowDownToLine size={16} />
            Export filtered JSON
          </button>
        </div>
        <div className="ledger-filters">
          {[
            {
              label: "Task",
              value: task,
              set: setTask,
              values: Array.from(new Set(data.runs.map((run) => run.task_id))),
            },
            {
              label: "Arm",
              value: arm,
              set: setArm,
              values: Array.from(new Set(data.runs.map((run) => run.arm))),
            },
            {
              label: "Source",
              value: source,
              set: setSource,
              values: Array.from(
                new Set(data.runs.map((run) => run.source_kind || "unknown")),
              ),
            },
            {
              label: "Evidence status",
              value: evidence,
              set: setEvidence,
              values: Array.from(
                new Set(
                  data.runs.map((run) => run.evidence_status || "missing"),
                ),
              ),
            },
          ].map((filter) => (
            <label className="field-label" key={filter.label}>
              {filter.label}
              <select
                value={filter.value}
                onChange={(event) => {
                  filter.set(event.target.value);
                  setPage(1);
                }}
              >
                <option value="all">
                  All {filter.label.toLowerCase()}
                  {filter.label === "Evidence status" ? "es" : "s"}
                </option>
                {filter.values.sort().map((value) => (
                  <option value={value} key={value}>
                    {value}
                  </option>
                ))}
              </select>
            </label>
          ))}
          <button className="button button-quiet" onClick={reset}>
            Clear filters
          </button>
        </div>
        <div
          className="table-scroll"
          role="region"
          aria-label="Evidence records"
          tabIndex={0}
        >
          <table className="data-table evidence-table">
            <caption className="sr-only">
              Source evidence and costs for each agent run
            </caption>
            <thead>
              <tr>
                <th
                  scope="col"
                  aria-sort={ascending ? "ascending" : "descending"}
                >
                  <button
                    className="sort-button"
                    onClick={() => setAscending((value) => !value)}
                  >
                    Run <ArrowDownUp size={13} />
                  </button>
                </th>
                <th scope="col">Experiment / model</th>
                <th scope="col">Arm / source</th>
                <th scope="col">Input tokens</th>
                <th scope="col">Cost</th>
                <th scope="col">Evidence</th>
                <th scope="col">Details</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((run) => (
                <tr key={run.id}>
                  <th scope="row" className="mono">
                    #{run.id}
                  </th>
                  <td>
                    <div className="ledger-record">
                      <ProviderIcon model={run.model} />
                      <span className="ledger-record-text">
                        <strong>{run.task_id}</strong>
                        <span className="cell-subtitle">{run.model}</span>
                      </span>
                    </div>
                  </td>
                  <td>
                    <span
                      className={`badge ${run.arm === "baseline" ? "badge-neutral" : "badge-purple"}`}
                    >
                      {run.arm}
                    </span>
                    <span className="cell-subtitle">
                      {run.source_kind || "unknown"}
                      {run.is_simulation ? " · simulation" : ""}
                    </span>
                  </td>
                  <td>{formatTokens(run.input_tokens)}</td>
                  <td>
                    {formatCurrency(run.cost_usd)}
                    <span className="cell-subtitle">
                      {run.cost_status || "unknown"}
                    </span>
                  </td>
                  <td>
                    <span
                      className={`evidence-status ${run.evidence_status === "verified" ? "is-verified" : ""}`}
                    >
                      {run.evidence_status === "verified" ? (
                        <ShieldCheck size={14} />
                      ) : (
                        <ShieldAlert size={14} />
                      )}
                      {run.evidence_status || "missing"}
                    </span>
                  </td>
                  <td>
                    <details className="run-details">
                      <summary aria-label={`Inspect run ${run.id}`}>
                        Inspect
                      </summary>
                      <dl>
                        <dt>Evidence reference</dt>
                        <dd>{run.evidence_ref || "Not supplied"}</dd>
                        <dt>Execution / verification</dt>
                        <dd>
                          {run.execution_status || "unknown"} /{" "}
                          {run.verification_status || "not_run"}
                        </dd>
                        <dt>Comparison eligible</dt>
                        <dd>{run.is_comparison_eligible ? "Yes" : "No"}</dd>
                        <dt>Input / cache / output / thinking</dt>
                        <dd>
                          {formatTokens(run.input_tokens)} /{" "}
                          {formatTokens(run.cache_read_tokens)} /{" "}
                          {formatTokens(run.output_tokens)} /{" "}
                          {formatTokens(run.thinking_tokens)}
                        </dd>
                        <dt>Recorded</dt>
                        <dd>{run.timestamp}</dd>
                        {run.exclusion_reasons?.length ? (
                          <>
                            <dt>Exclusion reasons</dt>
                            <dd>{run.exclusion_reasons.join(", ")}</dd>
                          </>
                        ) : null}
                        {run.notes ? (
                          <>
                            <dt>Notes</dt>
                            <dd>{run.notes}</dd>
                          </>
                        ) : null}
                      </dl>
                    </details>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!rows.length && (
          <div className="empty-state">
            <Search size={28} />
            <h2>No matching records.</h2>
            <p>Clear a filter or search another task or model.</p>
            <button className="button button-outline" onClick={reset}>
              Clear filters
            </button>
          </div>
        )}
        <div className="pagination">
          <span role="status">
            {filtered.length
              ? `${(currentPage - 1) * 10 + 1}–${Math.min(currentPage * 10, filtered.length)}`
              : "0"}{" "}
            of {filtered.length} records
          </span>
          <div>
            <button
              className="icon-button"
              aria-label="Previous page"
              disabled={currentPage === 1}
              onClick={() => setPage(currentPage - 1)}
            >
              <ChevronLeft size={18} />
            </button>
            <span>
              {currentPage} / {pages}
            </span>
            <button
              className="icon-button"
              aria-label="Next page"
              disabled={currentPage === pages}
              onClick={() => setPage(currentPage + 1)}
            >
              <ChevronRight size={18} />
            </button>
          </div>
        </div>
      </section>
      <p className="panel-note">
        Snapshot build: <code>{data.build_identity || "Unavailable"}</code>.
        Verified evidence and comparison eligibility are separate checks.
        Missing costs display as a dash.
      </p>
      <span className="sr-only" role="status">
        {exported
          ? `Exported ${filtered.length} evidence records as JSON.`
          : ""}
      </span>
    </>
  );
}
