import React, { useLayoutEffect, useRef, useState } from 'react';
import { Download, RefreshCw, Sparkles, ShieldCheck, Database } from 'lucide-react';
import { DashboardPayload } from '../types';
import { Button, buttonVariants } from './ui/button';
import { cn, getPublicUrl } from '../lib/utils';

interface HeaderProps {
  data: DashboardPayload | null;
  loading: boolean;
  onRefresh: () => void;
  activeTab: DashboardTab;
  onTabChange: (tab: DashboardTab) => void;
}

export type DashboardTab = 'showcase' | 'sandboxes' | 'telemetry' | 'simulator' | 'evidence';

export const TAB_ITEMS: { id: DashboardTab; label: string }[] = [
  { id: 'showcase', label: 'Visual Showcase' },
  { id: 'sandboxes', label: 'Live Sandboxes & Demos' },
  { id: 'telemetry', label: 'Telemetry & Statistics' },
  { id: 'simulator', label: 'Model Simulator' },
  { id: 'evidence', label: 'Audit Ledger & Provenance' },
];

export const Header: React.FC<HeaderProps> = ({
  data,
  loading,
  onRefresh,
  activeTab,
  onTabChange,
}) => {
  const navRef = useRef<HTMLElement>(null);
  const pillRef = useRef<HTMLDivElement>(null);
  const tabRefs = useRef<Map<DashboardTab, HTMLButtonElement>>(new Map());
  const [pillReady, setPillReady] = useState(false);

  const updatePill = (tab: DashboardTab): void => {
    const nav = navRef.current;
    const pill = pillRef.current;
    const btn = tabRefs.current.get(tab);
    if (!nav || !pill || !btn) return;
    const navRect = nav.getBoundingClientRect();
    const btnRect = btn.getBoundingClientRect();
    pill.style.left = `${btnRect.left - navRect.left}px`;
    pill.style.width = `${btnRect.width}px`;
  };

  useLayoutEffect(() => {
    updatePill(activeTab);
    setPillReady(true);
    const onResize = (): void => updatePill(activeTab);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]);

  // Fonts load async and shift widths; re-measure once they settle.
  useLayoutEffect(() => {
    if (typeof document === 'undefined' || !('fonts' in document)) return;
    document.fonts.ready.then(() => updatePill(activeTab)).catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLButtonElement>, idx: number): void => {
    if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
    e.preventDefault();
    const next =
      e.key === 'ArrowRight'
        ? (idx + 1) % TAB_ITEMS.length
        : (idx - 1 + TAB_ITEMS.length) % TAB_ITEMS.length;
    const nextTab = TAB_ITEMS[next];
    onTabChange(nextTab.id);
    tabRefs.current.get(nextTab.id)?.focus();
  };

  return (
    <header className="sticky top-0 z-40 border-b border-surface-border bg-background/95 backdrop-blur px-5 lg:px-8 py-3.5">
      <div className="max-w-[1600px] mx-auto flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="flex items-center gap-3.5">
          <div className="w-8 h-8 rounded-lg bg-primary/10 border border-primary/30 flex items-center justify-center text-primary-light font-mono shadow-sm shrink-0">
            <Sparkles className="size-4.5" />
          </div>
          <div>
            <div className="flex items-center gap-2.5 flex-wrap">
              <h1 className="text-sm md:text-base font-semibold tracking-tight text-white leading-none">
                Antigravity Savings Dashboard
              </h1>
              <span className="px-2 py-0.5 rounded text-[11px] font-mono tracking-wider bg-surface text-primary-light border border-surface-border">
                ICM vs. Baseline A/B
              </span>
            </div>
            <p className="text-[12px] text-muted-foreground font-mono mt-1 flex items-center flex-wrap gap-1.5">
              <span>Interpretable Context Methodology (ICM) Token &amp; Cache Efficiency Engine</span>
              <span className="hidden sm:inline">•</span>
              {data?.is_demo_report || !data?.cumulative?.has_measured_data ? (
                <span
                  data-testid="demo-fixture-badge"
                  className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30 text-[11px] font-semibold"
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                  DEMO / FIXTURE DATA (Empirical Headlines Suppressed)
                </span>
              ) : data?.is_simulation ? (
                <span
                  data-testid="simulation-active-badge"
                  className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-purple-500/10 text-purple-300 border border-purple-500/30 text-[11px] font-semibold"
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-purple-400" />
                  SIMULATION ACTIVE
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 px-1.5 py-0.5 rounded bg-sage/10 text-sage border border-sage/30 text-[11px]">
                  <span className="w-1.5 h-1.5 rounded-full bg-sage" />
                  Measured Actuals (Zero Hallucinated Projections)
                </span>
              )}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 self-end md:self-auto">
          {data && (
            <div
              title="Recorded Rows: total ledger rows. Evaluated Tasks: distinct tasks with valid evaluations. Measured Comparisons: strictly paired runs with verified empirical telemetry."
              className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface border border-surface-border text-xs font-mono text-muted-foreground"
            >
              <Database className="size-3.5 text-primary" />
              <span className="text-foreground">{data.runs.length} Rows</span>
              <span className="text-surface-border">•</span>
              <span>{data.cumulative.tasks_evaluated} Tasks</span>
              <span className="text-surface-border">•</span>
              <span className={data.cumulative.has_measured_data ? 'text-sage font-medium' : 'text-amber-400'}>
                {data.cumulative.comparison_eligible_runs_count || 0} Measured
              </span>
            </div>
          )}
          <a
            href={getPublicUrl('visual_showcase_2.html')}
            target="_blank"
            rel="noreferrer"
            aria-label="Open 3-Arena Interactive Showcase"
            className={buttonVariants({
              variant: 'outline',
              size: 'sm',
              className: 'gap-1.5 text-xs text-indigo-300 border-indigo-500/30 hover:bg-indigo-950/40 hover:text-white',
            })}
          >
            <Sparkles className="size-3.5 text-indigo-400" />
            <span>3-Arena Showcase ↗</span>
          </a>
          <a
            href={getPublicUrl('data.json')}
            download="antigravity_usage_data.json"
            aria-label="Download usage ledger as JSON"
            className={buttonVariants({
              variant: 'outline',
              size: 'sm',
              className: 'gap-1.5 text-xs text-muted-foreground hover:text-white border-surface-border',
            })}
          >
            <Download className="size-3.5" />
            <span>Export JSON</span>
          </a>
          <Button
            onClick={onRefresh}
            disabled={loading}
            variant="outline"
            size="sm"
            aria-label="Refresh usage data from server"
            className="bg-primary/20 text-primary-light border-primary/30 hover:bg-primary/30 hover:text-white gap-1.5"
            title="Reload static data.json"
          >
            <RefreshCw className={cn('size-3.5', loading && 'animate-spin')} />
            <span>Refresh</span>
          </Button>
        </div>
      </div>

      <nav
        ref={navRef}
        aria-label="Dashboard sections"
        className="relative inline-flex items-center p-1 rounded-lg bg-surface border border-surface-border mt-3 overflow-x-auto max-w-full"
      >
        <div
          ref={pillRef}
          aria-hidden="true"
          className={cn(
            'absolute h-[calc(100%-8px)] top-1 rounded-md bg-card border border-input shadow-sm transition-[left,width] duration-300 ease-out pointer-events-none',
            !pillReady && 'opacity-0'
          )}
          style={{ left: 4, width: 0 }}
        />
        {TAB_ITEMS.map((tab, idx) => (
          <button
            key={tab.id}
            ref={(el) => {
              if (el) tabRefs.current.set(tab.id, el);
            }}
            type="button"
            role="tab"
            id={`tab-${tab.id}`}
            aria-selected={activeTab === tab.id}
            aria-controls={`panel-${tab.id}`}
            tabIndex={activeTab === tab.id ? 0 : -1}
            onClick={() => onTabChange(tab.id)}
            onKeyDown={(e) => handleKeyDown(e, idx)}
            className={cn(
              'relative z-10 whitespace-nowrap inline-flex items-center gap-2 px-3.5 py-1.5 rounded-md text-xs font-semibold tracking-wide transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
              activeTab === tab.id ? 'text-white' : 'text-muted-foreground hover:text-white'
            )}
          >
            {tab.label}
          </button>
        ))}
      </nav>
      <span className="sr-only">
        <ShieldCheck />
        {data?.is_demo_report || !data?.cumulative?.has_measured_data
          ? 'Dashboard displaying synthetic fixtures or dry-run replayed telemetry. Empirical headline metrics are suppressed.'
          : data?.is_simulation
          ? 'Simulation active with rate-card model projections.'
          : 'Benchmark data sourced from measured ledger actuals.'}
      </span>
    </header>
  );
};
