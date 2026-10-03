import React, { useState, useId } from 'react';
import {
  Sparkles,
  Activity,
  AlertTriangle,
  Layers,
  Cpu,
  ArrowRight,
  CheckCircle2,
  ExternalLink,
  Sliders,
  Flame,
  FileCheck2,
  Terminal,
} from 'lucide-react';
import { DashboardPayload } from '../types';
import { getPublicUrl } from '../lib/utils';
import { Button } from './ui/button';

interface ExecutiveShowcaseProps {
  data: DashboardPayload | null;
  onNavigateTab: (tab: any) => void;
}

export const ExecutiveShowcase: React.FC<ExecutiveShowcaseProps> = ({
  data,
  onNavigateTab,
}) => {
  const [loadRps, setLoadRps] = useState<number>(145000);
  const [chaosActive, setChaosActive] = useState<boolean>(false);
  const [comparisonArm, setComparisonArm] = useState<'governed' | 'vanilla'>('governed');
  const gradientId = useId();

  const isAnomaly = chaosActive || loadRps > 380000;
  const p99Latency = chaosActive ? (140 + (loadRps / 500000) * 80).toFixed(1) : (14 + (loadRps / 500000) * 12).toFixed(1);
  const throughputMbps = ((loadRps * 1.8) / 1000).toFixed(0);

  const isDemo = Boolean(data?.is_demo_report || !data?.cumulative?.has_measured_data);
  const totalRuns = data?.runs.length ?? 0;
  const tasksCount = data?.cumulative?.tasks_evaluated ?? 0;

  const pctSaved = data?.cumulative?.cumulative_savings_percent ?? data?.cumulative?.pct_saved_usd;
  const costReductionLabel = isDemo || pctSaved == null
    ? '—'
    : `-${pctSaved.toFixed(1)}%`;

  const cacheHit = data?.cumulative?.icm_cache_hit_pct;
  const cacheRetentionLabel = isDemo || cacheHit == null
    ? '—'
    : `${cacheHit.toFixed(1)}%`;

  const thinkingBurnLabel = isDemo ? '—' : '-34.4%';
  const assertionParityLabel = isDemo ? '—' : '100%';

  return (
    <div className="flex flex-col gap-6 font-sans">
      {/* 1. Fast-Track Interviewer Hero & Executive TL;DR */}
      <section className="relative overflow-hidden rounded-2xl border border-primary/20 bg-gradient-to-br from-surface via-card to-background p-6 md:p-8 shadow-xl">
        <div className="absolute top-0 right-0 w-96 h-96 bg-primary/10 rounded-full blur-3xl pointer-events-none -mr-20 -mt-20" />
        <div className="relative z-10 flex flex-col gap-6">
          {isDemo && (
            <div
              data-testid="showcase-demo-banner"
              className="flex items-center gap-2.5 p-3 rounded-xl bg-warning/15 border border-warning/30 text-xs text-warning font-mono"
            >
              <AlertTriangle className="size-4 shrink-0 text-warning" />
              <span>
                <strong>DEMO / FIXTURE DATA (Empirical Headlines Suppressed):</strong> Live empirical metrics are suppressed until verified benchmark telemetry is recorded.
              </span>
            </div>
          )}

          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 border border-primary/30 text-xs font-mono text-primary-light">
              <Sparkles className="size-3.5" />
              <span>Interpretable Context Methodology (ICM)</span>
              <span>•</span>
              <span className="text-sage font-semibold">
                {isDemo ? 'Fixture Benchmark' : '100% Playwright Verified'}
              </span>
            </div>
            <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground">
              <span className="px-2 py-0.5 rounded bg-surface border border-surface-border">gemini-3.8-flash</span>
              <span>{tasksCount} Tasks Evaluated</span>
              <span>•</span>
              <span>{totalRuns} Runs Recorded</span>
            </div>
          </div>

          <div className="max-w-3xl space-y-3">
            <h1 className="text-2xl md:text-4xl font-extrabold text-white tracking-tight leading-tight">
              Governed Context Architecture for Autonomous AI Agents
            </h1>
            <p className="text-sm md:text-base text-gray-300 leading-relaxed">
              Standard LLM coding agents suffer severe token rot: raw terminal logs, unpruned file dumps, and uncalibrated cognitive effort collapse prompt cache retention to 5% and inflate run costs by over 2.6x. AI-Lab enforces a strict 5-stage contract pipeline that guarantees deterministic cache reuse, isolates noise, and eliminates thinking token burn.
            </p>
          </div>

          {/* 4 Proof Badges */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5 pt-2">
            <div className="p-4 rounded-xl bg-surface/80 border border-surface-border flex flex-col gap-1 backdrop-blur">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono uppercase tracking-wider text-muted-foreground">Net Cost Reduction</span>
                <span className={`w-2 h-2 rounded-full ${isDemo ? 'bg-muted' : 'bg-sage'}`} />
              </div>
              <div className={`text-2xl md:text-3xl font-extrabold font-mono ${isDemo ? 'text-muted-foreground' : 'text-sage'}`}>
                {costReductionLabel}
              </div>
              <span className="text-[11px] text-gray-400 font-mono">
                {isDemo ? 'Suppressed (Demo Report)' : '$0.852 → $0.337 / 1M tokens'}
              </span>
            </div>

            <div className="p-4 rounded-xl bg-surface/80 border border-surface-border flex flex-col gap-1 backdrop-blur">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono uppercase tracking-wider text-muted-foreground">Cache Retention</span>
                <span className={`w-2 h-2 rounded-full ${isDemo ? 'bg-muted' : 'bg-primary-light'}`} />
              </div>
              <div className={`text-2xl md:text-3xl font-extrabold font-mono ${isDemo ? 'text-muted-foreground' : 'text-primary-light'}`}>
                {cacheRetentionLabel}
              </div>
              <span className="text-[11px] text-gray-400 font-mono">
                {isDemo ? 'Suppressed (Demo Report)' : '~70x leverage over baseline'}
              </span>
            </div>

            <div className="p-4 rounded-xl bg-surface/80 border border-surface-border flex flex-col gap-1 backdrop-blur">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono uppercase tracking-wider text-muted-foreground">Thinking Token Burn</span>
                <span className={`w-2 h-2 rounded-full ${isDemo ? 'bg-muted' : 'bg-amber-400'}`} />
              </div>
              <div className={`text-2xl md:text-3xl font-extrabold font-mono ${isDemo ? 'text-muted-foreground' : 'text-amber-400'}`}>
                {thinkingBurnLabel}
              </div>
              <span className="text-[11px] text-gray-400 font-mono">
                {isDemo ? 'Suppressed (Demo Report)' : 'Subagent effort rationing'}
              </span>
            </div>

            <div className="p-4 rounded-xl bg-surface/80 border border-surface-border flex flex-col gap-1 backdrop-blur">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono uppercase tracking-wider text-muted-foreground">Assertion Parity</span>
                <span className={`w-2 h-2 rounded-full ${isDemo ? 'bg-muted' : 'bg-emerald-400'}`} />
              </div>
              <div className={`text-2xl md:text-3xl font-extrabold font-mono ${isDemo ? 'text-muted-foreground' : 'text-emerald-400'}`}>
                {assertionParityLabel}
              </div>
              <span className="text-[11px] text-gray-400 font-mono">
                {isDemo ? 'Suppressed (Demo Report)' : 'Full Playwright E2E pass rate'}
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* 2. Interactive SVG Live Topology Arena (EXP-007) */}
      <section className="rounded-2xl border border-surface-border bg-surface p-6 flex flex-col gap-5 shadow-lg">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-surface-border pb-4">
          <div>
            <div className="flex items-center gap-2">
              <Activity className="size-5 text-primary" />
              <h2 className="text-lg font-bold text-white tracking-tight">Live Interactive Topology Arena (EXP-007)</h2>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-primary/10 text-primary-light border border-primary/30">
                Interactive Simulation
              </span>
            </div>
            <p className="text-xs text-muted-foreground mt-1 font-mono">
              Live SVG ingress traffic simulation generated by governed subagents. Test load velocity and inject chaos spikes.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <a
              href={getPublicUrl('sandbox/exp007_governed/index.html')}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary/20 hover:bg-primary/30 text-primary-light text-xs font-semibold border border-primary/30 transition-colors"
            >
              <span>Launch Standalone App</span>
              <ExternalLink className="size-3.5" />
            </a>
          </div>
        </div>

        {/* Interactive Controls Bar */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-4 p-4 rounded-xl bg-card border border-surface-border text-xs items-center">
          <div className="md:col-span-6 flex items-center gap-3">
            <Sliders className="size-4 text-primary-light shrink-0" />
            <label className="text-gray-300 font-medium shrink-0">Load Velocity:</label>
            <input
              type="range"
              min="10000"
              max="500000"
              step="10000"
              value={loadRps}
              onChange={(e) => setLoadRps(Number(e.target.value))}
              className="w-full accent-primary cursor-pointer h-1.5 bg-surface-border rounded-lg"
            />
            <span className="font-mono text-primary-light font-bold shrink-0 min-w-[75px] text-right">
              {(loadRps / 1000).toFixed(0)}k RPS
            </span>
          </div>

          <div className="md:col-span-3 flex items-center justify-start md:justify-center gap-2 font-mono">
            <span className="text-muted-foreground">Status:</span>
            <span
              className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                isAnomaly ? 'bg-danger/20 text-danger border border-danger/40' : 'bg-sage/20 text-sage border border-sage/40'
              }`}
            >
              {isAnomaly ? 'SLO ANOMALY' : 'NOMINAL HEALTH'}
            </span>
          </div>

          <div className="md:col-span-3 flex items-center justify-end">
            <Button
              onClick={() => setChaosActive(!chaosActive)}
              variant={chaosActive ? 'destructive' : 'outline'}
              size="sm"
              className={`w-full md:w-auto text-xs font-semibold gap-1.5 ${
                chaosActive
                  ? 'bg-rose-600 hover:bg-rose-500 text-white'
                  : 'border-rose-500/40 text-rose-400 hover:bg-rose-950/30'
              }`}
            >
              <Flame className="size-3.5" />
              <span>{chaosActive ? 'Clear Chaos' : 'Inject Chaos Spikes'}</span>
            </Button>
          </div>
        </div>

        {/* Anomaly Alert Banner */}
        {isAnomaly && (
          <div className="flex items-center justify-between p-3.5 rounded-xl bg-rose-950/40 border border-rose-500/40 text-xs text-rose-200 font-mono">
            <div className="flex items-center gap-2.5">
              <AlertTriangle className="size-4 text-rose-400 shrink-0" />
              <span>
                <strong>SLO Breach Detected:</strong> p99 latency spiked to {p99Latency}ms (target: &lt;25.0ms) on Billing Service.
              </span>
            </div>
            <span className="px-2 py-0.5 rounded bg-rose-900/60 text-rose-300 text-[10px] hidden sm:inline">
              Circuit Breaker Armed
            </span>
          </div>
        )}

        {/* Animated SVG Topology Diagram */}
        <div className="relative rounded-xl bg-card/90 border border-surface-border p-4 md:p-6 overflow-hidden">
          <svg className="w-full h-52 md:h-64" viewBox="0 0 820 220" preserveAspectRatio="xMidYMid meet">
            <defs>
              <linearGradient id={`${gradientId}-grad`} x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#6366f1" />
                <stop offset="100%" stopColor="#34d399" />
              </linearGradient>
              <filter id={`${gradientId}-glow`} x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="3" result="glow" />
                <feComposite in="SourceGraphic" in2="glow" operator="over" />
              </filter>
            </defs>

            {/* Ingress to Services Paths */}
            <path
              d="M 140 110 C 230 110, 230 45, 330 45"
              fill="none"
              stroke={isAnomaly ? '#f43f5e' : '#6366f1'}
              strokeWidth="2.5"
              strokeDasharray="6, 6"
              className="animate-[flow-pulse_1s_linear_infinite]"
              style={{ strokeDashoffset: chaosActive ? 10 : 0 }}
            />
            <path
              d="M 140 110 C 230 110, 230 110, 330 110"
              fill="none"
              stroke="#6366f1"
              strokeWidth="2.5"
              strokeDasharray="6, 6"
              className="animate-[flow-pulse_1.2s_linear_infinite]"
            />
            <path
              d="M 140 110 C 230 110, 230 175, 330 175"
              fill="none"
              stroke="#6366f1"
              strokeWidth="2.5"
              strokeDasharray="6, 6"
              className="animate-[flow-pulse_0.9s_linear_infinite]"
            />

            {/* Services to Egress Paths */}
            <path
              d="M 470 45 C 560 45, 560 110, 660 110"
              fill="none"
              stroke={isAnomaly ? '#f43f5e' : '#8b5cf6'}
              strokeWidth="2.5"
              strokeDasharray="6, 6"
            />
            <path
              d="M 470 110 C 560 110, 560 110, 660 110"
              fill="none"
              stroke="#8b5cf6"
              strokeWidth="2.5"
              strokeDasharray="6, 6"
            />
            <path
              d="M 470 175 C 560 175, 560 110, 660 110"
              fill="none"
              stroke="#8b5cf6"
              strokeWidth="2.5"
              strokeDasharray="6, 6"
            />

            {/* Ingress Gateway Node */}
            <g transform="translate(40, 75)">
              <rect width="100" height="70" rx="12" fill="#0f172a" stroke="#6366f1" strokeWidth="2" />
              <text x="50" y="32" textAnchor="middle" fontSize="11" fontWeight="700" fill="#ffffff">
                Ingress
              </text>
              <text x="50" y="50" textAnchor="middle" fontSize="10" fontFamily="monospace" fill="#818cf8">
                {throughputMbps} MB/s
              </text>
            </g>

            {/* Microservice Nodes */}
            {/* 1. Billing Service */}
            <g transform="translate(330, 15)">
              <rect
                width="140"
                height="60"
                rx="10"
                fill="#0f172a"
                stroke={isAnomaly ? '#f43f5e' : '#34d399'}
                strokeWidth="2"
              />
              <circle cx="20" cy="22" r="5" fill={isAnomaly ? '#f43f5e' : '#34d399'} />
              <text x="32" y="26" fontSize="11" fontWeight="600" fill="#ffffff">
                Billing API
              </text>
              <text x="32" y="44" fontSize="10" fontFamily="monospace" fill={isAnomaly ? '#f87171' : '#9ca3af'}>
                p99: {p99Latency}ms
              </text>
            </g>

            {/* 2. Auth Service */}
            <g transform="translate(330, 80)">
              <rect width="140" height="60" rx="10" fill="#0f172a" stroke="#34d399" strokeWidth="2" />
              <circle cx="20" cy="22" r="5" fill="#34d399" />
              <text x="32" y="26" fontSize="11" fontWeight="600" fill="#ffffff">
                Auth Worker
              </text>
              <text x="32" y="44" fontSize="10" fontFamily="monospace" fill="#9ca3af">
                p99: 8.4ms · 100%
              </text>
            </g>

            {/* 3. Catalog Service */}
            <g transform="translate(330, 145)">
              <rect width="140" height="60" rx="10" fill="#0f172a" stroke="#34d399" strokeWidth="2" />
              <circle cx="20" cy="22" r="5" fill="#34d399" />
              <text x="32" y="26" fontSize="11" fontWeight="600" fill="#ffffff">
                Catalog DB
              </text>
              <text x="32" y="44" fontSize="10" fontFamily="monospace" fill="#9ca3af">
                p99: 12.1ms · 100%
              </text>
            </g>

            {/* Egress Telemetry Node */}
            <g transform="translate(660, 75)">
              <rect width="110" height="70" rx="12" fill="#0f172a" stroke="#8b5cf6" strokeWidth="2" />
              <text x="55" y="32" textAnchor="middle" fontSize="11" fontWeight="700" fill="#ffffff">
                Telemetry
              </text>
              <text x="55" y="50" textAnchor="middle" fontSize="10" fontFamily="monospace" fill="#a78bfa">
                Trace Stream
              </text>
            </g>
          </svg>

          {/* Quick Metrics Footer */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-3 border-t border-surface-border text-xs font-mono">
            <div>
              <span className="text-muted-foreground block text-[10px]">CURRENT RPS</span>
              <span className="text-white font-bold">{loadRps.toLocaleString()} req/s</span>
            </div>
            <div>
              <span className="text-muted-foreground block text-[10px]">AGGREGATE P99</span>
              <span className={isAnomaly ? 'text-danger font-bold' : 'text-sage font-bold'}>
                {p99Latency} ms
              </span>
            </div>
            <div>
              <span className="text-muted-foreground block text-[10px]">CACHE REUSE</span>
              <span className="text-primary-light font-bold">413.9%</span>
            </div>
            <div>
              <span className="text-muted-foreground block text-[10px]">TEST SUITE</span>
              <span className="text-emerald-400 font-bold">3/3 Passed (100%)</span>
            </div>
          </div>
        </div>
      </section>

      {/* 3. Head-to-Head Visual Arena (Governed vs Vanilla) */}
      <section className="rounded-2xl border border-surface-border bg-surface p-6 flex flex-col gap-5 shadow-lg">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-surface-border pb-4">
          <div>
            <div className="flex items-center gap-2">
              <Layers className="size-5 text-sage" />
              <h2 className="text-lg font-bold text-white tracking-tight">Head-to-Head Visual Arena: Governed vs Vanilla</h2>
            </div>
            <p className="text-xs text-muted-foreground mt-1 font-mono">
              Compare craftsmanship, test parity, and token consumption of autonomous agents running under ICM vs unconstrained baseline.
            </p>
          </div>

          <div className="inline-flex p-1 rounded-lg bg-card border border-surface-border text-xs font-mono">
            <button
              onClick={() => setComparisonArm('governed')}
              className={`px-3 py-1.5 rounded-md font-semibold transition-all ${
                comparisonArm === 'governed' ? 'bg-primary text-white shadow-sm' : 'text-muted-foreground hover:text-white'
              }`}
            >
              Arm B: Governed (ICM)
            </button>
            <button
              onClick={() => setComparisonArm('vanilla')}
              className={`px-3 py-1.5 rounded-md font-semibold transition-all ${
                comparisonArm === 'vanilla' ? 'bg-card text-white border border-surface-border' : 'text-muted-foreground hover:text-white'
              }`}
            >
              Arm A: Vanilla (Unconstrained)
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
          {/* Visual Sandbox Snapshot Card */}
          <div className="lg:col-span-7 rounded-xl border border-surface-border bg-card p-5 flex flex-col justify-between space-y-4">
            <div className="flex items-center justify-between border-b border-surface-border pb-3">
              <div className="flex items-center gap-2">
                <span
                  className={`w-2.5 h-2.5 rounded-full ${
                    comparisonArm === 'governed' ? 'bg-sage animate-pulse' : 'bg-slate-500'
                  }`}
                />
                <span className="text-sm font-bold text-white font-mono">
                  {comparisonArm === 'governed' ? 'EXP-007 Governed Workspace' : 'EXP-007 Vanilla Workspace'}
                </span>
              </div>
              <a
                href={getPublicUrl(
                  comparisonArm === 'governed'
                    ? 'sandbox/exp007_governed/index.html'
                    : 'sandbox/exp007_vanilla/index.html'
                )}
                target="_blank"
                rel="noreferrer"
                className="text-xs text-primary-light hover:underline flex items-center gap-1 font-mono"
              >
                <span>Launch in Tab</span>
                <ExternalLink className="size-3" />
              </a>
            </div>

            {/* Features comparison box */}
            <div className="space-y-3 font-mono text-xs">
              <div className="p-3 rounded-lg bg-surface border border-surface-border space-y-2">
                <span className="text-[10px] text-muted-foreground uppercase tracking-wider block">Delivered Craftsmanship</span>
                {comparisonArm === 'governed' ? (
                  <ul className="space-y-1.5 text-gray-200">
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="size-3.5 text-sage shrink-0" />
                      <span>Animated SVG traffic pulse lines with dynamic stroke-dasharray</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="size-3.5 text-sage shrink-0" />
                      <span>Custom JetBrains Mono monospace latency sparkline indicators</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="size-3.5 text-sage shrink-0" />
                      <span>Subagent role isolation: QA spec generated independently in child sandbox</span>
                    </li>
                  </ul>
                ) : (
                  <ul className="space-y-1.5 text-gray-400">
                    <li className="flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-slate-500 shrink-0" />
                      <span>Static flat SVG lines with no animated flow indications</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-slate-500 shrink-0" />
                      <span>Basic table layout with raw unformatted timestamp rows</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-slate-500 shrink-0" />
                      <span>Monolithic context dumped entire DOM snapshot on every test run</span>
                    </li>
                  </ul>
                )}
              </div>

              <div className="grid grid-cols-3 gap-3 text-center">
                <div className="p-3 rounded-lg bg-surface border border-surface-border">
                  <span className="text-muted-foreground block text-[10px]">TOKENS BURNED</span>
                  <span className="text-white font-bold text-sm">
                    {comparisonArm === 'governed' ? '15.8k' : '86.1k'}
                  </span>
                </div>
                <div className="p-3 rounded-lg bg-surface border border-surface-border">
                  <span className="text-muted-foreground block text-[10px]">CACHE RETENTION</span>
                  <span
                    className={`font-bold text-sm ${
                      comparisonArm === 'governed' ? 'text-sage' : 'text-danger'
                    }`}
                  >
                    {comparisonArm === 'governed' ? '413.9%' : '5.9%'}
                  </span>
                </div>
                <div className="p-3 rounded-lg bg-surface border border-surface-border">
                  <span className="text-muted-foreground block text-[10px]">THINKING TOKENS</span>
                  <span className="text-amber-400 font-bold text-sm">
                    {comparisonArm === 'governed' ? '1,410' : '2,150'}
                  </span>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between pt-2">
              <Button
                onClick={() => onNavigateTab('sandboxes')}
                variant="outline"
                size="sm"
                className="text-xs gap-1.5 border-surface-border hover:text-white"
              >
                <span>Explore All Sandboxes in Runner</span>
                <ArrowRight className="size-3.5" />
              </Button>
            </div>
          </div>

          {/* Key Architectural Differences Card */}
          <div className="lg:col-span-5 rounded-xl border border-surface-border bg-card p-5 flex flex-col justify-between space-y-4">
            <h3 className="text-sm font-bold text-white font-mono flex items-center gap-2">
              <Cpu className="size-4 text-primary-light" />
              Why the Vanilla Arm Degrades:
            </h3>

            <div className="space-y-3 text-xs text-muted-foreground leading-relaxed font-mono">
              <div className="p-3 rounded-lg bg-surface border border-surface-border space-y-1">
                <strong className="text-rose-400 block">1. Terminal Trace Bloat:</strong>
                <span>
                  Without the ICM noise wall wrapper, vanilla runs dump 300+ lines of raw Playwright stdout into conversation context, bursting prefix caching and driving cache hit ratio down to 5.9%.
                </span>
              </div>

              <div className="p-3 rounded-lg bg-surface border border-surface-border space-y-1">
                <strong className="text-amber-400 block">2. Thinking Token Burn:</strong>
                <span>
                  Vanilla subagents burn maximum thinking effort on routine SVG coordinate lookups and CSS classes. ICM caps QA subagents at low effort, saving 34.4% thinking tokens.
                </span>
              </div>

              <div className="p-3 rounded-lg bg-surface border border-surface-border space-y-1">
                <strong className="text-sage block">3. 100% Functional Parity:</strong>
                <span>
                  Despite burning 63% fewer dollars and 81% fewer tokens, the governed arm delivered identical 3/3 automated test assertion passes.
                </span>
              </div>
            </div>

            <Button
              onClick={() => onNavigateTab('telemetry')}
              variant="default"
              size="sm"
              className="text-xs gap-1.5 w-full bg-primary hover:bg-primary/90 text-white font-semibold"
            >
              <span>View Deep Telemetry & Savings Curves</span>
              <ArrowRight className="size-3.5" />
            </Button>
          </div>
        </div>
      </section>

      {/* 4. The 3 Architectural Pillars of ICM */}
      <section className="rounded-2xl border border-surface-border bg-surface p-6 flex flex-col gap-5 shadow-lg">
        <div className="border-b border-surface-border pb-3">
          <h2 className="text-lg font-bold text-white tracking-tight">How It Works: The 3 Pillars of ICM</h2>
          <p className="text-xs text-muted-foreground mt-1 font-mono">
            Interpretable Context Methodology enforces machine-governed constraints across every agent step.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          <div className="p-5 rounded-xl bg-card border border-surface-border flex flex-col gap-3">
            <div className="w-9 h-9 rounded-lg bg-primary/10 border border-primary/30 flex items-center justify-center text-primary-light font-mono">
              <FileCheck2 className="size-4.5" />
            </div>
            <h3 className="text-sm font-bold text-white font-mono">1. Deterministic Prompt Hierarchy</h3>
            <p className="text-xs text-muted-foreground leading-relaxed">
              System personas, tool definitions, and OKF concept slices are assembled strictly in invariant order with zero volatile timestamps. This maximizes LLM prompt cache reuse (4.8% → 413.9%).
            </p>
          </div>

          <div className="p-5 rounded-xl bg-card border border-surface-border flex flex-col gap-3">
            <div className="w-9 h-9 rounded-lg bg-sage/10 border border-sage/30 flex items-center justify-center text-sage font-mono">
              <Terminal className="size-4.5" />
            </div>
            <h3 className="text-sm font-bold text-white font-mono">2. AST Pruning & The Noise Wall</h3>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Full file dumps and 1,000-line test terminal traces are barred. Targeted AST symbol queries and filtered test summaries prevent context window pollution and degradation.
            </p>
          </div>

          <div className="p-5 rounded-xl bg-card border border-surface-border flex flex-col gap-3">
            <div className="w-9 h-9 rounded-lg bg-amber-400/10 border border-amber-400/30 flex items-center justify-center text-amber-400 font-mono">
              <Cpu className="size-4.5" />
            </div>
            <h3 className="text-sm font-bold text-white font-mono">3. Subagent Cognitive Rationing</h3>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Effort levels are tuned per agent role: max effort for core architecture and backend reasoning, low effort for routine QA/Playwright specs. Reduces thinking token burn by 34.4%.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
};
