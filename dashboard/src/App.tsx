import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Header } from './components/Header';
import { HeroStats } from './components/HeroStats';
import { TradeoffCallout } from './components/TradeoffCallout';
import { TaskComparison } from './components/TaskComparison';
import { TaskTable } from './components/TaskTable';
import { SandboxViewer } from './components/SandboxViewer';
import { MethodologyDrawer } from './components/MethodologyDrawer';
import { DashboardPayload } from './types';
import { deriveDataForModel } from './lib/recalculate';
import { AlertTriangle, RefreshCw, Terminal, PlayCircle } from 'lucide-react';
import { Alert } from './components/ui/alert';
import { Skeleton } from './components/ui/skeleton';
import { Button } from './components/ui/button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from './components/ui/card';
import { Empty, EmptyIcon, EmptyTitle, EmptyDescription, EmptyActions } from './components/ui/empty';
import { getPublicUrl } from './lib/utils';

export const App: React.FC = () => {
  const [data, setData] = useState<DashboardPayload | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
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

  const renderError = error && (
    <Alert variant="destructive" className="items-center justify-between">
      <div className="flex items-center gap-2">
        <AlertTriangle className="size-4 text-danger shrink-0" />
        <span>{error}</span>
      </div>
      <Button
        variant="outline"
        size="sm"
        onClick={() => fetchData()}
        className="text-xs border-danger/40 text-danger hover:bg-danger/20 gap-1.5 font-mono"
      >
        <RefreshCw className="size-3" /> Retry
      </Button>
    </Alert>
  );

  const renderLoading = loading && !data && (
    <div className="flex flex-col gap-6">
      <div className="rounded-xl border border-surface-border p-5 bg-surface flex flex-col gap-3">
        <Skeleton className="h-6 w-1/3" />
        <Skeleton className="h-4 w-1/2" />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Skeleton className="h-28 rounded-xl" />
        <Skeleton className="h-28 rounded-xl" />
        <Skeleton className="h-28 rounded-xl" />
      </div>
      <Skeleton className="h-64 rounded-xl" />
    </div>
  );

  const hasAnyRuns = Boolean(data && data.runs && data.runs.length > 0);
  const hasAnyTasks = Boolean(data && data.tasks && data.tasks.length > 0);
  const hasAnyData = Boolean(data && (data.has_data || hasAnyRuns || hasAnyTasks || data.is_demo_report));

  const renderEmpty = data && !hasAnyData && (
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
            Execute live model evaluations to populate token economics and cache ratio curves:
          </EmptyDescription>
          <div className="mt-4 p-3 bg-background rounded-lg border border-surface-border text-left font-mono text-xs text-gray-300 space-y-1 w-full max-w-lg">
            <div className="text-muted-foreground"># Run live benchmark trial:</div>
            <div className="text-sage">python scripts/run_experiment.py --task EXP-001 --runs 3</div>
            <div className="text-muted-foreground pt-1"># Export database to dashboard:</div>
            <div className="text-sage">python dashboard/build_data.py</div>
          </div>
          <EmptyActions>
            <Button onClick={() => fetchData()} variant="default" size="sm" className="gap-2 font-mono">
              <RefreshCw className="size-3.5" /> Check for New Runs
            </Button>
          </EmptyActions>
        </Empty>
      </CardContent>
    </Card>
  );

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col font-sans selection:bg-primary/20">
      <Header
        data={activeData}
        loading={loading}
        onRefresh={() => fetchData()}
      />

      <main className="max-w-[1400px] mx-auto w-full px-5 lg:px-8 py-6 flex-1 space-y-6">
        {renderError}
        {renderLoading}
        {renderEmpty}

        {activeData && (activeData.is_demo_report || !activeData.cumulative?.has_measured_data) && (
          <div
            data-testid="demo-fixture-banner"
            className="rounded-lg border border-warning/40 bg-warning/10 p-4 text-warning flex items-start gap-3"
          >
            <AlertTriangle className="size-5 shrink-0 mt-0.5" />
            <div className="flex-1 space-y-1">
              <div className="font-semibold text-sm tracking-wide uppercase font-mono">
                DEMO / FIXTURE DATA (Empirical Headlines Suppressed)
              </div>
              <div className="text-xs text-warning/90 leading-relaxed font-sans">
                This dashboard is displaying synthetic fixtures or dry-run replayed telemetry. Empirical headline metrics and savings claims are suppressed until verified live benchmark telemetry is recorded.
              </div>
            </div>
          </div>
        )}

        {data && hasAnyData && (
          <div className="flex flex-col gap-6">
            {/* 1. Hero Headline & Big Impact Stat Tiles */}
            <HeroStats
              headline={activeData?.headline}
              totalRuns={activeData?.cumulative?.total_runs || 0}
            />

            {/* 2. Honest Operational Tradeoff Callout */}
            {activeData && <TradeoffCallout data={activeData} />}

            {/* 3. Primary Cost Comparison Chart */}
            {activeData && activeData.tasks && (
              <TaskComparison tasks={activeData.tasks} />
            )}

            {/* 4. Task-by-Task Telemetry & Quality Table */}
            {activeData && activeData.tasks && (
              <TaskTable tasks={activeData.tasks} />
            )}

            {/* 5. See the Output: Interactive Sandbox Viewer */}
            <div className="pt-2">
              <div className="mb-3">
                <h3 className="text-sm font-semibold text-white font-mono">
                  Verified Generated Output
                </h3>
                <p className="text-xs text-muted-foreground font-mono">
                  Side-by-side verification artifacts and interactive sandboxes built by benchmark arms.
                </p>
              </div>
              <SandboxViewer />
            </div>

            {/* 6. Collapsible Methodology & SQLite Audit Ledger Drawer */}
            {activeData && (
              <MethodologyDrawer
                data={activeData}
                selectedModel={selectedModel}
                onModelChange={setSelectedModel}
              />
            )}
          </div>
        )}
      </main>

      <footer className="border-t border-surface-border bg-background px-5 lg:px-8 py-4 mt-8">
        <div className="max-w-[1400px] mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-muted-foreground font-mono">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-primary" />
            <span>Antigravity Interpretable Context Methodology (ICM) Measurement Layer</span>
          </div>
          <div>Auditable Cache Economics • Provenance Hashed • OKF v0.2</div>
        </div>
      </footer>
    </div>
  );
};
