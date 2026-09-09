import React from 'react';
import { Download, RefreshCw, Layers, ShieldCheck, Database } from 'lucide-react';
import { DashboardPayload } from '../types';
import { Button, buttonVariants } from './ui/button';
import { Badge } from './ui/badge';
import { cn } from '../lib/utils';

interface HeaderProps {
  data: DashboardPayload | null;
  loading: boolean;
  onRefresh: () => void;
}

export const Header: React.FC<HeaderProps> = ({ data, loading, onRefresh }) => {
  return (
    <header className="border-b border-surface-border bg-surface/80 backdrop-blur sticky top-0 z-30 px-6 py-4">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="size-9 rounded-lg bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400 font-bold shrink-0 shadow-sm">
              <Layers className="size-5" />
            </div>
            <div className="flex flex-col gap-0.5">
              <div className="flex items-center gap-2 flex-wrap">
                <h1 className="text-xl font-bold text-white tracking-tight">
                  Antigravity Savings Dashboard
                </h1>
                <Badge variant="default" className="bg-primary/20 text-primary border border-primary/30 font-medium">
                  ICM vs. Baseline A/B
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground flex items-center gap-2 flex-wrap">
                <span>Interpretable Context Methodology (ICM) Token & Cache Efficiency Engine</span>
                <span className="text-gray-600 hidden sm:inline">•</span>
                <span className="text-emerald-400 font-mono inline-flex items-center gap-1">
                  <ShieldCheck className="size-3" /> Measured Actuals (Zero Hallucinated Projections)
                </span>
              </p>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto justify-between md:justify-end">
          {data && (
            <div className="flex items-center gap-2 text-xs text-gray-400 bg-background/60 border border-surface-border px-3 py-1.5 rounded-md font-mono">
              <Database className="size-3.5 text-gray-400" />
              <span>{data.cumulative.tasks_evaluated} Task(s)</span>
              <span className="text-gray-600">•</span>
              <span>{data.runs.length} Runs</span>
            </div>
          )}

          <a
            href={`${(import.meta.env.BASE_URL || '/').replace(/\/+$/, '')}/data.json`}
            download="antigravity_usage_data.json"
            aria-label="Download usage ledger as JSON"
            className={buttonVariants({
              variant: "outline",
              size: "sm",
              className: "gap-1.5 text-xs text-gray-200 hover:text-white border-surface-border",
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
            className="text-primary hover:text-primary hover:bg-primary/10 border-primary/40 gap-1.5"
            title="Reload static data.json"
          >
            <RefreshCw className={cn("size-3.5", loading && "animate-spin")} />
            <span>Refresh</span>
          </Button>
        </div>
      </div>
    </header>
  );
};
