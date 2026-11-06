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
import { DashboardPayload, HeadlineStat } from "../../types";
import { formatCurrency } from "../../lib/formatters";
import { experimentNames, finite, governedArm } from "../../lib/workspace";

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
  const isQuality = stat.id === "defect_rate";
  const Icon = isCost ? TrendingDown : isQuality ? ShieldCheck : Cpu;
  const label = isCost
    ? "Cost reduction"
    : isQuality
      ? "Governed defect rate"
      : "Governed cache hit rate";
  return (
    <article className="metric-card">
      <div className="metric-top">
        <span>{label}</span>
        <Icon size={19} />
      </div>
      <div
        className={`metric-value ${isCost && finite(stat.value) && stat.value < 0 ? "text-rust" : ""}`}
      >
        {finite(stat.value) ? `${stat.value.toFixed(1)}%` : stat.value}
        <span className="metric-tag">{isQuality ? "Quality" : "Recorded"}</span>
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
        {stat.source} · {stat.n_tasks} tasks
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
  const measured =
    !data.is_demo_report &&
    !data.is_simulation &&
    Boolean(data.cumulative?.has_measured_data);
  const tasks = data.tasks || [];
  const maxCost = Math.max(
    0.001,
    ...tasks
      .flatMap((task) => [
        task.arms.baseline?.mean_cost_usd,
        governedArm(task)?.mean_cost_usd,
      ])
      .filter(finite),
  );
  const stats = measured ? data.headline?.stats || [] : [];
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
      <div className="section-heading results-heading">
        <h2>What the evidence says</h2>
        <span>
          {tasks.length} experiments <span className="middle-dot">·</span>{" "}
          {data.cumulative?.total_runs ?? 0} comparison runs
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
              <span>
                <i className="legend-governed" />
                Governed
              </span>
            </div>
          </div>
          <div
            className="cost-chart"
            role="group"
            aria-label="Cost comparison in US dollars. Values for baseline and governed runs are labeled on each row."
          >
            {tasks.map((task) => {
              const baseline = task.arms.baseline?.mean_cost_usd,
                governed = governedArm(task)?.mean_cost_usd;
              return (
                <div className="chart-row" key={task.task_id}>
                  <a href="#tasks" className="chart-label">
                    {task.task_id}
                    <span>{experimentNames[task.task_id] || "Experiment"}</span>
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
                    <div className="bar-line">
                      <span
                        className="bar bar-governed"
                        style={{
                          width: finite(governed)
                            ? `${Math.max(1, (governed / maxCost) * 100)}%`
                            : "0%",
                        }}
                      />
                      <span className="bar-value">
                        <span className="sr-only">Governed </span>
                        {formatCurrency(governed)}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
            {!tasks.length && (
              <p className="empty-inline">
                No experiment comparisons available.
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
