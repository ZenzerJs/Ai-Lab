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

  const opsSummary = ops?.summary;
  const overheadPct = opsSummary?.duration_overhead_percent;

  return (
    <div className="bg-amber-500/5 border border-amber-500/20 rounded-xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 text-xs font-mono text-amber-200/90 shadow-sm">
      <div className="flex items-start gap-3">
        <Clock className="size-4 text-amber-400 shrink-0 mt-0.5" />
        <div className="space-y-0.5">
          <div className="font-semibold text-white flex items-center gap-2">
            <span>Operational Tradeoff: Duration &amp; Turn Overhead</span>
          </div>
          <p className="text-muted-foreground leading-relaxed">
            The ICM stage gate pipeline introduces structured planning overhead ({overheadPct ? `+${overheadPct}% duration` : 'higher execution turns'}) in exchange for rigorous quality guarantees, zero defect regressions, and cryptographic provenance.
          </p>
        </div>
      </div>
    </div>
  );
};
