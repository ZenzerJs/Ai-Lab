import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Header } from './components/Header';
import { HeroStats } from './components/HeroStats';
import { TradeoffCallout } from './components/TradeoffCallout';
import { TaskComparison } from './components/TaskComparison';
import { TaskTable } from './components/TaskTable';
import { SandboxViewer } from './components/SandboxViewer';
import { SpendCascadeComparison } from './components/SpendCascadeComparison';
import { ModelSelector } from './components/ModelSelector';
import { RawLedgerTable } from './components/RawLedgerTable';
import { DashboardPayload, ScaleMode } from './types';
import { deriveDataForModel } from './lib/recalculate';
import {
  AlertTriangle,
  RefreshCw,
  Terminal,
  PlayCircle,
  LayoutDashboard,
  Layers,
  Cpu,
  Monitor,
  Database,
  ArrowUpRight,
} from 'lucide-react';
import { Alert } from './components/ui/alert';
import { Skeleton } from './components/ui/skeleton';
import { Button } from './components/ui/button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from './components/ui/card';
import { Empty, EmptyIcon, EmptyTitle, EmptyDescription, EmptyActions } from './components/ui/empty';
import { getPublicUrl } from './lib/utils';

type ActiveTab = 'overview' | 'tasks' | 'simulator' | 'sandboxes' | 'audit';

