import React from 'react';
import { HeadlineBlock } from '../types';
import { Sparkles, TrendingDown, Cpu, Zap, ShieldCheck } from 'lucide-react';
import { Badge } from './ui/badge';

interface HeroStatsProps {
  headline?: HeadlineBlock | null;
  totalRuns: number;
}

export const HeroStats: React.FC<HeroStatsProps> = ({ headline, totalRuns }) => {
  if (!headline || !headline.stats || headline.stats.length === 0) {
    return (
      <div className="glass-panel rounded-2xl p-6 flex flex-col md:flex-row items-center justify-between gap-4 border border-white/10 shadow-2xl">
        <div className="flex items-center gap-3.5">
          <div className="size-11 rounded-xl bg-gradient-to-br from-indigo-500/20 to-purple-500/10 border border-indigo-500/30 flex items-center justify-center shrink-0 shadow-inner">
            <Sparkles className="size-5 text-indigo-400" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-white font-mono tracking-tight">
              Live Benchmark Telemetry Active
            </h3>
            <p className="text-xs text-gray-400 font-mono mt-0.5">
              Empirical A/B trials are evaluating governance efficiency against live CLI event streams.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-xs font-mono border-indigo-500/40 text-indigo-300 bg-indigo-500/10 px-3 py-1">
            {totalRuns} Verified Runs
          </Badge>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-5">
      {headline.sentence && (
        <div className="relative overflow-hidden rounded-2xl border border-indigo-500/30 bg-gradient-to-r from-indigo-950/40 via-purple-950/20 to-background/60 p-4.5 backdrop-blur-md shadow-lg">
          <div className="absolute top-0 right-0 w-96 h-full bg-gradient-to-l from-indigo-500/10 to-transparent pointer-events-none" />
          <div className="relative flex items-center gap-3.5">
            <div className="size-9 rounded-lg bg-indigo-500/20 border border-indigo-400/30 flex items-center justify-center shrink-0">
              <Zap className="size-4.5 text-indigo-300" />
            </div>
            <p className="text-sm font-medium text-white tracking-wide leading-relaxed font-sans">
              {headline.sentence}
            </p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4.5">
        {headline.stats.map((stat) => {
          const isCost = stat.id === 'cost_reduction';
          const isQuality = stat.id === 'defect_rate';

          const accentGradient = isCost
            ? 'from-emerald-500/15 via-emerald-950/5 to-transparent border-emerald-500/30 hover:border-emerald-500/60 glow-emerald'
            : isQuality
            ? 'from-sky-500/15 via-sky-950/5 to-transparent border-sky-500/30 hover:border-sky-500/60'
            : 'from-purple-500/15 via-purple-950/5 to-transparent border-purple-500/30 hover:border-purple-500/60 glow-indigo';

          const valueColor = isCost
            ? 'text-emerald-400'
            : isQuality
            ? 'text-sky-400'
            : 'text-purple-300';

          const IconComponent = isCost ? TrendingDown : isQuality ? ShieldCheck : Cpu;

          return (
            <div
              key={stat.id}
              className={`relative overflow-hidden rounded-2xl border bg-gradient-to-b bg-[#0e1422] p-5 flex flex-col justify-between gap-4 transition-all duration-300 hover:translate-y-[-2px] ${accentGradient}`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded-md bg-white/5 border border-white/10">
                    <IconComponent className="size-3.5 text-gray-300" />
                  </div>
                  <span className="text-xs font-mono font-semibold uppercase tracking-wider text-gray-300">
                    {stat.label}
                  </span>
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-black/40 border border-white/10 text-gray-400 font-mono">
                  {stat.source}
                </span>
              </div>

              <div className="flex items-baseline gap-2.5 my-1">
                <span className={`text-3xl lg:text-4xl font-black font-mono tracking-tight ${valueColor}`}>
                  {typeof stat.value === 'number' ? (
                    `${(stat.value as number) > 0 ? '+' : ''}${stat.value}%`
                  ) : (
                    stat.value
                  )}
                </span>
                {stat.ci95 && (
                  <span className="text-[11px] text-gray-400 font-mono bg-white/5 px-2 py-0.5 rounded border border-white/10">
                    95% CI [{stat.ci95[0]}%, {stat.ci95[1]}%]
                  </span>
                )}
              </div>

              <div className="pt-3 border-t border-white/10 flex items-center justify-between text-xs font-mono">
                <div className="flex flex-col">
                  <span className="text-[10px] uppercase text-gray-500 font-semibold">Unconstrained Baseline</span>
                  <span className="text-gray-300 font-medium mt-0.5">{stat.baseline}</span>
                </div>
                <div className="flex flex-col text-right">
                  <span className="text-[10px] uppercase text-indigo-400 font-semibold">ICM Governed Arm</span>
                  <span className="text-white font-bold mt-0.5">{stat.icm}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
