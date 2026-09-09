import React, { useState } from 'react';
import { ModelCascadeItem } from '../types';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { ToggleGroup, ToggleGroupItem } from './ui/toggle-group';
import { Layers, Check, Zap, Sparkles } from 'lucide-react';
import { formatCurrency, formatSignedCurrency, formatSignedPercent } from '../lib/formatters';

interface SpendCascadeComparisonProps {
  cascade: ModelCascadeItem[];
  selectedModel: string;
  onSelectModel: (model: string) => void;
}

type CascadeScale = '1x' | '10x' | '100x' | '100m' | '1b';

export const SpendCascadeComparison: React.FC<SpendCascadeComparisonProps> = ({
  cascade,
  selectedModel,
  onSelectModel,
}) => {
  const [scale, setScale] = useState<CascadeScale>('1x');

  if (!cascade || cascade.length === 0) {
    return null;
  }

  const getMultiplier = (s: CascadeScale): number => {
    switch (s) {
      case '10x':
        return 10;
      case '100x':
        return 100;
      case '100m':
      case '1b':
      case '1x':
      default:
        return 1;
    }
  };

  const multiplier = getMultiplier(scale);

  return (
    <Card className="border-surface-border bg-surface">
      <CardHeader className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Layers className="size-5 text-primary" />
            <CardTitle className="text-base font-semibold text-white">
              Spend Cascade Across Foundation Models
            </CardTitle>
            <Badge variant="outline" className="border-primary/40 text-primary text-xs">
              Cross-Model Pricing
            </Badge>
          </div>
          <CardDescription className="text-xs text-muted-foreground mt-1">
            Rate-card simulation: re-prices empirical token telemetry (EXP-001–004 on gemini-3.8-flash) across published rate cards without live commercial API calls.
          </CardDescription>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-400">Scale Projection:</span>
          <ToggleGroup
            value={scale}
            onValueChange={(val) => val && setScale(val as CascadeScale)}
            className="bg-background/80 p-0.5 rounded-lg border border-surface-border text-xs"
          >
            <ToggleGroupItem value="1x" className="px-2.5 py-1 text-xs">
              1x Run
            </ToggleGroupItem>
            <ToggleGroupItem value="10x" className="px-2.5 py-1 text-xs">
              10x Batch
            </ToggleGroupItem>
            <ToggleGroupItem value="100x" className="px-2.5 py-1 text-xs">
              100x Batch
            </ToggleGroupItem>
            <ToggleGroupItem value="100m" className="px-2.5 py-1 text-xs">
              100M Tok
            </ToggleGroupItem>
            <ToggleGroupItem value="1b" className="px-2.5 py-1 text-xs">
              1B Tok
            </ToggleGroupItem>
          </ToggleGroup>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-surface-border text-gray-400 font-mono text-[11px] uppercase tracking-wider bg-background/40">
                <th className="py-2.5 px-3">Model</th>
                <th className="py-2.5 px-3">Rate Card (In / Cache / Out)</th>
                <th className="py-2.5 px-3 text-right">Baseline Spend</th>
                <th className="py-2.5 px-3 text-right">ICM Spend</th>
                <th className="py-2.5 px-3 text-right">Net Savings</th>
                <th className="py-2.5 px-3 text-right">Reduction</th>
                <th className="py-2.5 px-3 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border font-mono">
              {cascade.map((item) => {
                const isSelected = selectedModel === item.model;

                let bSpend = item.total_baseline_cost_usd * multiplier;
                let iSpend = item.total_icm_cost_usd * multiplier;
                let saved = item.cumulative_savings_usd * multiplier;

                if (scale === '100m') {
                  bSpend = item.cost_per_mtok_baseline * 100;
                  iSpend = item.cost_per_mtok_icm * 100;
                  saved = item.projected_savings_100m;
                } else if (scale === '1b') {
                  bSpend = item.cost_per_mtok_baseline * 1000;
                  iSpend = item.cost_per_mtok_icm * 1000;
                  saved = item.projected_savings_1b;
                }

                // Relative bar width
                const maxSpend = Math.max(...cascade.map((c) => c.total_baseline_cost_usd));
                const barWidthPct = Math.min(100, Math.max(10, (item.total_baseline_cost_usd / maxSpend) * 100));

                return (
                  <tr
                    key={item.model}
                    className={`hover:bg-white/[0.02] transition-colors ${
                      isSelected ? 'bg-primary/5 border-l-2 border-primary' : ''
                    }`}
                  >
                    <td className="py-3 px-3">
                      <div className="flex flex-col">
                        <span className="font-semibold text-white flex items-center gap-1.5">
                          {item.model}
                          {isSelected && (
                            <Badge variant="secondary" className="text-[10px] py-0 px-1.5 bg-primary/20 text-primary border-primary/30">
                              Active
                            </Badge>
                          )}
                        </span>
                        <div className="w-24 h-1 bg-surface-border rounded-full mt-1.5 overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-emerald-500 to-primary"
                            style={{ width: `${barWidthPct}%` }}
                          />
                        </div>
                      </div>
                    </td>

                    <td className="py-3 px-3 text-gray-300 text-[11px]">
                      <div>
                        ${item.input_usd_per_mtok.toFixed(3)} / ${item.cache_read_usd_per_mtok.toFixed(4)} / ${item.output_usd_per_mtok.toFixed(2)}
                      </div>
                      <div className="text-[10px] text-gray-500">per million tokens</div>
                    </td>

                    <td className="py-3 px-3 text-right text-gray-300">
                      {formatCurrency(bSpend)}
                    </td>

                    <td className="py-3 px-3 text-right font-medium text-emerald-400">
                      {formatCurrency(iSpend)}
                    </td>

                    <td className="py-3 px-3 text-right font-semibold text-primary">
                      {formatSignedCurrency(saved)}
                    </td>

                    <td className="py-3 px-3 text-right">
                      <Badge
                        variant="outline"
                        className="font-mono text-xs border-emerald-500/30 text-emerald-400 bg-emerald-500/10"
                      >
                        {formatSignedPercent(item.cumulative_savings_percent)}
                      </Badge>
                    </td>

                    <td className="py-3 px-3 text-center">
                      <Button
                        variant={isSelected ? 'secondary' : 'outline'}
                        size="sm"
                        disabled={isSelected}
                        onClick={() => onSelectModel(item.model)}
                        className={`text-xs h-7 px-2.5 gap-1 font-sans ${
                          isSelected
                            ? 'bg-primary/20 text-primary border-primary/30'
                            : 'hover:bg-primary/10 hover:text-primary hover:border-primary/40'
                        }`}
                      >
                        {isSelected ? (
                          <>
                            <Check className="size-3" /> Selected
                          </>
                        ) : (
                          <>
                            <Sparkles className="size-3" /> Simulate
                          </>
                        )}
                      </Button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Insight Banner */}
        <div className="p-3 bg-background/60 rounded-lg border border-surface-border text-xs text-gray-300 flex items-start gap-2.5">
          <Zap className="size-4 text-amber-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <span className="font-semibold text-white">Why the Savings Cascade:</span>
            <p className="text-gray-400 text-[11px] leading-relaxed">
              Premium models (e.g., Claude Sonnet 4.6, Sonnet 5, and Claude 3.7 Sonnet) heavily penalize unconstrained agents that repeatedly dump whole repositories and multi-megabyte log files into context.
              By combining <strong className="text-emerald-300">AST symbol filtering</strong> with <strong className="text-primary">byte-stable prompt caching</strong> (90% cache read discount), ICM compounds monetary savings from cents on lightweight flash models to <strong className="text-white">thousands of dollars</strong> on enterprise-tier models.
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
