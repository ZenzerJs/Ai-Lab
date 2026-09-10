import React from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import { CumulativeSummary, TimelinePoint } from '../types';
import { ScaleMode } from './ScaleSelector';
import { ShieldAlert, Award, Layers } from 'lucide-react';
import { RollingCounter } from './RollingCounter';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { Empty, EmptyIcon, EmptyTitle, EmptyDescription } from './ui/empty';
import { formatCurrency, formatSignedCurrency } from '../lib/formatters';

interface CumulativeSavingsProps {
  cumulative: CumulativeSummary;
  timeline: TimelinePoint[];
  scaleMode: ScaleMode;
}

export const CumulativeSavings: React.FC<CumulativeSavingsProps> = ({
  cumulative,
  timeline,
  scaleMode,
}) => {
  const pctSaved = cumulative.cumulative_savings_percent || 0;
  const totalRuns = cumulative.total_runs || 0;

  // Scale calculations
  let scaleMultiplier = 1.0;
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
    if (cumulative.cumulative_savings_usd > 0 && cumulative.savings_usd_per_mtok) {
      scaleMultiplier = cumulative.savings_usd_per_mtok / cumulative.cumulative_savings_usd;
    }
  } else if (scaleMode === '10m') {
    scaleLabel = 'Projected at 10M Tokens (Engineering Team Volume)';
    badgeText = 'Projected @ 10M Tokens';
    totalSaved = (cumulative.savings_usd_per_mtok ?? 0) * 10;
    baselineCost = (cumulative.cost_per_mtok_baseline ?? 0) * 10;
    icmCost = (cumulative.cost_per_mtok_icm ?? 0) * 10;
    if (cumulative.cumulative_savings_usd > 0 && cumulative.savings_usd_per_mtok) {
      scaleMultiplier = (cumulative.savings_usd_per_mtok * 10) / cumulative.cumulative_savings_usd;
    }
  } else if (scaleMode === '100m') {
    scaleLabel = 'Projected at 100M Tokens (Enterprise Monthly Volume)';
    badgeText = 'Projected @ 100M Tokens';
    totalSaved = (cumulative.savings_usd_per_mtok ?? 0) * 100;
    baselineCost = (cumulative.cost_per_mtok_baseline ?? 0) * 100;
    icmCost = (cumulative.cost_per_mtok_icm ?? 0) * 100;
    if (cumulative.cumulative_savings_usd > 0 && cumulative.savings_usd_per_mtok) {
      scaleMultiplier = (cumulative.savings_usd_per_mtok * 100) / cumulative.cumulative_savings_usd;
    }
  }

  // Guard against non-finite scale multiplier
  if (!Number.isFinite(scaleMultiplier) || scaleMultiplier <= 0) {
    scaleMultiplier = 1.0;
  }

  // Adjust timeline data for the chosen scale
  const scaledTimeline = timeline.map((p) => ({
    ...p,
    delta_saved_usd: p.delta_saved_usd * scaleMultiplier,
    cumulative_savings_usd: p.cumulative_savings_usd * scaleMultiplier,
  }));

  const CustomLineTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const p = payload[0].payload;
      return (
        <div className="bg-surface border border-surface-border p-3 rounded-lg shadow-xl text-xs flex flex-col gap-1.5 font-sans min-w-[200px]">
          <div className="font-semibold text-white border-b border-surface-border pb-1 flex justify-between gap-4">
            <span>{p.label}</span>
            <span className="text-gray-400 font-mono text-[10px]">Step #{p.step}</span>
          </div>
          <div className="flex justify-between gap-4 text-gray-300">
            <span>Delta Saved:</span>
            <span className={p.delta_saved_usd >= 0 ? "font-mono text-emerald-400" : "font-mono text-red-400"}>
              {formatSignedCurrency(p.delta_saved_usd)}
            </span>
          </div>
          <div className="flex justify-between gap-4 text-white font-medium pt-1 border-t border-surface-border">
            <span>Cumulative Saved:</span>
            <span className="font-mono text-emerald-300">{formatCurrency(p.cumulative_savings_usd)}</span>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <Card>
      <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between pb-4 gap-3">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2 flex-wrap">
            <Award className="size-4 text-emerald-400" />
            <CardTitle>Cumulative Savings</CardTitle>
            <Badge variant="secondary" className="font-normal text-[11px]">
              Total n={totalRuns} runs
            </Badge>
          </div>
          <CardDescription>
            {scaleLabel} — comparing baseline vs. ICM pipeline expenditure.
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
        {/* Metric Cards Banner */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="bg-background/60 border border-surface-border rounded-lg p-3 flex flex-col justify-between">
            <span className="text-[11px] uppercase tracking-wide text-muted-foreground font-medium">Net USD Saved</span>
            <div className="text-xl font-bold text-sage font-mono mt-1">
              <RollingCounter target={totalSaved} decimals={totalSaved >= 1 ? 2 : 4} prefix="$" replayKey={totalSaved} />
            </div>
            <span className="text-[10px] text-sage/80 font-mono">
              {pctSaved >= 0
                ? `${pctSaved.toFixed(1)}% Cost Reduction`
                : `${Math.abs(pctSaved).toFixed(1)}% Cost Increase`}
            </span>
          </div>

          <div className="bg-background/60 border border-surface-border rounded-lg p-3 flex flex-col justify-between">
            <span className="text-[11px] uppercase tracking-wide text-muted-foreground font-medium">Baseline Cost</span>
            <div className="text-xl font-bold text-baseline font-mono mt-1">
              <RollingCounter target={baselineCost} decimals={baselineCost >= 1 ? 2 : 4} prefix="$" replayKey={baselineCost} />
            </div>
            <span className="text-[10px] text-muted-foreground">Total expenditure</span>
          </div>

          <div className="bg-background/60 border border-surface-border rounded-lg p-3 flex flex-col justify-between">
            <span className="text-[11px] uppercase tracking-wide text-muted-foreground font-medium">ICM Pipeline Cost</span>
            <div className="text-xl font-bold text-primary-light font-mono mt-1">
              <RollingCounter target={icmCost} decimals={icmCost >= 1 ? 2 : 4} prefix="$" replayKey={icmCost} />
            </div>
            <span className="text-[10px] text-muted-foreground">Total expenditure</span>
          </div>

          <div className="bg-background/60 border border-surface-border rounded-lg p-3 flex flex-col justify-between">
            <span className="text-[11px] uppercase tracking-wide text-muted-foreground font-medium">Calibrated Scope</span>
            <div className="text-xl font-bold text-foreground font-mono mt-1">
              <RollingCounter target={totalRuns} decimals={0} prefix="n = " suffix=" Runs" replayKey={totalRuns} />
            </div>
            <span className="text-[10px] text-muted-foreground">
              Across {cumulative.tasks_evaluated} Benchmark Tasks
            </span>
          </div>
        </div>

        {/* Running Cumulative Line Chart */}
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
          <div className="min-h-[220px] h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={scaledTimeline}
                margin={{ top: 10, right: 25, left: 10, bottom: 5 }}
              >
                <defs>
                  <linearGradient id="savingsGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10B981" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#10B981" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1D2433" vertical={false} />
                <XAxis
                  dataKey="label"
                  stroke="#75859C"
                  fontSize={11}
                  tickLine={false}
                  axisLine={{ stroke: '#2D3748' }}
                />
                <YAxis
                  stroke="#75859C"
                  fontSize={11}
                  tickLine={false}
                  axisLine={{ stroke: '#2D3748' }}
                  tickFormatter={(v) => formatCurrency(v)}
                />
                <Tooltip content={<CustomLineTooltip />} />
                <Area
                  type="monotone"
                  dataKey="cumulative_savings_usd"
                  stroke="#10B981"
                  strokeWidth={2.5}
                  strokeLinecap="round"
                  fillOpacity={1}
                  fill="url(#savingsGradient)"
                  dot={{ r: 4, fill: '#34D399', stroke: '#0B0D11', strokeWidth: 2 }}
                  activeDot={{ r: 6, fill: '#34D399', stroke: '#F1F5F9' }}
                  className="chart-area-fade"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
