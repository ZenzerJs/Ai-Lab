import { useEffect, useId, useMemo, useState } from "react";
import { GitBranch, Layers, Sparkles, TrendingDown } from "lucide-react";
import { DashboardPayload } from "../../types";
import {
  formatCurrency,
  formatDecimal,
  formatPercent,
  formatSignedPercent,
  formatTokens,
} from "../../lib/formatters";
import {
  computeParetoFrontier,
  LineageModelCohort,
  LineagePoint,
  lineageEdges,
  resolveLineageModels,
} from "../../lib/lineage";
import { finite } from "../../lib/workspace";

type CostAxisMode = "cost_per_run" | "cost_per_pass";

function pickDefaultModel(cohorts: LineageModelCohort[]): string {
  if (!cohorts.length) return "";
  const priced = cohorts.filter((c) => c.hasPricing);
  if (!priced.length) return cohorts[0].model;
  const maxVersions = Math.max(...priced.map((c) => c.points.length));
  const flash = priced.find(
    (c) => c.model === "gemini-3.8-flash-low" && c.points.length === maxVersions,
  );
  return flash ? flash.model : priced[0].model;
}

function niceTicks(minVal: number, maxVal: number, count = 4): number[] {
  const lo = Math.max(0, minVal);
  const hi = maxVal > lo ? maxVal : lo + 1;
  const step = (hi - lo) / (count - 1);
  return Array.from({ length: count }, (_, idx) => lo + idx * step);
}

function formatAxisX(val: number, hasPricing: boolean): string {
  if (!hasPricing) return val >= 10 ? Math.round(val).toString() : val.toFixed(1);
  if (val >= 1) return `$${val.toFixed(2)}`;
  if (val >= 0.05) return `$${val.toFixed(3)}`;
  return `$${val.toFixed(4)}`;
}

