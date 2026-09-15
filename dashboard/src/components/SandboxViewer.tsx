import React, { useState } from 'react';
import {
  Layers,
  ExternalLink,
  CheckCircle2,
  Maximize2,
  RefreshCw,
  Sparkles,
  Info,
} from 'lucide-react';
import { getPublicUrl } from '../lib/utils';
import { Button } from './ui/button';

interface SandboxOption {
  id: string;
  title: string;
  category: string;
  governedPath: string;
  vanillaPath?: string;
  description: string;
  assertions: string;
  highlights: string[];
}

const SANDBOXES: SandboxOption[] = [
  {
    id: 'exp007-topology',
    title: 'EXP-007: API Gateway Topology Simulator',
    category: 'Microservices & Telemetry',
    governedPath: 'sandbox/exp007_governed/index.html',
    vanillaPath: 'sandbox/exp007_vanilla/index.html',
    description:
      'Real-time SVG ingress topology with load velocity sliders, animated packet flow, sparkline telemetry, and chaos injection triggers.',
    assertions: '3/3 Playwright Assertions Passed (100% Functional Parity)',
    highlights: [
      'Interactive SVG flow paths with dynamic stroke-dasharray animation',
      'Live chaos spike injection with dynamic p99 latency SLO alert banner',
      'Telemetry trace drawer with raw timing logs and machine receipts',
    ],
  },
  {
    id: 'exp008-interview',
    title: 'EXP-008: ResumeForge Grounded Interview System',
    category: 'Full-Stack Agent Workspace',
    governedPath: 'sandbox/exp008_governed/index.html',
    vanillaPath: 'sandbox/exp008_vanilla/index.html',
    description:
      'Evidence-grounded, multi-turn technical interview console with real-time 4-axis rubric scoring, evidence citation mapping, and scorecard modal.',
    assertions: 'Multi-turn dialog & evidence grounding verified',
    highlights: [
      'Split-console interview layout with question stream and timer readout',
      'Real-time evidence inspector displaying targeted evidence spans',
      'Accessible dialog scorecard displaying 4-axis rubric breakdown',
    ],
  },
  {
    id: 'showcase-3arena',
    title: '3-Arena Interactive Portfolio Exhibition',
    category: 'Interactive Suite',
    governedPath: 'visual_showcase_2.html',
    description:
      'Comprehensive 3-Arena interactive portfolio showcasing live SVG topology, head-to-head split view, and auditable token telemetry.',
    assertions: 'Comprehensive Interactive Exhibition',
    highlights: [
      'Section 01: Live SVG Ingress Gateway Topology with Load Slider',
      'Section 02: Head-to-Head Split-Screen Visual Arena',
      'Section 03: Telemetry Receipts Drawer with thinking token audit',
    ],
  },
  {
    id: 'exp005-landing',
    title: 'EXP-005: SaaS High-Conversion Landing Page',
    category: 'Frontend UI',
    governedPath: 'sandbox/governed/index.html',
    vanillaPath: 'sandbox/vanilla/index.html',
    description:
      'Modern dark glassmorphism SaaS landing page generated with zero ICM defects vs 2 baseline functional bugs.',
    assertions: 'Visual layout & interactive components verified',
    highlights: [
      'Dark glassmorphism card elevation with responsive flex grids',
      'Animated hero badge and interactive pricing tier cards',
      'Zero layout shift or DOM errors in governed output',
    ],
  },
];

