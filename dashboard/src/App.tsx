import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Header, DashboardTab } from './components/Header';
import { ScaleSelector, ScaleMode } from './components/ScaleSelector';
import { ModelSelector } from './components/ModelSelector';
import { SpendCascadeComparison } from './components/SpendCascadeComparison';
import { PerTaskComparison } from './components/PerTaskComparison';
import { CacheHitRatio } from './components/CacheHitRatio';
import { CumulativeSavings } from './components/CumulativeSavings';
import { TurnsDuration } from './components/TurnsDuration';
import { RawLedgerTable } from './components/RawLedgerTable';
import { ExperimentCards } from './components/ExperimentCards';
import { DashboardPayload } from './types';
import { deriveDataForModel } from './lib/recalculate';
import { Info, AlertTriangle, RefreshCw, Terminal, PlayCircle } from 'lucide-react';
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
  const [activeTab, setActiveTab] = useState<DashboardTab>('overview');

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
        className="text-xs border-danger/40 text-danger hover:bg-danger/20 gap-1.5"
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
  );

  const renderEmpty = data && !data.has_data && (
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
            <div className="text-muted-foreground"># 1. Populate synthetic fixtures (zero model quota):</div>
            <div className="text-sage">python scripts/run_experiment.py --task MOCK-001 --dry-run</div>
            <div className="text-muted-foreground pt-1"># 2. Export database to dashboard:</div>
            <div className="text-sage">python dashboard/build_data.py</div>
          </div>
          <EmptyActions>
            <Button onClick={() => fetchData()} variant="default" size="sm" className="gap-2">
              <RefreshCw className="size-3.5" /> Check for New Runs
            </Button>
          </EmptyActions>
        </Empty>
      </CardContent>
    </Card>
  );

  const renderOverview = activeData && data?.has_data && (
    <>
      <CumulativeSavings
        cumulative={activeData.cumulative}
        timeline={activeData.timeline}
        scaleMode={scaleMode}
      />

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        <div className="lg:col-span-7 flex">
          <PerTaskComparison tasks={activeData.tasks} scaleMode={scaleMode} />
        </div>
        <div className="lg:col-span-5 flex">
          <CacheHitRatio tasks={activeData.tasks} />
        </div>
      </div>

      <TurnsDuration tasks={activeData.tasks} />
    </>
  );

  const renderSimulator = data?.has_data && (
    <>
      <div className="flex flex-col gap-3">
        <ModelSelector
          selectedModel={selectedModel}
          onModelChange={setSelectedModel}
          pricing={data.pricing || []}
        />
        <ScaleSelector
          scaleMode={scaleMode}
          onScaleChange={setScaleMode}
          totalRuns={activeData?.cumulative.total_runs || 0}
        />
      </div>

      {data.cascade && data.cascade.length > 0 && (
        <SpendCascadeComparison
          cascade={data.cascade}
          selectedModel={selectedModel}
          onSelectModel={setSelectedModel}
        />
      )}
    </>
  );

  const renderExperiments = data?.has_data && activeData && (
    <ExperimentCards tasks={activeData.tasks} />
  );

  const renderEvidence = data?.has_data && activeData && (
    <RawLedgerTable runs={activeData.runs} />
  );

  const tabPanels: { id: DashboardTab; render: React.ReactNode }[] = [
    { id: 'overview', render: renderOverview },
    { id: 'simulator', render: renderSimulator },
    { id: 'experiments', render: renderExperiments },
    { id: 'evidence', render: renderEvidence },
  ];

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col font-sans">
      <Header
        data={activeData}
        loading={loading}
        onRefresh={() => fetchData()}
        activeTab={activeTab}
        onTabChange={setActiveTab}
      />

      <main className="max-w-[1600px] mx-auto w-full px-5 lg:px-8 py-6 flex-1 flex flex-col gap-5">
        {/* Telemetry protocol banner: measured vs simulated separation */}
        <Alert variant="info">
          <Info className="size-5 text-primary-light shrink-0 mt-0.5" />
          <div className="flex flex-col gap-1">
            <AlertTitle className="text-white font-semibold">
              Empirical Benchmark Telemetry vs. Rate-Card Simulations:
            </AlertTitle>
            <AlertDescription className="text-muted-foreground text-xs leading-relaxed font-mono">
              <strong className="text-white">Empirical Benchmark:</strong>{' '}
              <span className="bg-card text-primary-light border border-surface-border px-1.5 py-0.5 rounded font-medium">
                gemini-3.8-flash
              </span>{' '}
              16 paired runs via Antigravity CLI event streams (52.8% cost reduction, cache-read-to-input ratio 4.8% → 390.5%).
              <br />
              <strong className="text-white ml-2">Rate-Card Simulations:</strong>{' '}
              <code className="text-slate-200 font-mono">claude-sonnet-4-6</code>,{' '}
              <code className="text-slate-200 font-mono">claude-sonnet-5</code>,{' '}
              <code className="text-slate-200 font-mono">claude-3-7-sonnet</code>,{' '}
              <code className="text-slate-200 font-mono">gpt-4o</code>,{' '}
              <code className="text-slate-200 font-mono">gemini-2.5-pro/flash</code>, and{' '}
              <code className="text-slate-200 font-mono">glm-5.3-flash</code>{' '}
              re-price the identical measured token workload against published rate cards without paid live API calls. Provider-equivalent models (e.g. FreeBuff GLM) carry $0 direct user cost — USD figures are simulated for workload comparability only.
            </AlertDescription>
          </div>
        </Alert>

        {renderError}
        {renderLoading}
        {renderEmpty}

        {data && data.has_data && (
          <>
            {tabPanels.map((panel) => (
              <section
                key={panel.id}
                role="tabpanel"
                id={`panel-${panel.id}`}
                aria-labelledby={`tab-${panel.id}`}
                hidden={activeTab !== panel.id}
                className="flex flex-col gap-5"
              >
                {panel.render}
              </section>
            ))}
          </>
        )}
      </main>

      <footer className="border-t border-surface-border bg-background px-5 lg:px-8 py-4 mt-8">
        <div className="max-w-[1600px] mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-muted-foreground font-mono">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-primary" />
            <span>Antigravity Interpretable Context Methodology (ICM) Measurement Layer</span>
          </div>
          <div>Auditable Cache Economics • Scaled Token Projections • OKF v0.2</div>
        </div>
      </footer>
    </div>
  );
};
