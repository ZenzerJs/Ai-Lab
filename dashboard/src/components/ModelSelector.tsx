import React from 'react';
import { PricingRecord } from '../types';
import { SelectNative } from './ui/select-native';
import { Cpu } from 'lucide-react';
import { Badge } from './ui/badge';

interface ModelSelectorProps {
  selectedModel: string;
  onModelChange: (model: string) => void;
  pricing: PricingRecord[];
}

export const ModelSelector: React.FC<ModelSelectorProps> = ({
  selectedModel,
  onModelChange,
  pricing,
}) => {
  const currentPricing = pricing.find((p) => p.model === selectedModel);

  return (
    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-4 rounded-xl border border-surface-border bg-surface shadow-sm">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-primary/10 border border-primary/20 text-primary shrink-0">
          <Cpu className="size-5" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-white">
              Model Rate Card Simulation
            </span>
            {selectedModel !== 'recorded' && (
              <Badge variant="secondary" className="text-xs bg-primary/20 text-primary border-primary/30">
                Simulated
              </Badge>
            )}
            {currentPricing?.pricing_mode === 'provider-equivalent' && (
              <Badge
                variant="outline"
                className="text-xs border-amber-500/40 text-amber-400 bg-amber-500/10"
                title={currentPricing.provider_note ?? undefined}
              >
                Provider-equivalent · $0 direct cost
              </Badge>
            )}
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">
            Re-price identical token workloads across foundation models to demonstrate spend cascade.
          </p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3 w-full sm:w-auto">
        {currentPricing && (
          <div className="hidden lg:flex items-center gap-2 text-xs font-mono text-gray-300 bg-background/80 px-3 py-1.5 rounded-lg border border-surface-border">
            <span className="text-gray-400">In:</span>
            <span className="text-emerald-400 font-medium">${currentPricing.input_usd_per_mtok}/M</span>
            <span className="text-gray-500">•</span>
            <span className="text-gray-400">Cache:</span>
            <span className="text-cyan-400 font-medium">${currentPricing.cache_read_usd_per_mtok}/M</span>
            <span className="text-gray-500">•</span>
            <span className="text-gray-400">Out:</span>
            <span className="text-amber-400 font-medium">${currentPricing.output_usd_per_mtok}/M</span>
          </div>
        )}

        <div className="w-full sm:w-64">
          <SelectNative
            value={selectedModel}
            onChange={(e) => onModelChange(e.target.value)}
            className="w-full text-xs font-mono bg-background border-surface-border"
          >
            <option value="recorded">As Recorded (Original)</option>
            {pricing.map((p) => (
              <option key={p.model} value={p.model}>
                {p.model}
                {p.pricing_mode === 'provider-equivalent' ? ' (provider-equivalent, $0 direct)' : ''} (${p.input_usd_per_mtok}/M in, ${p.output_usd_per_mtok}/M out)
              </option>
            ))}
          </SelectNative>
        </div>
      </div>
    </div>
  );
};
