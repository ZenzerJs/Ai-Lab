import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { PerTaskComparison } from './components/PerTaskComparison';
import { CacheHitRatio } from './components/CacheHitRatio';
import { CumulativeSavings } from './components/CumulativeSavings';
import { TurnsDuration } from './components/TurnsDuration';
import { RawLedgerTable } from './components/RawLedgerTable';
import { DashboardPayload } from './types';
import { Info, AlertTriangle, ShieldCheck } from 'lucide-react';

export const App: React.FC = () => {
  const [data, setData] = useState<DashboardPayload | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/data.json', { cache: 'no-store' });
      if (!response.ok) {
        throw new Error(`Failed to load data.json: HTTP ${response.status}`);
      }
      const json: DashboardPayload = await response.json();
      setData(json);
    } catch (err: any) {
      setError(err.message || 'Error fetching dashboard data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  return (
    <div className="min-h-screen bg-background text-gray-100 flex flex-col font-sans">
      <Header data={data} loading={loading} onRefresh={fetchData} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 space-y-6">
        {/* Banner: Verification Mode Notice */}
        <div className="bg-primary/10 border border-primary/30 rounded-xl p-4 flex items-start gap-3 text-xs">
          <Info className="w-5 h-5 text-primary shrink-0 mt-0.5" />
          <div className="space-y-1">
            <span className="font-semibold text-white">Verification & Calibration Environment:</span>
            <p className="text-gray-300">
              No live model calls were made. The ledger currently contains only MOCK-001 data.
              To record real A/B trials, execute <code className="bg-background px-1.5 py-0.5 rounded border border-surface-border text-primary">python scripts/run_experiment.py --task &lt;TASK-ID&gt;</code> from the terminal.
            </p>
          </div>
        </div>

        {error && (
          <div className="bg-red-500/15 border border-red-500/40 rounded-xl p-4 text-xs text-red-300 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-red-400" />
            <span>{error}</span>
          </div>
        )}

        {loading && !data && (
          <div className="py-24 text-center space-y-3">
            <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-xs text-gray-400 font-mono">Loading usage ledger data...</p>
          </div>
        )}

        {data && (
          <>
            {/* View 3: Cumulative Savings Card & Running Line */}
            <CumulativeSavings
              cumulative={data.cumulative}
              timeline={data.timeline}
            />

            {/* Grid: View 1 (Per-Task Cost) and View 2 (Cache Hit Ratio) */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <PerTaskComparison tasks={data.tasks} />
              <CacheHitRatio tasks={data.tasks} />
            </div>

            {/* View 4: Turns & Duration Telemetry */}
            <TurnsDuration tasks={data.tasks} />

            {/* View 5: Raw Ledger Table */}
            <RawLedgerTable runs={data.runs} />
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-surface-border bg-surface/50 py-4 px-6 mt-12 text-xs text-gray-500 text-center flex flex-col sm:flex-row justify-between items-center max-w-7xl mx-auto w-full gap-2 font-mono">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span>Antigravity Interpretable Context Methodology (ICM) Measurement Layer</span>
        </div>
        <div>
          <span>Auditable Cache Economics • OKF v0.2 Compliant</span>
        </div>
      </footer>
    </div>
  );
};
