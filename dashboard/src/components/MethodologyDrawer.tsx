import React, { useState } from 'react';
import { RawLedgerTable } from './RawLedgerTable';
import { SpendCascadeComparison } from './SpendCascadeComparison';
import { ModelSelector } from './ModelSelector';
import { DashboardPayload } from '../types';
import { ChevronDown, ChevronRight, ShieldCheck, Cpu, FileText } from 'lucide-react';

interface MethodologyDrawerProps {
  data: DashboardPayload;
  selectedModel: string;
  onModelChange: (model: string) => void;
}

export const MethodologyDrawer: React.FC<MethodologyDrawerProps> = ({
  data,
  selectedModel,
  onModelChange,
}) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="border border-surface-border rounded-xl bg-surface/50 overflow-hidden shadow-sm">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-5 py-4 flex items-center justify-between hover:bg-surface transition-colors text-left"
        aria-expanded={isOpen}
      >
        <div className="flex items-center gap-3">
          <div className="size-8 rounded-lg bg-surface border border-surface-border flex items-center justify-center shrink-0">
            <ShieldCheck className="size-4 text-primary" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white font-mono">
              Methodology, Provenance &amp; Raw Audit Ledger
            </h3>
            <p className="text-xs text-muted-foreground font-mono mt-0.5">
              Cryptographic hashes, rate-card simulator, and SQLite run logs.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground">
          <span>{isOpen ? 'Collapse' : 'Expand Details'}</span>
          {isOpen ? <ChevronDown className="size-4" /> : <ChevronRight className="size-4" />}
        </div>
      </button>

      {isOpen && (
        <div className="p-5 border-t border-surface-border space-y-6 bg-background/50">
          {/* Methodology Callouts */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono text-muted-foreground">
            <div className="bg-surface p-4 rounded-lg border border-surface-border space-y-1.5">
              <div className="text-white font-semibold flex items-center gap-1.5">
                <FileText className="size-3.5 text-primary" />
                Prompt Parity Invariant
              </div>
              <p className="leading-relaxed">
                Both baseline and ICM arms execute with byte-identical prompt specifications and identical model configs.
              </p>
            </div>

            <div className="bg-surface p-4 rounded-lg border border-surface-border space-y-1.5">
              <div className="text-white font-semibold flex items-center gap-1.5">
                <ShieldCheck className="size-3.5 text-emerald-400" />
                Evidence Verification
              </div>
              <p className="leading-relaxed">
                Every qualifying run is authenticated against its raw NDJSON stream with SHA-256 integrity checks.
              </p>
            </div>

            <div className="bg-surface p-4 rounded-lg border border-surface-border space-y-1.5">
              <div className="text-white font-semibold flex items-center gap-1.5">
                <Cpu className="size-3.5 text-cyan-400" />
                Multi-Model Pricing
              </div>
              <p className="leading-relaxed">
                Workloads measured on Gemini Flash are re-priced across official provider rate cards via exact token calculations.
              </p>
            </div>
          </div>

          {/* Rate Card Simulator */}
          <div className="space-y-3">
            <h4 className="text-xs font-semibold text-white font-mono uppercase tracking-wider">
              Cross-Model Rate Card Simulation
            </h4>
            <ModelSelector
              selectedModel={selectedModel}
              onModelChange={onModelChange}
              pricing={data.pricing || []}
            />
            {data.cascade && data.cascade.length > 0 && (
              <SpendCascadeComparison
                cascade={data.cascade}
                selectedModel={selectedModel}
                onSelectModel={onModelChange}
                scaleMode="1x"
              />
            )}
          </div>

          {/* Raw SQLite Ledger Table */}
          <div className="space-y-3">
            <h4 className="text-xs font-semibold text-white font-mono uppercase tracking-wider">
              Run-by-Run SQLite Audit Ledger
            </h4>
            <RawLedgerTable
              runs={data.runs}
              generatedAt={data.generated_at}
              buildIdentity={data.build_identity}
            />
          </div>
        </div>
      )}
    </div>
  );
};
