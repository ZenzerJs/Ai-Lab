import React from 'react';
import { Download, RefreshCw, Layers, ShieldCheck, Database } from 'lucide-react';
import { DashboardPayload } from '../types';

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
            <div className="w-9 h-9 rounded-lg bg-success/15 border border-success/30 flex items-center justify-center text-success font-bold">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
                Antigravity Savings Dashboard
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-primary/20 text-primary border border-primary/30">
                  ICM vs. Baseline A/B
                </span>
              </h1>
              <p className="text-xs text-gray-400 mt-0.5 flex items-center gap-2">
                <span>Interpretable Context Methodology (ICM) Token & Cache Efficiency Engine</span>
                <span className="text-gray-600">•</span>
                <span className="text-emerald-400 font-mono flex items-center gap-1">
                  <ShieldCheck className="w-3 h-3" /> Measured Actuals (No Projections)
                </span>
              </p>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto justify-between md:justify-end">
          {data && (
            <div className="flex items-center gap-2 text-xs text-gray-400 bg-background/60 border border-surface-border px-3 py-1.5 rounded-md font-mono">
              <Database className="w-3.5 h-3.5 text-gray-400" />
              <span>{data.cumulative.tasks_evaluated} Task(s)</span>
              <span className="text-gray-600">•</span>
              <span>{data.runs.length} Runs</span>
            </div>
          )}

          <a
            href="/data.json"
            download="antigravity_usage_data.json"
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-surface-hover hover:bg-surface-border text-gray-200 border border-surface-border transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download JSON</span>
          </a>

          <button
            onClick={onRefresh}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-primary/20 hover:bg-primary/30 text-primary border border-primary/40 transition-colors disabled:opacity-50"
            title="Reload static data.json"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>
    </header>
  );
};
