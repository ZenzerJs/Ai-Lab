import React from 'react';
import { Clock } from 'lucide-react';
import { DashboardPayload } from '../types';

interface TradeoffCalloutProps {
  data: DashboardPayload;
}

export const TradeoffCallout: React.FC<TradeoffCalloutProps> = ({ data }) => {
  const ops = data.operational;
  const cum = data.cumulative;

  if (!ops?.has_data && !cum?.has_measured_data) {
    return null;
  }

  return (
    <div className="relative overflow-hidden rounded-2xl border border-amber-500/30 bg-gradient-to-r from-amber-950/30 via-slate-900/60 to-background/80 p-4.5 backdrop-blur-md shadow-lg">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 text-xs font-mono">
        <div className="flex items-start gap-3.5">
          <div className="size-9 rounded-lg bg-amber-500/15 border border-amber-500/30 flex items-center justify-center shrink-0 text-amber-400">
            <Clock className="size-4.5" />
          </div>
          <div className="space-y-1">
            <div className="font-bold text-white flex items-center gap-2 text-sm tracking-tight font-sans">
              <span>Transparent Operational Tradeoff: Planning Ceremony</span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40">
                Governance Cost
              </span>
            </div>
            <p className="text-gray-300 leading-relaxed font-sans text-xs">
              ICM stage contracts enforce formal intake, AST planning, and verify-before-merge gates. This incurs structured planning ceremony on trivial micro-helpers, but unlocks <strong>50–70% cost reduction</strong> and <strong>zero defect regressions</strong> across production architectures.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
