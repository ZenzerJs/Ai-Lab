import React from 'react';
import { Layers, TrendingUp } from 'lucide-react';
import { Badge } from './ui/badge';
import { ToggleGroup, ToggleGroupItem } from './ui/toggle-group';

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
      <div className="flex items-center gap-3">
        <div className="size-8 rounded-lg bg-primary/10 border border-primary/30 flex items-center justify-center shrink-0">
          <TrendingUp className="size-4 text-primary" />
        </div>
        <div className="flex flex-col gap-0.5">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-white">Token Volume Scale Multiplier</span>
            <Badge variant="secondary" className="text-[10px] py-0 px-1.5 font-normal">
              n={totalRuns} calibrated runs
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground">
            Project measured cache economics across standard token volume scales.
          </p>
        </div>
      </div>

      <ToggleGroup
        value={scaleMode}
        onValueChange={(val) => onScaleChange(val as ScaleMode)}
        aria-label="Token volume scale multiplier selector"
        className="self-stretch md:self-auto justify-start"
      >
        {options.map((opt) => (
          <ToggleGroupItem
            key={opt.id}
            value={opt.id}
            title={opt.desc}
          >
            <Layers className="size-3 opacity-70" />
            <span>{opt.label}</span>
          </ToggleGroupItem>
        ))}
      </ToggleGroup>
    </div>
  );
};
