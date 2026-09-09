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
        <div className="bg-surface-hover border border-surface-border p-3 rounded-lg shadow-xl text-xs space-y-1.5 font-sans">
          <div className="font-semibold text-white border-b border-surface-border pb-1 flex justify-between gap-4">
            <span>{p.label}</span>
            <span className="text-gray-400 font-mono text-[10px]">Step #{p.step}</span>
          </div>
          <div className="flex justify-between gap-4 text-gray-300">
            <span>Delta Saved:</span>
            <span className="font-mono text-emerald-400">+${p.delta_saved_usd.toFixed(4)}</span>
          </div>
          <div className="flex justify-between gap-4 text-white font-medium pt-1 border-t border-surface-border">
            <span>Cumulative Saved:</span>
            <span className="font-mono text-emerald-300">${p.cumulative_savings_usd.toFixed(4)}</span>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="bg-surface border border-surface-border rounded-xl p-5 shadow-sm">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-4 border-b border-surface-border gap-2">
        <div>
          <div className="flex items-center gap-2">
            <Award className="w-4 h-4 text-emerald-400" />
            <h2 className="text-base font-semibold text-white">Cumulative Savings</h2>
            <span className="text-[11px] font-mono font-medium px-2 py-0.5 rounded bg-surface-border text-gray-300">
              Total n={totalRuns} runs
            </span>
          </div>
          <p className="text-xs text-gray-400 mt-0.5">
            {scaleLabel} — comparing baseline vs. ICM pipeline expenditure.
          </p>
        </div>

        <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-mono border ${
          scaleMode === '1x'
            ? 'bg-amber-500/10 border-amber-500/30 text-amber-300'
            : 'bg-primary/15 border-primary/40 text-primary-light'
        }`}>
          {scaleMode === '1x' ? <ShieldAlert className="w-3.5 h-3.5" /> : <Layers className="w-3.5 h-3.5" />}
          <span>{badgeText}</span>
        </div>
      </div>

      {/* Metric Cards Banner */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
        <div className="bg-background/60 border border-surface-border rounded-lg p-3">
          <span className="text-[11px] uppercase tracking-wide text-gray-400 font-medium">Net USD Saved</span>
          <div className="text-xl font-bold text-emerald-400 font-mono mt-1">
            ${totalSaved >= 1 ? totalSaved.toFixed(2) : totalSaved.toFixed(4)}
          </div>
          <span className="text-[10px] text-emerald-400/80 font-mono">
            {pctSaved.toFixed(1)}% Cost Reduction
          </span>
        </div>

        <div className="bg-background/60 border border-surface-border rounded-lg p-3">
          <span className="text-[11px] uppercase tracking-wide text-gray-400 font-medium">Baseline Cost</span>
          <div className="text-xl font-bold text-red-400 font-mono mt-1">
            ${baselineCost >= 1 ? baselineCost.toFixed(2) : baselineCost.toFixed(4)}
          </div>
          <span className="text-[10px] text-gray-400">Total expenditure</span>
        </div>

        <div className="bg-background/60 border border-surface-border rounded-lg p-3">
          <span className="text-[11px] uppercase tracking-wide text-gray-400 font-medium">ICM Pipeline Cost</span>
          <div className="text-xl font-bold text-blue-400 font-mono mt-1">
            ${icmCost >= 1 ? icmCost.toFixed(2) : icmCost.toFixed(4)}
          </div>
          <span className="text-[10px] text-gray-400">Total expenditure</span>
        </div>

        <div className="bg-background/60 border border-surface-border rounded-lg p-3">
          <span className="text-[11px] uppercase tracking-wide text-gray-400 font-medium">Calibrated Scope</span>
          <div className="text-xl font-bold text-gray-200 font-mono mt-1">
            n={totalRuns}
          </div>
          <span className="text-[10px] text-gray-400">
            Across {cumulative.tasks_evaluated} Benchmark Tasks
          </span>
        </div>
      </div>

      {/* Running Cumulative Line Chart */}
      {timeline.length === 0 ? (
        <div className="bg-background/40 border border-surface-border/80 rounded-lg p-8 text-center mt-5">
          <ShieldAlert className="w-8 h-8 text-gray-500 mx-auto mb-2" />
          <p className="text-gray-400 text-sm">No cumulative savings timeline recorded yet.</p>
          <p className="text-gray-500 text-xs mt-1 font-mono">Execute an A/B benchmark run to visualize the savings curve.</p>
        </div>
      ) : (
        <div className="h-60 w-full mt-5">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={scaledTimeline}
              margin={{ top: 10, right: 25, left: 10, bottom: 5 }}
            >
              <defs>
                <linearGradient id="savingsGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#2ea043" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#2ea043" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#21262d" vertical={false} />
              <XAxis
                dataKey="label"
                stroke="#8b949e"
                fontSize={11}
                tickLine={false}
                axisLine={{ stroke: '#30363d' }}
              />
              <YAxis
                stroke="#8b949e"
                fontSize={11}
                tickLine={false}
                axisLine={{ stroke: '#30363d' }}
                tickFormatter={(v) => `$${v >= 1 ? v.toFixed(2) : v.toFixed(3)}`}
              />
              <Tooltip content={<CustomLineTooltip />} />
              <Area
                type="monotone"
                dataKey="cumulative_savings_usd"
                stroke="#3fb950"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#savingsGradient)"
                dot={{ r: 4, fill: '#2ea043', stroke: '#7ee787' }}
                activeDot={{ r: 6, fill: '#56d364', stroke: '#ffffff' }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
};