export const SandboxViewer: React.FC = () => {
  const [selectedId, setSelectedId] = useState<string>(SANDBOXES[0].id);
  const [selectedArm, setSelectedArm] = useState<'governed' | 'vanilla'>('governed');
  const [iframeKey, setIframeKey] = useState<number>(0);

  const current = SANDBOXES.find((s) => s.id === selectedId) ?? SANDBOXES[0];
  const activePath =
    selectedArm === 'vanilla' && current.vanillaPath
      ? current.vanillaPath
      : current.governedPath;

  const resolvedUrl = getPublicUrl(activePath);

  return (
    <div className="flex flex-col gap-6 font-sans">
      {/* Header Bar */}
      <div className="rounded-2xl border border-surface-border bg-surface p-6 flex flex-col gap-4 shadow-lg">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-surface-border pb-4">
          <div>
            <div className="flex items-center gap-2">
              <Layers className="size-5 text-primary-light" />
              <h1 className="text-xl font-bold text-white tracking-tight">Interactive Sandbox Runner</h1>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-sage/10 text-sage border border-sage/30">
                Live In-Dashboard Previews
              </span>
            </div>
            <p className="text-xs text-muted-foreground mt-1 font-mono">
              Directly interact with the artifacts and user interfaces built by autonomous agents under ICM governance.
            </p>
          </div>

          {/* Quick Actions */}
          <div className="flex items-center gap-2">
            <Button
              onClick={() => setIframeKey((k) => k + 1)}
              variant="outline"
              size="sm"
              className="text-xs font-mono gap-1.5 border-surface-border hover:text-white"
              title="Reload sandbox iframe"
            >
              <RefreshCw className="size-3.5" />
              <span>Reload Sandbox</span>
            </Button>

            <a
              href={resolvedUrl}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary hover:bg-primary/90 text-white text-xs font-semibold shadow-sm transition-colors"
            >
              <span>Open Standalone Tab</span>
              <Maximize2 className="size-3.5" />
            </a>
          </div>
        </div>

        {/* Sandbox Selection Pills & Arm Switcher */}
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
          <div className="flex items-center gap-2 overflow-x-auto max-w-full pb-1">
            {SANDBOXES.map((s) => (
              <button
                key={s.id}
                onClick={() => {
                  setSelectedId(s.id);
                  setIframeKey((k) => k + 1);
                }}
                className={`px-3.5 py-2 rounded-xl text-xs font-semibold whitespace-nowrap transition-all flex items-center gap-2 ${
                  selectedId === s.id
                    ? 'bg-primary text-white shadow-md shadow-primary/20'
                    : 'bg-card border border-surface-border text-muted-foreground hover:text-white'
                }`}
              >
                <span>{s.title.split(':')[0]}</span>
                <span className="text-[10px] opacity-75 font-mono">({s.category})</span>
              </button>
            ))}
          </div>

          {current.vanillaPath && (
            <div className="inline-flex p-1 rounded-lg bg-card border border-surface-border text-xs font-mono shrink-0">
              <button
                onClick={() => {
                  setSelectedArm('governed');
                  setIframeKey((k) => k + 1);
                }}
                className={`px-3 py-1 rounded-md font-semibold transition-all ${
                  selectedArm === 'governed'
                    ? 'bg-sage text-black font-bold'
                    : 'text-muted-foreground hover:text-white'
                }`}
              >
                Governed (ICM)
              </button>
              <button
                onClick={() => {
                  setSelectedArm('vanilla');
                  setIframeKey((k) => k + 1);
                }}
                className={`px-3 py-1 rounded-md font-semibold transition-all ${
                  selectedArm === 'vanilla'
                    ? 'bg-surface text-white border border-surface-border'
                    : 'text-muted-foreground hover:text-white'
                }`}
              >
                Vanilla (Baseline)
              </button>
            </div>
          )}
        </div>

        {/* Selected Sandbox Meta Card */}
        <div className="p-4 rounded-xl bg-card border border-surface-border flex flex-col md:flex-row items-start md:items-center justify-between gap-4 text-xs font-mono">
          <div className="space-y-1 max-w-2xl">
            <div className="flex items-center gap-2 text-white font-bold text-sm">
              <Sparkles className="size-4 text-primary-light" />
              <span>{current.title}</span>
            </div>
            <p className="text-gray-300 font-sans text-xs">{current.description}</p>
          </div>

          <div className="flex flex-col items-start md:items-end gap-1 text-[11px] shrink-0">
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-sage/10 text-sage border border-sage/30">
              <CheckCircle2 className="size-3" />
              {current.assertions}
            </span>
            <span className="text-muted-foreground font-mono">
              Active Arm: <strong className="text-white uppercase">{selectedArm}</strong>
            </span>
          </div>
        </div>
      </div>

      {/* Embedded Iframe Container */}
      <div className="relative rounded-2xl border border-surface-border bg-slate-950 overflow-hidden shadow-2xl">
        <div className="h-10 bg-slate-900 border-b border-surface-border px-4 flex items-center justify-between text-xs font-mono text-muted-foreground">
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-500/80" />
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80" />
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80" />
            </div>
            <span className="text-slate-400 pl-2">preview://{activePath}</span>
          </div>

          <a
            href={resolvedUrl}
            target="_blank"
            rel="noreferrer"
            className="hover:text-white flex items-center gap-1"
          >
            <span>Fullscreen</span>
            <ExternalLink className="size-3" />
          </a>
        </div>

        <iframe
          key={iframeKey}
          src={resolvedUrl}
          title={current.title}
          className="w-full h-[750px] border-0 bg-slate-950"
          sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
        />
      </div>

      {/* Highlights & Delivery Verification */}
      <div className="rounded-2xl border border-surface-border bg-surface p-6 space-y-3">
        <h3 className="text-sm font-bold text-white font-mono flex items-center gap-2">
          <Info className="size-4 text-primary-light" />
          Delivered Artifact Architectural Highlights:
        </h3>
        <ul className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs font-mono text-gray-300">
          {current.highlights.map((h, i) => (
            <li key={i} className="p-3 rounded-lg bg-card border border-surface-border flex items-start gap-2">
              <CheckCircle2 className="size-4 text-sage shrink-0 mt-0.5" />
              <span>{h}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};
