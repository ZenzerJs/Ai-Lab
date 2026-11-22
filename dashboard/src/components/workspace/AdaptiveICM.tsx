import { ArrowRight, Layers3 } from "lucide-react";
import { formatArm, formatCurrency, formatSignedPercent } from "../../lib/formatters";
import { matchedArmComparison } from "../../lib/analytics";
import { armNames, finite } from "../../lib/workspace";
import { DashboardPayload } from "../../types";

/** Routing guidance, deliberately separate from the recorded benchmark results. */
export default function AdaptiveICM({ data }: { data?: DashboardPayload }) {
  const liteMatched = data?.tasks
    ? matchedArmComparison(data.tasks, "icm_lite", "baseline", "all")
    : null;
  const armTotals = new Map<string, { runs: number; cost: number; n: number }>();
  for (const task of data?.tasks || []) {
    for (const name of armNames(task)) {
      const arm = task.arms[name];
      const cur = armTotals.get(name) || { runs: 0, cost: 0, n: 0 };
      cur.runs +=
        arm?.scheduled_count ??
        arm?.evaluated_count ??
        arm?.n ??
        arm?.runs?.length ??
        0;
      if (finite(arm?.mean_cost_usd) && finite(arm?.cost_complete_n)) {
        cur.cost += arm.mean_cost_usd * arm.cost_complete_n;
        cur.n += arm.cost_complete_n;
      } else if (finite(arm?.mean_cost_usd)) {
        cur.cost += arm.mean_cost_usd * (arm?.n ?? 0);
        cur.n += arm?.n ?? 0;
      }
      armTotals.set(name, cur);
    }
  }
  const order = ["baseline", "icm", "icm_lite"];
  const names = Array.from(armTotals.keys()).sort(
    (a, b) => (order.indexOf(a) === -1 ? 9 : order.indexOf(a)) -
      (order.indexOf(b) === -1 ? 9 : order.indexOf(b)) ||
      a.localeCompare(b),
  );
  return (
    <section className="adaptive-icm panel" aria-label="Adaptive ICM routing guidance">
      <div className="adaptive-heading">
        <div>
          <span className="eyebrow"><Layers3 size={14} /> ADAPTIVE ICM</span>
          <h2>The right amount of structure.</h2>
        </div>
        <span className="badge badge-purple">~150 LOC / 2+ file break-even</span>
      </div>
      <div className="adaptive-regimes">
        <div>
          <span className="badge badge-purple">{formatArm("icm_lite")}</span>
          <h3>Micro-tasks</h3>
          <p>&lt;150 LOC <strong>and</strong> exactly 1 target file.</p>
          <span className="adaptive-detail">One compact contract. Less fixed governance overhead.</span>
        </div>
        <ArrowRight className="adaptive-arrow" size={22} aria-hidden="true" />
        <div>
          <span className="badge badge-purple">{formatArm("icm")}</span>
          <h3>Larger or multi-file work</h3>
          <p>≥150 LOC <strong>or</strong> 2+ target files.</p>
          <span className="adaptive-detail">Full five-stage governance. Unknown scope defaults here, too.</span>
        </div>
      </div>
      <p className="adaptive-note">
        <span className="badge badge-neutral">{formatArm("baseline")}</span>
        Unconstrained comparison arm. These are deterministic auto-routing rules informed by
        the empirical break-even range, not a guarantee of savings.
      </p>
      {names.length > 0 && (
        <div className="adaptive-measured" aria-label="Measured arm totals">
          {names.map((name) => {
            const t = armTotals.get(name)!;
            return (
              <span key={name} className="adaptive-arm-chip">
                <span className={`badge ${name === "baseline" ? "badge-neutral" : "badge-purple"}`}>
                  {formatArm(name)}
                </span>
                {" "}{t.runs} runs ·{" "}
                {t.n ? formatCurrency(t.cost / t.n) : "—"} / run
              </span>
            );
          })}
          {liteMatched && liteMatched.sharedTaskIds.length > 0 && (
            <span className="adaptive-arm-chip">
              <span className="badge badge-blue">Matched {formatArm("icm_lite")} vs {formatArm("baseline")}</span>
              {" "}{liteMatched.sharedTaskIds.length} shared tasks
              {liteMatched.tokenStats?.meanDeltaPct != null
                ? ` · ${formatSignedPercent(liteMatched.tokenStats.meanDeltaPct)} tokens (n=${liteMatched.tokenStats.n})`
                : ""}
            </span>
          )}
        </div>
      )}
    </section>
  );
}