export default function IterationLineage({ data }: { data: DashboardPayload }) {
  const uid = useId().replace(/[^a-zA-Z0-9_-]/g, "");
  const cohorts = useMemo(() => resolveLineageModels(data), [data]);
  const [selectedModel, setSelectedModel] = useState<string>(() =>
    pickDefaultModel(cohorts),
  );
  const [costAxis, setCostAxis] = useState<CostAxisMode>("cost_per_run");
  const [lockedVersion, setLockedVersion] = useState<string | null>(null);
  const [hoveredVersion, setHoveredVersion] = useState<string | null>(null);

  useEffect(() => {
    if (!cohorts.length) return;
    if (!cohorts.some((c) => c.model === selectedModel)) {
      setSelectedModel(pickDefaultModel(cohorts));
    }
  }, [cohorts, selectedModel]);

  const activeCohort = useMemo(
    () => cohorts.find((c) => c.model === selectedModel) || cohorts[0] || null,
    [cohorts, selectedModel],
  );

  useEffect(() => {
    setLockedVersion(null);
    setHoveredVersion(null);
  }, [activeCohort?.model]);

  if (!activeCohort || !activeCohort.points.length) {
    return (
      <section
        className="panel empty-state lineage-empty"
        aria-label="Iteration lineage and Pareto frontier"
      >
        <GitBranch size={28} />
        <h2>Iteration lineage starts with verified runs.</h2>
        <p>
          No live verified model cohorts are present in this snapshot to plot
          harness versions against the Pareto frontier.
        </p>
      </section>
    );
  }

  const hasPricing = activeCohort.hasPricing;
  const xAccessor = (p: LineagePoint): number | null => {
    if (!hasPricing) return p.mean_tools;
    return costAxis === "cost_per_pass"
      ? p.cost_per_passing_patch_usd
      : p.mean_cost_usd;
  };
  const xAxisLabel = !hasPricing
    ? "Avg Tool Calls (no USD rate)"
    : costAxis === "cost_per_pass"
      ? "Cost / Verified Pass (USD)"
      : "Cost / Run (USD)";

  const paretoSet = computeParetoFrontier(activeCohort.points, xAccessor);
  const edges = lineageEdges(activeCohort.points);
  const baselinePoint = activeCohort.points.find((p) => p.version === "baseline");

  const plottedPoints = activeCohort.points.filter(
    (p) => finite(xAccessor(p)) && finite(p.pass_rate),
  );
  const omittedZeroPassPoints =
    hasPricing && costAxis === "cost_per_pass"
      ? activeCohort.points.filter(
          (p) => p.cost_per_passing_patch_usd === null && finite(p.pass_rate),
        )
      : [];

  const defaultFocusVersion =
    activeCohort.points.find(
      (p) => p.version !== "baseline" && paretoSet.has(p.version),
    )?.version ||
    activeCohort.points[activeCohort.points.length - 1]?.version ||
    null;

  const inspectedVersion = hoveredVersion || lockedVersion || defaultFocusVersion;
  const inspectedPoint =
    activeCohort.points.find((p) => p.version === inspectedVersion) ||
    activeCohort.points[0];

  // SVG plot geometry
  const W = 560;
  const H = 310;
  const PAD = { top: 34, right: 28, bottom: 48, left: 56 };
  const plotW = W - PAD.left - PAD.right;
  const plotH = H - PAD.top - PAD.bottom;

  const rawXs = plottedPoints.map((p) => xAccessor(p) as number);
  const rawMinX = rawXs.length ? Math.min(...rawXs) : 0;
  const rawMaxX = rawXs.length ? Math.max(...rawXs) : 1;
  const xSpan = Math.max(rawMaxX - rawMinX, rawMaxX * 0.25, hasPricing ? 0.01 : 1);
  const xMin = Math.max(0, rawMinX - xSpan * 0.14);
  const xMax = rawMaxX + xSpan * 0.14;

  const rawYs = plottedPoints.map((p) => (p.pass_rate as number) * 100);
  const yMin = rawYs.length ? Math.max(0, Math.floor(Math.min(...rawYs) / 10) * 10 - 10) : 0;
  const yMax = 100;

  const scaleX = (val: number) =>
    PAD.left + ((val - xMin) / Math.max(1e-9, xMax - xMin)) * plotW;
  const scaleY = (pct: number) =>
    PAD.top + (1 - (pct - yMin) / Math.max(1e-9, yMax - yMin)) * plotH;

  const coordsByVersion = new Map<string, { cx: number; cy: number; point: LineagePoint }>();
  for (const p of plottedPoints) {
    coordsByVersion.set(p.version, {
      cx: scaleX(xAccessor(p) as number),
      cy: scaleY((p.pass_rate as number) * 100),
      point: p,
    });
  }

  const frontierSorted = plottedPoints
    .filter((p) => paretoSet.has(p.version))
    .sort((a, b) => (xAccessor(a) as number) - (xAccessor(b) as number));
  const frontierPathD =
    frontierSorted.length >= 2
      ? frontierSorted
          .map((p, i) => {
            const c = coordsByVersion.get(p.version)!;
            return `${i === 0 ? "M" : "L"}${c.cx.toFixed(1)},${c.cy.toFixed(1)}`;
          })
          .join(" ")
      : "";

  const xTicks = niceTicks(xMin, xMax, 4);
  const yTicks = niceTicks(yMin, yMax, 4);

  // Token-burn vs tool-call bar decomposition
  const hasTokenBars = activeCohort.points.some(
    (p) =>
      (finite(p.mean_input_tokens) && p.mean_input_tokens > 0) ||
      (finite(p.mean_cache_read_tokens) && p.mean_cache_read_tokens > 0) ||
      (finite(p.mean_output_tokens) && p.mean_output_tokens > 0),
  );
  const maxBarTotal = Math.max(
    1,
    ...activeCohort.points.map((p) =>
      hasTokenBars
        ? (p.mean_input_tokens || 0) +
          (p.mean_cache_read_tokens || 0) +
          (p.mean_output_tokens || 0)
        : p.mean_tools || 0,
    ),
  );

  const isRegression = (p: LineagePoint): boolean => {
    if (!baselinePoint || p.version === "baseline") return false;
    const basePass = baselinePoint.pass_rate;
    const pPass = p.pass_rate;
    const passImproved = finite(basePass) && finite(pPass) ? pPass > basePass + 1e-6 : false;
    if (hasPricing) {
      const bx = xAccessor(baselinePoint);
      const px = xAccessor(p);
      if (finite(bx) && finite(px)) return px > bx && !passImproved;
      return finite(p.cost_delta_vs_baseline_pct) && p.cost_delta_vs_baseline_pct > 0 && !passImproved;
    }
    return (
      finite(baselinePoint.mean_tools) &&
      finite(p.mean_tools) &&
      p.mean_tools > baselinePoint.mean_tools &&
      !passImproved
    );
  };

  const animKey = `${activeCohort.model}-${hasPricing ? costAxis : "tools"}`;

  return (
    <section
      className="panel lineage-panel"
      aria-labelledby="lineage-section-title"
    >
      <div className="panel-heading lineage-header">
        <div>
          <span className="eyebrow">
            <GitBranch size={13} /> ITERATION LINEAGE &amp; PARETO FRONTIER
          </span>
          <h2 id="lineage-section-title">
            Harness evolution across {hasPricing ? "spend" : "tool calls"} &amp; pass rate
          </h2>
          <p className="lineage-caption">
            <span className="mono">{activeCohort.model}</span>
            {" · "}
            {activeCohort.totalRuns} live runs · {activeCohort.taskCount} tasks ·{" "}
            {xAxisLabel}
          </p>
        </div>

        <div className="lineage-controls">
          {hasPricing ? (
            <div
              className="segmented-control"
              role="group"
              aria-label="Pareto X-axis cost metric"
            >
              <button
                type="button"
                aria-pressed={costAxis === "cost_per_run"}
                onClick={() => setCostAxis("cost_per_run")}
              >
                Cost / Run (USD)
              </button>
              <button
                type="button"
                aria-pressed={costAxis === "cost_per_pass"}
                onClick={() => setCostAxis("cost_per_pass")}
              >
                Cost / Verified Pass (USD)
              </button>
            </div>
          ) : (
            <span className="badge badge-amber">
              Avg Tool Calls (no USD rate)
            </span>
          )}
        </div>
      </div>

      <div
        className="lineage-model-pills"
        role="group"
        aria-label="Select model cohort"
      >
        {cohorts.map((c) => {
          const active = c.model === activeCohort.model;
          return (
            <button
              key={c.model}
              type="button"
              className={`lineage-pill ${active ? "is-active" : ""}`}
              aria-pressed={active}
              onClick={() => setSelectedModel(c.model)}
            >
              <span className="mono">{c.model}</span>
              <span
                className={`lineage-pill-meta ${c.hasPricing ? "is-priced" : "is-unpriced"}`}
              >
                {c.hasPricing ? "USD" : "Tools"} · {c.points.length}v
              </span>
            </button>
          );
        })}
      </div>

      <div className="lineage-visual-grid">
        <div className="lineage-plot-card">
          <div className="lineage-plot-head">
            <span className="lineage-optimal-hint">
              <Sparkles size={13} />
              {hasPricing
                ? "Optimal: lower cost · higher pass rate"
                : "Optimal: fewer tool calls · higher pass rate"}
            </span>
            <div className="lineage-legend">
              <span>
                <i className="dot-pareto" /> Pareto frontier
              </span>
              <span>
                <i className="dot-governed" /> Trajectory
              </span>
              <span>
                <i className="dot-regression" /> Regression
              </span>
            </div>
          </div>

          <div className="lineage-svg-wrap" key={animKey}>
            <svg
              viewBox={`0 0 ${W} ${H}`}
              role="img"
              aria-label={`Pareto frontier plot for ${activeCohort.model}: ${xAxisLabel} versus pass rate across ${activeCohort.points.length} harness versions`}
              className="lineage-svg"
            >
              <defs>
                <marker
                  id={`arrow-iris-${uid}`}
                  viewBox="0 0 10 10"
                  refX="8"
                  refY="5"
                  markerWidth="6"
                  markerHeight="6"
                  orient="auto-start-reverse"
                >
                  <path d="M 1 2 L 8 5 L 1 8 z" fill="var(--iris)" />
                </marker>
                <marker
                  id={`arrow-branch-${uid}`}
                  viewBox="0 0 10 10"
                  refX="8"
                  refY="5"
                  markerWidth="5"
                  markerHeight="5"
                  orient="auto-start-reverse"
                >
                  <path d="M 1 2 L 8 5 L 1 8 z" fill="var(--muted)" />
                </marker>
                <linearGradient id={`optimal-zone-${uid}`} x1="0" y1="0" x2="1" y2="1">
                  <stop offset="0%" stopColor="var(--sea)" stopOpacity="0.14" />
                  <stop offset="100%" stopColor="var(--sea)" stopOpacity="0" />
                </linearGradient>
              </defs>

              {/* Hairline grid */}
              {yTicks.map((yt) => {
                const y = scaleY(yt);
                return (
                  <g key={`y-${yt}`}>
                    <line
                      x1={PAD.left}
                      y1={y}
                      x2={W - PAD.right}
                      y2={y}
                      stroke="var(--line)"
                      strokeWidth="1"
                    />
                    <text
                      x={PAD.left - 8}
                      y={y + 4}
                      textAnchor="end"
                      fill="var(--muted)"
                      fontSize="10.5"
                      fontFamily="var(--mono)"
                    >
                      {Math.round(yt)}%
                    </text>
                  </g>
                );
              })}
              {xTicks.map((xt, idx) => {
                const x = scaleX(xt);
                return (
                  <g key={`x-${idx}`}>
                    <line
                      x1={x}
                      y1={PAD.top}
                      x2={x}
                      y2={H - PAD.bottom}
                      stroke="var(--line)"
                      strokeWidth="1"
                    />
                    <text
                      x={x}
                      y={H - PAD.bottom + 18}
                      textAnchor="middle"
                      fill="var(--muted)"
                      fontSize="10.5"
                      fontFamily="var(--mono)"
                    >
                      {formatAxisX(xt, hasPricing)}
                    </text>
                  </g>
                );
              })}

              {/* Axis titles */}
              <text
                x={PAD.left + plotW / 2}
                y={H - 8}
                textAnchor="middle"
                fill="var(--muted)"
                fontSize="11"
                fontFamily="var(--body)"
                fontWeight="600"
              >
                {xAxisLabel}
              </text>
              <text
                x={16}
                y={PAD.top + plotH / 2}
                textAnchor="middle"
                fill="var(--muted)"
                fontSize="11"
                fontFamily="var(--body)"
                fontWeight="600"
                transform={`rotate(-90 16 ${PAD.top + plotH / 2})`}
              >
                Pass rate
              </text>

              {/* Subtle optimal quadrant glow + non-overlapping label above plot top */}
              <rect
                x={PAD.left}
                y={PAD.top}
                width={plotW * 0.36}
                height={plotH * 0.36}
                fill={`url(#optimal-zone-${uid})`}
                pointerEvents="none"
              />
              <text
                x={PAD.left + 2}
                y={PAD.top - 12}
                textAnchor="start"
                fill="var(--sea)"
                fontSize="9.5"
                fontFamily="var(--mono)"
                fontWeight="600"
              >
                ★ Optimal corner
              </text>

              {/* Pareto frontier dashed envelope */}
              {frontierPathD && (
                <path
                  d={frontierPathD}
                  fill="none"
                  stroke="var(--sea)"
                  strokeWidth="2"
                  strokeDasharray="6 4"
                  className="pareto-frontier-path"
                />
              )}

              {/* Lineage transition arrows */}
              {edges.map((edge) => {
                const fromC = coordsByVersion.get(edge.from);
                const toC = coordsByVersion.get(edge.to);
                if (!fromC || !toC) return null;
                const dx = toC.cx - fromC.cx;
                const dy = toC.cy - fromC.cy;
                const dist = Math.hypot(dx, dy);
                if (dist < 1) return null;
                const offset = 11;
                const x1 = fromC.cx + (dx / dist) * offset;
                const y1 = fromC.cy + (dy / dist) * offset;
                const x2 = toC.cx - (dx / dist) * offset;
                const y2 = toC.cy - (dy / dist) * offset;
                const isBranch = edge.kind === "branch";
                return (
                  <line
                    key={`${edge.from}->${edge.to}`}
                    x1={x1}
                    y1={y1}
                    x2={x2}
                    y2={y2}
                    stroke={isBranch ? "var(--muted)" : "var(--iris)"}
                    strokeWidth={isBranch ? "1.4" : "1.8"}
                    strokeDasharray={isBranch ? "3 3" : undefined}
                    strokeOpacity={isBranch ? 0.7 : 0.85}
                    markerEnd={`url(#${isBranch ? `arrow-branch-${uid}` : `arrow-iris-${uid}`})`}
                    className="lineage-edge-line"
                  />
                );
              })}

              {/* Interactive nodes */}
              {plottedPoints.map((p, idx) => {
                const coord = coordsByVersion.get(p.version);
                if (!coord) return null;
                const isBase = p.version === "baseline";
                const isPareto = paretoSet.has(p.version);
                const regressed = isRegression(p);
                const active = inspectedPoint?.version === p.version;
                const fill = isBase
                  ? "var(--paper)"
                  : isPareto
                    ? "var(--sea)"
                    : "var(--iris)";
                const stroke = regressed
                  ? "var(--rust)"
                  : isBase
                    ? "var(--muted)"
                    : isPareto
                      ? "var(--sea)"
                      : "var(--iris)";
                const labelAbove = coord.cy > PAD.top + 34;
                return (
                  <g
                    key={p.version}
                    transform={`translate(${coord.cx}, ${coord.cy})`}
                    className={`pareto-node ${active ? "is-active" : ""}`}
                    style={{ ["--node-order" as string]: idx }}
                    tabIndex={0}
                    role="button"
                    aria-pressed={lockedVersion === p.version}
                    aria-label={`${p.label}: ${formatPercent(
                      p.pass_rate != null ? p.pass_rate * 100 : null,
                    )} pass rate, ${
                      hasPricing
                        ? formatCurrency(xAccessor(p))
                        : `${formatDecimal(xAccessor(p))} tools`
                    }${isPareto ? ", Pareto optimal" : ""}`}
                    onMouseEnter={() => setHoveredVersion(p.version)}
                    onMouseLeave={() => setHoveredVersion(null)}
                    onFocus={() => setHoveredVersion(p.version)}
                    onBlur={() => setHoveredVersion(null)}
                    onClick={() =>
                      setLockedVersion((cur) =>
                        cur === p.version ? null : p.version,
                      )
                    }
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        setLockedVersion((cur) =>
                          cur === p.version ? null : p.version,
                        );
                      }
                    }}
                  >
                    <g className="pareto-node-inner">
                      {isPareto && (
                        <circle
                          r={active ? 14 : 11}
                          fill="none"
                          stroke="var(--sea)"
                          strokeWidth="1.5"
                          strokeOpacity="0.45"
                        />
                      )}
                      {active && (
                        <circle
                          r="16"
                          fill="none"
                          stroke="var(--iris)"
                          strokeWidth="1.5"
                          strokeOpacity="0.4"
                        />
                      )}
                      <circle
                        r={active ? 8 : 6.5}
                        fill={fill}
                        stroke={stroke}
                        strokeWidth={regressed || isBase ? 2.5 : 2}
                      />
                      <text
                        y={labelAbove ? -14 : 22}
                        textAnchor="middle"
                        fill="var(--ink)"
                        fontSize="10.5"
                        fontFamily="var(--mono)"
                        fontWeight={active || isPareto ? "600" : "500"}
                      >
                        {p.label}
                      </text>
                    </g>
                  </g>
                );
              })}
            </svg>
          </div>

          {omittedZeroPassPoints.length > 0 && (
            <p className="lineage-omitted-note">
              Omitted from Cost / Verified Pass axis (0 verified passes, REP-06):{" "}
              {omittedZeroPassPoints.map((p) => p.label).join(", ")}
            </p>
          )}

          {inspectedPoint && (
            <div
              className="lineage-readout"
              aria-live="polite"
              aria-label="Selected harness version details"
            >
              <div className="lineage-readout-title">
                <strong>{inspectedPoint.label}</strong>
                <div className="lineage-readout-badges">
                  {paretoSet.has(inspectedPoint.version) && (
                    <span className="badge badge-green">Pareto optimal</span>
                  )}
                  {inspectedPoint.version === "baseline" && (
                    <span className="badge badge-neutral">Anchor</span>
                  )}
                  {isRegression(inspectedPoint) && (
                    <span className="badge badge-amber">Higher cost</span>
                  )}
                </div>
              </div>
              <dl className="lineage-readout-grid">
                <div>
                  <dt>Pass rate</dt>
                  <dd className="mono">
                    {formatPercent(
                      inspectedPoint.pass_rate != null
                        ? inspectedPoint.pass_rate * 100
                        : null,
                    )}{" "}
                    ({inspectedPoint.passed_count}/{inspectedPoint.n_runs})
                  </dd>
                </div>
                <div>
                  <dt>Cost / run</dt>
                  <dd className="mono">
                    {formatCurrency(inspectedPoint.mean_cost_usd)}
                  </dd>
                </div>
                <div>
                  <dt>$/pass</dt>
                  <dd className="mono">
                    {formatCurrency(inspectedPoint.cost_per_passing_patch_usd)}
                  </dd>
                </div>
                <div>
                  <dt>Delta vs baseline</dt>
                  <dd
                    className={`mono ${
                      finite(inspectedPoint.cost_delta_vs_baseline_pct)
                        ? inspectedPoint.cost_delta_vs_baseline_pct <= 0
                          ? "text-sea"
                          : "text-rust"
                        : ""
                    }`}
                  >
                    {formatSignedPercent(
                      inspectedPoint.cost_delta_vs_baseline_pct,
                    )}
                  </dd>
                </div>
                <div>
                  <dt>Avg tools</dt>
                  <dd className="mono">
                    {formatDecimal(inspectedPoint.mean_tools)}
                  </dd>
                </div>
                <div>
                  <dt>LLM calls</dt>
                  <dd className="mono">
                    {formatDecimal(inspectedPoint.mean_llm_calls)}
                  </dd>
                </div>
                <div>
                  <dt>Cache hit %</dt>
                  <dd className="mono">
                    {inspectedPoint.mean_cache_hit_ratio != null
                      ? formatPercent(
                          inspectedPoint.mean_cache_hit_ratio * 100,
                        )
                      : "—"}
                  </dd>
                </div>
                <div>
                  <dt>Cache busts</dt>
                  <dd className="mono">
                    {inspectedPoint.total_cache_busts != null
                      ? String(inspectedPoint.total_cache_busts)
                      : "—"}
                  </dd>
                </div>
              </dl>
            </div>
          )}
        </div>

        <div className="lineage-bars-card">
          <div className="lineage-plot-head">
            <div>
              <h3>
                {hasTokenBars
                  ? "Mean token composition per run"
                  : "Mean tool calls per run"}
              </h3>
              <p className="lineage-bars-sub">
                {hasTokenBars
                  ? "Fresh input, prompt cache reads, and output tokens"
                  : "Zero-token unpriced Devin cohort — ranked by tool calls"}
              </p>
            </div>
            {hasTokenBars && (
              <div className="lineage-legend">
                <span>
                  <i className="dot-input" /> Fresh input
                </span>
                <span>
                  <i className="dot-cache" /> Cache read
                </span>
                <span>
                  <i className="dot-output" /> Output
                </span>
              </div>
            )}
          </div>

          <div className="lineage-bars-list" key={`${animKey}-bars`}>
            {activeCohort.points.map((p, idx) => {
              const inp = p.mean_input_tokens || 0;
              const cache = p.mean_cache_read_tokens || 0;
              const out = p.mean_output_tokens || 0;
              const total = hasTokenBars
                ? inp + cache + out
                : p.mean_tools || 0;
              const trackPct = Math.min(100, (total / maxBarTotal) * 100);
              const inpShare = total > 0 ? (inp / total) * 100 : 0;
              const cacheShare = total > 0 ? (cache / total) * 100 : 0;
              const outShare = total > 0 ? (out / total) * 100 : 0;
              const isSelected = inspectedPoint?.version === p.version;

              return (
                <button
                  key={p.version}
                  type="button"
                  className={`lineage-bar-row ${isSelected ? "is-active" : ""}`}
                  style={{ ["--bar-order" as string]: idx }}
                  onMouseEnter={() => setHoveredVersion(p.version)}
                  onMouseLeave={() => setHoveredVersion(null)}
                  onClick={() =>
                    setLockedVersion((cur) =>
                      cur === p.version ? null : p.version,
                    )
                  }
                >
                  <div className="lineage-bar-top">
                    <span className="lineage-bar-name">
                      {p.label}
                      {paretoSet.has(p.version) && (
                        <span className="lineage-pareto-chip">Pareto</span>
                      )}
                    </span>
                    <span className="mono lineage-bar-total">
                      {hasTokenBars
                        ? `${formatTokens(total)} tok`
                        : `${formatDecimal(p.mean_tools)} calls`}
                    </span>
                  </div>

                  <div
                    className="lineage-bar-track"
                    style={{ width: `${Math.max(4, trackPct)}%` }}
                  >
                    {hasTokenBars ? (
                      <>
                        {inpShare > 0 && (
                          <span
                            className="seg-input"
                            style={{ width: `${inpShare}%` }}
                          />
                        )}
                        {cacheShare > 0 && (
                          <span
                            className="seg-cache"
                            style={{ width: `${cacheShare}%` }}
                          />
                        )}
                        {outShare > 0 && (
                          <span
                            className="seg-output"
                            style={{ width: `${outShare}%` }}
                          />
                        )}
                      </>
                    ) : (
                      <span
                        className={
                          p.version === "baseline"
                            ? "seg-baseline"
                            : "seg-input"
                        }
                        style={{ width: "100%" }}
                      />
                    )}
                  </div>

                  <div className="lineage-bar-meta mono">
                    <span>LLM {formatDecimal(p.mean_llm_calls)}</span>
                    <span>Tools/call {formatDecimal(p.mean_tools_per_call)}</span>
                    <span>
                      Cache{" "}
                      {p.mean_cache_hit_ratio != null
                        ? formatPercent(p.mean_cache_hit_ratio * 100)
                        : "—"}
                    </span>
                    <span>
                      Busts{" "}
                      {p.total_cache_busts != null
                        ? p.total_cache_busts
                        : "—"}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      <div className="lineage-cards-grid">
        {activeCohort.points.map((p) => {
          const isPareto = paretoSet.has(p.version);
          const active = inspectedPoint?.version === p.version;
          const regressed = isRegression(p);
          return (
            <article
              key={p.version}
              className={`lineage-card ${active ? "is-active" : ""}`}
              onClick={() =>
                setLockedVersion((cur) => (cur === p.version ? null : p.version))
              }
            >
              <div className="lineage-card-head">
                <div>
                  <span
                    className={`badge ${p.version === "baseline" ? "badge-neutral" : "badge-purple"}`}
                  >
                    {p.label}
                  </span>
                  {isPareto && (
                    <span className="badge badge-green">Pareto</span>
                  )}
                  {regressed && (
                    <span className="badge badge-amber">
                      <TrendingDown size={12} /> Regression
                    </span>
                  )}
                </div>
                <span className="mono lineage-card-runs">
                  {p.passed_count}/{p.n_runs} passed
                </span>
              </div>

              {p.hypothesis && (
                <p className="lineage-card-hypothesis">{p.hypothesis}</p>
              )}

              {p.changes_from_prev.length > 0 && (
                <ul className="lineage-card-changes">
                  {p.changes_from_prev.map((change, i) => (
                    <li key={i}>{change}</li>
                  ))}
                </ul>
              )}

              <div className="lineage-card-deltas mono">
                <span>
                  <Layers size={12} />{" "}
                  {hasPricing
                    ? formatCurrency(p.mean_cost_usd)
                    : `${formatDecimal(p.mean_tools)} tools`}
                </span>
                <span>
                  {p.version === "baseline"
                    ? "Baseline anchor"
                    : finite(p.cost_delta_vs_baseline_pct)
                      ? `${formatSignedPercent(p.cost_delta_vs_baseline_pct)} vs base`
                      : p.mean_cache_hit_ratio != null
                        ? `${formatPercent(p.mean_cache_hit_ratio * 100)} cache`
                        : "Unpriced"}
                </span>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
