import React from 'react';
import { CumulativeSummary, TimelinePoint } from '../types';
import { ScaleMode } from './ScaleSelector';
import { ShieldAlert, Award, Layers } from 'lucide-react';
import { RollingCounter } from './RollingCounter';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { Empty, EmptyIcon, EmptyTitle, EmptyDescription } from './ui/empty';

interface CumulativeSavingsProps {
  cumulative: CumulativeSummary;
  timeline: TimelinePoint[];
  scaleMode: ScaleMode;
}

const VIEW_W = 800;
const VIEW_H = 160;
const PAD_X = 40;
const PAD_BOTTOM = 10;
const PAD_TOP = 15;

/** Custom SVG vector curve ported from the code.html prototype (gradient polygon + polyline + dual-ring endpoint). */
export const CumulativeSavings: React.FC<CumulativeSavingsProps> = ({
  cumulative,
  timeline,
  scaleMode,
}) => {
  const pctSaved = cumulative.cumulative_savings_percent || 0;
  const totalRuns = cumulative.total_runs || 0;

  // Scale calculations
  let scaleLabel = 'Raw Single-Run Expenditures';
  let badgeText = 'Strict Actuals • Zero Projections';
  let totalSaved = cumulative.cumulative_savings_usd || 0;
  let baselineCost = cumulative.total_baseline_cost_usd || 0;
  let icmCost = cumulative.total_icm_cost_usd || 0;

  if (scaleMode === '1m') {
    scaleLabel = 'Normalized per 1,000,000 Tokens (1 MTok)';
    badgeText = 'Scaled to 1M Tokens (1 MTok)';
    totalSaved = cumulative.savings_usd_per_mtok ?? totalSaved;
    baselineCost = cumulative.cost_per_mtok_baseline ?? baselineCost;
    icmCost = cumulative.cost_per_mtok_icm ?? icmCost;
  } else if (scaleMode === '10m') {
    scaleLabel = 'Projected at 10M Tokens (Engineering Team Volume)';
    badgeText = 'Projected @ 10M Tokens';
    totalSaved = (cumulative.savings_usd_per_mtok ?? 0) * 10;
    baselineCost = (cumulative.cost_per_mtok_baseline ?? 0) * 10;
    icmCost = (cumulative.cost_per_mtok_icm ?? 0) * 10;
  } else if (scaleMode === '100m') {
    scaleLabel = 'Projected at 100M Tokens (Enterprise Monthly Volume)';
    badgeText = 'Projected @ 100M Tokens';
    totalSaved = (cumulative.savings_usd_per_mtok ?? 0) * 100;
    baselineCost = (cumulative.cost_per_mtok_baseline ?? 0) * 100;
    icmCost = (cumulative.cost_per_mtok_icm ?? 0) * 100;
  }

  // Map timeline to SVG coordinates (monotone rise like prototype)
  const points = timeline.map((p) => Math.max(0, p.cumulative_savings_usd));
  const hasCurve = points.length >= 2;
  const maxY = Math.max(1e-9, ...points);
  const stepX =
    points.length > 1 ? (VIEW_W - PAD_X * 2) / (points.length - 1) : 0;

  const coords = points.map((v, idx) => {
    const x = PAD_X + idx * stepX;
    const y =
      VIEW_H - PAD_BOTTOM - (v / maxY) * (VIEW_H - PAD_BOTTOM - PAD_TOP);
    return { x, y: Number(y.toFixed(1)) };
  });

  const polylinePoints = coords.map((c) => `${c.x},${c.y}`).join(' ');
  const areaPoints =
    coords.length > 0
      ? `${PAD_X},${VIEW_H - PAD_BOTTOM} ${polylinePoints} ${
          coords[coords.length - 1].x
        },${VIEW_H - PAD_BOTTOM}`
      : '';
  const endpoint = coords.length > 0 ? coords[coords.length - 1] : null;

  return (
    <Card>
      <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between pb-4 gap-3">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2 flex-wrap">
            <Award className="size-4 text-sage" />
            <CardTitle>Cumulative Savings (USD)</CardTitle>
            <Badge variant="secondary" className="font-normal text-[11px]">
              Total n={totalRuns} runs
            </Badge>
          </div>
          <CardDescription>
            {scaleLabel} — chronological execution trace across successive runs.
          </CardDescription>
        </div>

        <Badge
          variant={scaleMode === '1x' ? 'warning' : 'default'}
          className="self-start sm:self-auto flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono font-medium"
        >
          {scaleMode === '1x' ? <ShieldAlert className="size-3.5" /> : <Layers className="size-3.5" />}
          <span>{badgeText}</span>
        </Badge>
      </CardHeader>

      <CardContent className="flex flex-col gap-5">
        {/* Hero Metrics Bar (prototype style) */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="p-3 rounded-lg bg-background/60 border border-sage/30 flex flex-col justify-between">
            <span className="text-[11px] font-mono uppercase text-sage font-semibold tracking-wider flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-sage inline-block" /> Net USD Saved
            </span>
            <div className="text-2xl font-bold font-mono tabular-nums text-sage tracking-tight mt-1">
              <RollingCounter target={totalSaved} decimals={totalSaved >= 1 ? 2 : 4} prefix="$" replayKey={totalSaved} />
            </div>
            <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-sage/10 text-sage border border-sage/20 font-mono tabular-nums self-start">
              {pctSaved >= 0
                ? `${pctSaved.toFixed(1)}% Saved`
                : `${Math.abs(pctSaved).toFixed(1)}% Increase`}
            </span>
          </div>

          <div className="p-3 rounded-lg bg-background/60 border border-surface-border flex flex-col justify-between">
            <span className="text-[11px] font-mono uppercase text-baseline font-semibold tracking-wider flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-baseline inline-block" /> Baseline Cost
            </span>
            <div className="text-2xl font-bold font-mono tabular-nums text-baseline tracking-tight mt-1">
              <RollingCounter target={baselineCost} decimals={baselineCost >= 1 ? 2 : 4} prefix="$" replayKey={baselineCost} />
            </div>
            <span className="text-[10px] text-muted-foreground">Unconstrained context</span>
          </div>

          <div className="p-3 rounded-lg bg-background/60 border border-surface-border flex flex-col justify-between">
            <span className="text-[11px] font-mono uppercase text-primary-light font-semibold tracking-wider flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-primary-light inline-block" /> ICM Pipeline Cost
            </span>
            <div className="text-2xl font-bold font-mono tabular-nums text-primary-light tracking-tight mt-1">
              <RollingCounter target={icmCost} decimals={icmCost >= 1 ? 2 : 4} prefix="$" replayKey={icmCost} />
            </div>
            <span className="text-[10px] text-muted-foreground">Byte-stable caching + AST slicing</span>
          </div>

          <div className="p-3 rounded-lg bg-background/60 border border-surface-border flex flex-col justify-between">
            <span className="text-[11px] font-mono uppercase text-muted-foreground font-semibold tracking-wider flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground inline-block" /> Calibrated Scope
            </span>
            <div className="text-2xl font-bold font-mono tabular-nums text-white tracking-tight mt-1">
              <RollingCounter target={totalRuns} decimals={0} prefix="n = " suffix=" Runs" replayKey={totalRuns} />
            </div>
            <span className="text-[10px] text-muted-foreground">
              Across {cumulative.tasks_evaluated} benchmark tasks
            </span>
          </div>
        </div>

        {/* SVG Timeline Chart with clean solid endpoint */}
        {timeline.length === 0 ? (
          <Empty className="rounded-lg border border-surface-border/80 bg-background/40">
            <EmptyIcon>
              <ShieldAlert className="size-6" />
            </EmptyIcon>
            <EmptyTitle>No cumulative savings timeline recorded yet</EmptyTitle>
            <EmptyDescription>
              Execute an A/B benchmark run to generate paired run comparisons and visualize the savings curve.
            </EmptyDescription>
          </Empty>
        ) : (
          <div className="relative w-full min-h-[220px] h-56 bg-background rounded-lg border border-surface-border/70 p-4 flex flex-col justify-between overflow-hidden">
            <div className="absolute inset-0 flex flex-col justify-between pointer-events-none p-4 opacity-15">
              <div className="border-b border-dashed border-slate-500 w-full" />
              <div className="border-b border-dashed border-slate-500 w-full" />
              <div className="border-b border-dashed border-slate-500 w-full" />
              <div className="border-b border-dashed border-slate-500 w-full" />
            </div>

            {hasCurve ? (
              <svg
                className="w-full h-44 overflow-visible"
                viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
                preserveAspectRatio="none"
                role="img"
                aria-label="Cumulative net savings across successive runs"
              >
                <defs>
                  <linearGradient id="areaGradient" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stopColor="#10B981" stopOpacity="0.25" />
                    <stop offset="100%" stopColor="#10B981" stopOpacity="0.0" />
                  </linearGradient>
                </defs>
                <polygon fill="url(#areaGradient)" points={areaPoints} />
                <polyline
                  fill="none"
                  points={polylinePoints}
                  stroke="#10B981"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2.5"
                />
                {coords.slice(0, -1).map((c, idx) => (
                  <circle
                    key={idx}
                    cx={c.x}
                    cy={c.y}
                    r="4"
                    className="fill-sage stroke-background"
                    strokeWidth="2"
                  />
                ))}
                {endpoint && (
                  <g transform={`translate(${endpoint.x}, ${endpoint.y})`}>
                    <circle fill="none" r="7" stroke="#10B981" strokeOpacity="0.4" strokeWidth="1.5" />
                    <circle fill="#34D399" r="4" stroke="#0B0D11" strokeWidth="1.5" />
                  </g>
                )}
              </svg>
            ) : (
              <div className="flex items-center justify-center h-44 text-xs font-mono text-muted-foreground">
                Need ≥ 2 recorded runs to draw the savings curve.
              </div>
            )}

            <div className="flex justify-between text-[11px] font-mono text-muted-foreground pt-2 border-t border-surface-border relative z-10">
              {timeline.map((p, idx) => (
                <span key={idx} className="truncate max-w-[12%]">
                  {p.label}
                </span>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