export const App: React.FC = () => {
  const [data, setData] = useState<DashboardPayload | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<ActiveTab>('overview');
  const [selectedModel, setSelectedModel] = useState<string>('recorded');
  const [scaleMode, setScaleMode] = useState<ScaleMode>('1x');

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
    <Alert variant="destructive" className="items-center justify-between glass-panel border-rose-500/30">
      <div className="flex items-center gap-2">
        <AlertTriangle className="size-4 text-rose-400 shrink-0" />
        <span className="text-xs font-mono">{error}</span>
      </div>
      <Button
        variant="outline"
        size="sm"
        onClick={() => fetchData()}
        className="text-xs border-rose-500/40 text-rose-300 hover:bg-rose-500/20 gap-1.5 font-mono"
      >
        <RefreshCw className="size-3" /> Retry
      </Button>
    </Alert>
  );

  const renderLoading = loading && !data && (
    <div className="flex flex-col gap-6">
      <div className="glass-panel rounded-2xl p-6 flex flex-col gap-4">
        <Skeleton className="h-7 w-1/3 bg-white/5" />
        <Skeleton className="h-4 w-1/2 bg-white/5" />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Skeleton className="h-32 rounded-2xl bg-white/5" />
        <Skeleton className="h-32 rounded-2xl bg-white/5" />
        <Skeleton className="h-32 rounded-2xl bg-white/5" />
      </div>
      <Skeleton className="h-72 rounded-2xl bg-white/5" />
    </div>
  );

  const hasAnyRuns = Boolean(data && data.runs && data.runs.length > 0);
  const hasAnyTasks = Boolean(data && data.tasks && data.tasks.length > 0);
  const hasAnyData = Boolean(data && (data.has_data || hasAnyRuns || hasAnyTasks || data.is_demo_report));

  const renderEmpty = data && !hasAnyData && (
    <Card className="glass-panel border-white/10 rounded-2xl shadow-xl">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <PlayCircle className="size-5 text-indigo-400" />
          <CardTitle className="text-white font-mono">Antigravity Benchmark Suite</CardTitle>
        </div>
        <CardDescription className="text-gray-400 font-mono">
          No live benchmark runs detected in usage.db.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Empty className="py-12">
          <EmptyIcon>
            <Terminal className="size-8 text-indigo-400" />
          </EmptyIcon>
          <EmptyTitle className="text-white font-mono">Ready to execute benchmark matrix</EmptyTitle>
          <EmptyDescription className="text-gray-400 font-sans">
            Run empirical A/B trials across task archetypes:
          </EmptyDescription>
          <div className="mt-4 p-4 bg-black/60 rounded-xl border border-white/10 text-left font-mono text-xs text-gray-300 space-y-1.5 w-full max-w-lg shadow-inner">
            <div className="text-gray-500"># Run live benchmark trial:</div>
            <div className="text-emerald-400">python scripts/run_experiment.py --task EXP-002 --runs 1</div>
            <div className="text-gray-500 pt-2"># Export telemetry to dashboard:</div>
            <div className="text-indigo-300">python dashboard/build_data.py</div>
          </div>
          <EmptyActions>
            <Button onClick={() => fetchData()} variant="default" size="sm" className="gap-2 font-mono bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-500/20">
              <RefreshCw className="size-3.5" /> Check for New Runs
            </Button>
          </EmptyActions>
        </Empty>
      </CardContent>
    </Card>
  );

  return (
    <div className="min-h-screen bg-[#080b11] text-foreground flex flex-col font-sans selection:bg-indigo-500/25">
      <Header
        data={activeData}
        loading={loading}
        onRefresh={() => fetchData()}
      />

      <main className="max-w-[1440px] mx-auto w-full px-5 lg:px-8 py-6 flex-1 space-y-6">
        {renderError}
        {renderLoading}
        {renderEmpty}

        {activeData && (activeData.is_demo_report || !activeData.cumulative?.has_measured_data) && (
          <div
            data-testid="demo-fixture-banner"
            className="rounded-2xl border border-amber-500/40 bg-amber-500/10 p-4 text-amber-200 flex items-start gap-3 backdrop-blur-md"
          >
            <AlertTriangle className="size-5 shrink-0 mt-0.5 text-amber-400" />
            <div className="flex-1 space-y-1">
              <div className="font-bold text-sm tracking-wide uppercase font-mono text-amber-300">
                DEMO / FIXTURE DATA (Empirical Headlines Suppressed)
              </div>
              <div className="text-xs text-amber-200/90 leading-relaxed font-sans">
                This dashboard snapshot was generated from synthetic fixture replays. Headline claims are suppressed until verified live runs are recorded.
              </div>
            </div>
          </div>
        )}

        {data && hasAnyData && (
          <div className="flex flex-col gap-6">
            {/* Top Interactive Tab Bar */}
            <div className="flex items-center justify-between border-b border-white/10 pb-3 flex-wrap gap-3">
              <nav className="flex items-center gap-1.5 p-1 rounded-xl bg-[#0e1422] border border-white/10 backdrop-blur">
                <button
                  onClick={() => setActiveTab('overview')}
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-mono font-medium transition-all ${
                    activeTab === 'overview'
                      ? 'bg-indigo-600 text-white shadow-md shadow-indigo-500/20'
                      : 'text-gray-400 hover:text-white hover:bg-white/5'
                  }`}
                >
                  <LayoutDashboard className="size-3.5" />
                  <span>Overview &amp; Impact</span>
                </button>

                <button
                  onClick={() => setActiveTab('tasks')}
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-mono font-medium transition-all ${
                    activeTab === 'tasks'
                      ? 'bg-indigo-600 text-white shadow-md shadow-indigo-500/20'
                      : 'text-gray-400 hover:text-white hover:bg-white/5'
                  }`}
                >
                  <Layers className="size-3.5" />
                  <span>Task Breakdown</span>
                  <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-black/40 text-gray-300 border border-white/10">
                    {activeData?.tasks?.length || 0}
                  </span>
                </button>

                <button
                  onClick={() => setActiveTab('simulator')}
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-mono font-medium transition-all ${
                    activeTab === 'simulator'
                      ? 'bg-indigo-600 text-white shadow-md shadow-indigo-500/20'
                      : 'text-gray-400 hover:text-white hover:bg-white/5'
                  }`}
                >
                  <Cpu className="size-3.5" />
                  <span>Frontier Spend Cascade</span>
                  <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                    Multi-Model
                  </span>
                </button>

                <button
                  onClick={() => setActiveTab('sandboxes')}
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-mono font-medium transition-all ${
                    activeTab === 'sandboxes'
                      ? 'bg-indigo-600 text-white shadow-md shadow-indigo-500/20'
                      : 'text-gray-400 hover:text-white hover:bg-white/5'
                  }`}
                >
                  <Monitor className="size-3.5" />
                  <span>Output Sandboxes</span>
                </button>

                <button
                  onClick={() => setActiveTab('audit')}
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-mono font-medium transition-all ${
                    activeTab === 'audit'
                      ? 'bg-indigo-600 text-white shadow-md shadow-indigo-500/20'
                      : 'text-gray-400 hover:text-white hover:bg-white/5'
                  }`}
                >
                  <Database className="size-3.5" />
                  <span>Audit Ledger</span>
                  <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-black/40 text-gray-300 border border-white/10">
                    {activeData?.runs?.length || 0}
                  </span>
                </button>
              </nav>

              <div className="flex items-center gap-2">
                <span className="text-[11px] font-mono text-gray-400">Model Scope:</span>
                <span className="text-xs font-mono font-semibold text-indigo-300 bg-indigo-500/10 border border-indigo-500/20 px-2.5 py-1 rounded-lg">
                  {selectedModel === 'recorded' ? 'Recorded Live CLI' : selectedModel}
                </span>
              </div>
            </div>

            {/* TAB CONTENT: 1. OVERVIEW */}
            {activeTab === 'overview' && (
              <div className="flex flex-col gap-6 animate-in fade-in duration-300">
                <HeroStats
                  headline={activeData?.headline}
                  totalRuns={activeData?.cumulative?.total_runs || 0}
                />

                {activeData && <TradeoffCallout data={activeData} />}

                {activeData && activeData.tasks && (
                  <TaskComparison tasks={activeData.tasks} />
                )}

                {/* Quick preview of Frontier Model Economics */}
                {activeData?.cascade && activeData.cascade.length > 0 && (
                  <div className="pt-2">
                    <div className="flex items-center justify-between mb-3">
                      <div>
                        <h3 className="text-sm font-bold text-white font-mono">
                          Frontier Model Economic Simulation
                        </h3>
                        <p className="text-xs text-gray-400 font-mono">
                          Repriced token workloads across major foundation model rate cards.
                        </p>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setActiveTab('simulator')}
                        className="text-xs font-mono text-indigo-300 border-indigo-500/30 hover:bg-indigo-500/10 gap-1.5"
                      >
                        Explore Full Simulator <ArrowUpRight className="size-3.5" />
                      </Button>
                    </div>
                    <SpendCascadeComparison
                      cascade={activeData.cascade}
                      selectedModel={selectedModel}
                      onSelectModel={setSelectedModel}
                      scaleMode={scaleMode}
                    />
                  </div>
                )}
              </div>
            )}

            {/* TAB CONTENT: 2. TASKS */}
            {activeTab === 'tasks' && activeData?.tasks && (
              <div className="flex flex-col gap-6 animate-in fade-in duration-300">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-base font-bold text-white font-mono">
                      Empirical Task Matrix &amp; Quality Metrics
                    </h2>
                    <p className="text-xs text-gray-400 font-mono">
                      Per-task token consumption, cache hit ratios, execution duration, and defect assertions.
                    </p>
                  </div>
                </div>
                <TaskTable tasks={activeData.tasks} />
              </div>
            )}

            {/* TAB CONTENT: 3. FRONTIER SIMULATOR */}
            {activeTab === 'simulator' && activeData && (
              <div className="flex flex-col gap-6 animate-in fade-in duration-300">
                <ModelSelector
                  selectedModel={selectedModel}
                  onModelChange={setSelectedModel}
                  pricing={activeData.pricing || []}
                />

                {/* Scale Multiplier Controls */}
                <div className="p-4 rounded-xl glass-panel border-white/10 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                  <div>
                    <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-gray-300">
                      Token Volume Scale Multiplier
                    </h4>
                    <p className="text-xs text-gray-400 font-mono mt-0.5">
                      Project fleet-wide cost reductions from single task runs up to 100M token engineering fleets.
                    </p>
                  </div>
                  <div className="flex items-center gap-1.5 bg-black/40 p-1 rounded-lg border border-white/10 font-mono text-xs">
                    {(['1x', '1m', '10m', '100m'] as ScaleMode[]).map((mode) => (
                      <button
                        key={mode}
                        onClick={() => setScaleMode(mode)}
                        className={`px-3 py-1 rounded-md transition-all ${
                          scaleMode === mode
                            ? 'bg-indigo-600 text-white font-bold shadow'
                            : 'text-gray-400 hover:text-white'
                        }`}
                      >
                        {mode.toUpperCase()}
                      </button>
                    ))}
                  </div>
                </div>

                {activeData.cascade && (
                  <SpendCascadeComparison
                    cascade={activeData.cascade}
                    selectedModel={selectedModel}
                    onSelectModel={setSelectedModel}
                    scaleMode={scaleMode}
                  />
                )}
              </div>
            )}

            {/* TAB CONTENT: 4. SANDBOXES */}
            {activeTab === 'sandboxes' && (
              <div className="flex flex-col gap-6 animate-in fade-in duration-300">
                <div>
                  <h2 className="text-base font-bold text-white font-mono">
                    Interactive Verification Sandboxes &amp; Playwright Test Runs
                  </h2>
                  <p className="text-xs text-gray-400 font-mono">
                    Inspect actual artifacts and visual sandboxes generated by governed vs unconstrained agents.
                  </p>
                </div>
                <SandboxViewer />
              </div>
            )}

            {/* TAB CONTENT: 5. AUDIT LEDGER */}
            {activeTab === 'audit' && activeData?.runs && (
              <div className="flex flex-col gap-6 animate-in fade-in duration-300">
                <div>
                  <h2 className="text-base font-bold text-white font-mono">
                    Cryptographic Provenance Ledger
                  </h2>
                  <p className="text-xs text-gray-400 font-mono">
                    All individual runs recorded in SQLite with byte-exact SHA-256 evidence digests.
                  </p>
                </div>
                <RawLedgerTable
                  runs={activeData.runs}
                  generatedAt={activeData.generated_at}
                  buildIdentity={activeData.build_identity}
                />
              </div>
            )}
          </div>
        )}
      </main>

      <footer className="border-t border-white/10 bg-[#06080d] px-5 lg:px-8 py-5 mt-10">
        <div className="max-w-[1440px] mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-gray-400 font-mono">
          <div className="flex items-center gap-2.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(16,185,129,0.8)]" />
            <span className="text-gray-300">Antigravity Interpretable Context Methodology (ICM) Measurement Layer</span>
          </div>
          <div className="text-gray-500">Auditable Cache Economics • Provenance Hashed • OKF v0.2</div>
        </div>
      </footer>
    </div>
  );
};
