import React from 'react';
import { Sparkles, RefreshCw } from 'lucide-react';
import { DashboardPayload } from '../types';
import { Button } from './ui/button';

interface HeaderProps {
  data: DashboardPayload | null;
  loading: boolean;
  onRefresh: () => void;
}

export const Header: React.FC<HeaderProps> = ({ data, loading, onRefresh }) => {
  return (
    <header className="sticky top-0 z-40 border-b border-surface-border bg-background/95 backdrop-blur px-5 lg:px-8 py-3.5">
      <div className="max-w-[1400px] mx-auto flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="size-8 rounded-lg bg-primary/10 border border-primary/30 flex items-center justify-center text-primary-light font-mono shadow-sm shrink-0">
            <Sparkles className="size-4.5 text-primary" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-sm md:text-base font-semibold tracking-tight text-white leading-none font-mono">
                Antigravity AI-Lab
              </h1>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono tracking-wider bg-surface text-primary-light border border-surface-border">
                Empirical Benchmark
              </span>
            </div>
            <p className="text-[11px] text-muted-foreground font-mono mt-0.5">
              Interpretable Context Methodology (ICM) vs. Baseline Agent Execution
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {data?.build_identity && (
            <span className="hidden sm:inline text-[11px] font-mono text-muted-foreground border border-surface-border px-2 py-1 rounded bg-surface">
              commit: {data.build_identity}
            </span>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={onRefresh}
            disabled={loading}
            className="text-xs font-mono gap-1.5 border-surface-border bg-surface hover:bg-background"
          >
            <RefreshCw className={`size-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">Refresh Data</span>
          </Button>
        </div>
      </div>
    </header>
  );
};
