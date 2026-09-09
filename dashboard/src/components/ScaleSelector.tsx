import React from 'react';
import { Layers, TrendingUp } from 'lucide-react';

export type ScaleMode = '1x' | '1m' | '10m' | '100m';

interface ScaleSelectorProps {
  scaleMode: ScaleMode;
  onScaleChange: (mode: ScaleMode) => void;
  totalRuns: number;
}

export const ScaleSelector: React.FC<ScaleSelectorProps> = ({
  scaleMode,
  onScaleChange,
  totalRuns,
}) => {
  const options: { id: ScaleMode; label: string; desc: string }[] = [
    { id: '1x', label: '1x (Raw Runs)', desc: 'Actual per-task run costs' },
    { id: '1m', label: '1M Tokens', desc: 'Normalized per 1,000,000 tokens' },
    { id: '10m', label: '10M Tokens', desc: 'Engineering team scale' },
    { id: '100m', label: '100M Tokens', desc: 'Enterprise monthly volume' },
  ];

  return (
    <div className="bg-surface border border-surface-border rounded-xl p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-sm">
      <div className="flex items-center gap-2.5">
        <div className="w-8 h-8 rounded-lg bg-primary/10 border border-primary/30 flex items-center justify-center shrink-0">
          <TrendingUp className="w-4 h-4 text-primary" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-white">Token Volume Scale Multiplier</span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-surface-border text-gray-300">
              n={totalRuns} calibrated runs
            </span>
          </div>
          <p className="text-xs text-gray-400">
            Project measured cache economics across standard token volume scales.
          </p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-1.5 bg-background/80 p-1 rounded-lg border border-surface-border self-stretch md:self-auto justify-start">
        {options.map((opt) => {
          const active = scaleMode === opt.id;
          return (
            <button
              key={opt.id}
              onClick={() => onScaleChange(opt.id)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium font-mono transition-all flex items-center gap-1.5 ${
                active
                  ? 'bg-primary text-white shadow-sm'
                  : 'text-gray-400 hover:text-white hover:bg-surface-hover'
              }`}
              title={opt.desc}
            >
              <Layers className="w-3 h-3 opacity-70" />
              <span>{opt.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
};
