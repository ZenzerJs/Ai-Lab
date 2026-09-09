import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Header } from './components/Header';
import { ScaleSelector, ScaleMode } from './components/ScaleSelector';
import { ModelSelector } from './components/ModelSelector';
import { SpendCascadeComparison } from './components/SpendCascadeComparison';
import { PerTaskComparison } from './components/PerTaskComparison';
import { CacheHitRatio } from './components/CacheHitRatio';
import { CumulativeSavings } from './components/CumulativeSavings';
import { TurnsDuration } from './components/TurnsDuration';
import { RawLedgerTable } from './components/RawLedgerTable';
import { DashboardPayload } from './types';
import { deriveDataForModel } from './lib/recalculate';
import { Info, AlertTriangle, ShieldCheck, RefreshCw, Terminal, PlayCircle } from 'lucide-react';
import { Alert, AlertTitle, AlertDescription } from './components/ui/alert';
import { Skeleton } from './components/ui/skeleton';
import { Button } from './components/ui/button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from './components/ui/card';
import { Empty, EmptyIcon, EmptyTitle, EmptyDescription, EmptyActions } from './components/ui/empty';
import { getPublicUrl } from './lib/utils';

export const App: React.FC = () => {
  const [data, setData] = useState<DashboardPayload | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [scaleMode, setScaleMode] = useState<ScaleMode>('1x');
  const [selectedModel, setSelectedModel] = useState<string>('recorded');

  const activeData = useMemo(() => {
    return deriveDataForModel(data, selectedModel);
  }, [data, selectedModel]);

  const fetchData = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(getPublicUrl('data.json'), {
        cache: 'no-store',
        signal,
      });
      if (!response.ok) {
        throw new Error(`Failed to load data.json: HTTP ${response.status}`);
      }
      const json: DashboardPayload = await response.json();
      setData(json);
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        return;
      }
      const message = err instanceof Error ? err.message : 'Error fetching dashboard data';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    fetchData(controller.signal);
    return () => controller.abort();
  }, [fetchData]);

  return (
    <div className="min-h-screen bg-background text-gray-100 flex flex-col font-sans">
      <Header data={activeData} loading={loading} onRefresh={() => fetchData()} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 flex flex-col gap-6">
        {/* Banner: Operational Notice & Model Disclaimer */}
        <Alert variant="info">
          <Info className="size-5 text-primary shrink-0 mt-0.5" />
          <div className="flex flex-col gap-1">
            <AlertTitle className="text-white font-semibold">
              Empirical Benchmark Telemetry vs. Rate-Card Simulations:
            </AlertTitle>
            <AlertDescription className="text-gray-300 text-xs leading-relaxed">
              <strong className="text-white">Empirical Benchmark:</strong> 16 runs evaluated live against <code className="text-primary font-mono font-medium">gemini-3.8-flash</code> via Antigravity CLI event streams (52.82% cost reduction, cache ratio 4.8% → 390.5%).
              <br />
              <strong className="text-white">Rate-Card Simulations:</strong> Models such as <code className="text-emerald-300 font-mono">claude-sonnet-4-6</code>, <code className="text-emerald-300 font-mono">claude-sonnet-5</code>, <code className="text-emerald-300 font-mono">claude-3-7-sonnet</code>, <code className="text-emerald-300 font-mono">gpt-4o</code>, and <code className="text-emerald-300 font-mono">gemini-2.5-pro</code> dynamically re-price this exact measured token workload across published rate cards without incurring paid live API calls to those specific endpoints.
            </AlertDescription>
          </div>
        </Alert>

        {error && (
          <Alert variant="destructive" className="items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertTriangle className="size-4 text-red-400 shrink-0" />
              <span>{error}</span>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => fetchData()}
              className="text-xs border-red-500/40 text-red-300 hover:bg-red-500/20 gap-1.5"
            >
              <RefreshCw className="size-3" /> Retry
            </Button>
          </Alert>
        )}

        {loading && !data && (
          <div className="flex flex-col gap-6">
            <div className="rounded-xl border border-surface-border p-5 bg-surface flex flex-col gap-3">
              <Skeleton className="h-6 w-1/3" />
              <Skeleton className="h-4 w-1/2" />
            </div>
            <div className="rounded-xl border border-surface-border p-5 bg-surface flex flex-col gap-4">
              <Skeleton className="h-7 w-1/4" />
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <Skeleton className="h-20" />
                <Skeleton className="h-20" />
                <Skeleton className="h-20" />
                <Skeleton className="h-20" />
              </div>
              <Skeleton className="h-60 w-full" />
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Skeleton className="h-80 rounded-xl" />
              <Skeleton className="h-80 rounded-xl" />
            </div>
          </div>
        )}

        {data && !data.has_data && (
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <PlayCircle className="size-5 text-primary" />
                <CardTitle>Welcome to Antigravity AI-Lab Benchmark Dashboard</CardTitle>
              </div>
              <CardDescription>
                No benchmark runs have been recorded in the local ledger database yet.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Empty className="py-12">
                <EmptyIcon>
                  <Terminal className="size-8 text-primary" />
                </EmptyIcon>
                <EmptyTitle>Ready to execute your first benchmark</EmptyTitle>
                <EmptyDescription>
                  Generate synthetic dry-run data or execute live model evaluations to populate token economics and cache ratio curves:
                </EmptyDescription>
                <div className="mt-4 p-3 bg-background rounded-lg border border-surface-border text-left font-mono text-xs text-gray-300 space-y-1 w-full max-w-lg">
                  <div className="text-gray-500"># 1. Populate synthetic fixtures (zero model quota):</div>
                  <div className="text-emerald-400">python scripts/run_experiment.py --task MOCK-001 --dry-run</div>
                  <div className="text-gray-500 pt-1"># 2. Export database to dashboard:</div>
                  <div className="text-emerald-400">python dashboard/build_data.py</div>
                </div>
                <EmptyActions>
                  <Button
                    onClick={() => fetchData()}
                    variant="default"
                    size="sm"
                    className="gap-2"
                  >
                    <RefreshCw className="size-3.5" /> Check for New Runs
                  </Button>
                </EmptyActions>
              </Empty>
            </CardContent>
          </Card>
        )}

        {data && data.has_data && activeData && (
          <>
            {/* Simulation Controls: Model Rate Card & Volume Scale Multiplier */}
            <div className="flex flex-col gap-3">
              <ModelSelector
                selectedModel={selectedModel}
                onModelChange={setSelectedModel}
                pricing={data.pricing || []}
              />
              <ScaleSelector
                scaleMode={scaleMode}
                onScaleChange={setScaleMode}
                totalRuns={activeData.cumulative.total_runs || 0}
              />
            </div>

            {/* Cross-Model Spend Cascade Visualizer */}
            {data.cascade && data.cascade.length > 0 && (
              <SpendCascadeComparison
                cascade={data.cascade}
                selectedModel={selectedModel}
                onSelectModel={setSelectedModel}
              />
            )}

            {/* View 3: Cumulative Savings Card & Running Line */}
            <CumulativeSavings
              cumulative={activeData.cumulative}
              timeline={activeData.timeline}
              scaleMode={scaleMode}
            />

            {/* Grid: View 1 (Per-Task Cost) and View 2 (Cache Hit Ratio) */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <PerTaskComparison tasks={activeData.tasks} scaleMode={scaleMode} />
              <CacheHitRatio tasks={activeData.tasks} />
            </div>

            {/* View 4: Turns & Duration Telemetry */}
            <TurnsDuration tasks={activeData.tasks} />

            {/* View 5: Raw Ledger Table */}
            <RawLedgerTable runs={activeData.runs} />
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-surface-border bg-surface/50 py-4 px-6 mt-12 text-xs text-muted-foreground text-center flex flex-col sm:flex-row justify-between items-center max-w-7xl mx-auto w-full gap-2 font-mono">
        <div className="flex items-center gap-2">
          <ShieldCheck className="size-4 text-emerald-400" />
          <span>Antigravity Interpretable Context Methodology (ICM) Measurement Layer</span>
        </div>
        <div>
          <span>Auditable Cache Economics • Scaled Token Projections • OKF v0.2</span>
        </div>
      </footer>
    </div>
  );
};
