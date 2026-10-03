import React from 'react';
import { HeadlineBlock } from '../types';
import { Sparkles } from 'lucide-react';
import { Badge } from './ui/badge';

interface HeroStatsProps {
  headline?: HeadlineBlock | null;
  totalRuns: number;
}

export const HeroStats: React.FC<HeroStatsProps> = ({ headline, totalRuns }) => {
  if (!headline || !headline.stats || headline.stats.length === 0) {
    return (
      <div className="bg-surface border border-surface-border rounded-xl p-6 flex flex-col md:flex-row items-center justify-between gap-4 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="size-10 rounded-lg bg-primary/10 border border-primary/30 flex items-center justify-center shrink-0">
            <Sparkles className="size-5 text-primary" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-white font-mono">
              Live Benchmark Measurement Engine
            </h3>
            <p className="text-xs text-muted-foreground font-mono mt-0.5">
              Empirical trials are actively gathering live telemetry across test arms.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-xs font-mono border-primary/40 text-primary">
            {totalRuns} Runs Executed
          </Badge>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {headline.sentence && (
        <div className="bg-primary/5 border border-primary/20 rounded-xl p-4 flex items-center gap-3 shadow-sm">
          <Sparkles className="size-5 text-primary shrink-0" />
          <p className="text-sm font-medium text-white tracking-wide leading-relaxed">
            {headline.sentence}
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {headline.stats.map((stat) => {

          return (
            <div
              key={stat.id}
              className="bg-surface border border-surface-border rounded-xl p-5 flex flex-col justify-between gap-3 shadow-sm hover:border-surface-border/80 transition-colors"
            >
              <div className="flex items-start justify-between gap-2">
                <span className="text-xs text-muted-foreground font-mono font-medium">
                  {stat.label}
                </span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-background border border-surface-border text-muted-foreground font-mono">
                  {stat.source}
                </span>
              </div>

              <div className="flex items-baseline gap-2">
                <span className="text-2xl lg:text-3xl font-bold font-mono tracking-tight text-white">
                  {typeof stat.value === 'number' ? (
                    `${(stat.value as number) > 0 ? '+' : ''}${stat.value}%`
                  ) : (
                    stat.value
                  )}
                </span>
                {stat.ci95 && (
                  <span className="text-[11px] text-muted-foreground font-mono">
                    95% CI [{stat.ci95[0]}%, {stat.ci95[1]}%]
                  </span>
                )}
              </div>

              <div className="pt-2 border-t border-surface-border flex items-center justify-between text-xs font-mono text-muted-foreground">
                <div className="flex flex-col">
                  <span className="text-[10px] uppercase text-muted-foreground/80">Baseline</span>
                  <span className="text-gray-300 font-medium">{stat.baseline}</span>
                </div>
                <div className="flex flex-col text-right">
                  <span className="text-[10px] uppercase text-primary-light">ICM Pipeline</span>
                  <span className="text-white font-medium">{stat.icm}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
