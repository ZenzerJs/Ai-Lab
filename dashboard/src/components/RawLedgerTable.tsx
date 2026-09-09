import React, { useState } from 'react';
import { RunRecord } from '../types';
import {
  Table,
  ChevronDown,
  ChevronUp,
  Download,
  ArrowUpDown,
  Filter,
} from 'lucide-react';

interface RawLedgerTableProps {
  runs: RunRecord[];
}

type SortField = 'id' | 'task_id' | 'arm' | 'run_index' | 'cost_usd' | 'total_tokens' | 'cache_read_tokens' | 'duration_seconds';

export const RawLedgerTable: React.FC<RawLedgerTableProps> = ({ runs }) => {
  const [isOpen, setIsOpen] = useState(true);
  const [sortField, setSortField] = useState<SortField>('id');
  const [sortAsc, setSortAsc] = useState(true);
  const [armFilter, setArmFilter] = useState<'all' | 'baseline' | 'icm'>('all');

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(true);
    }
  };

  const filteredRuns = runs.filter((r) => {
    if (armFilter === 'all') return true;
    return r.arm.toLowerCase() === armFilter;
  });

  const sortedRuns = [...filteredRuns].sort((a, b) => {
    let valA = a[sortField];
    let valB = b[sortField];

    if (typeof valA === 'string') {
      return sortAsc
        ? (valA as string).localeCompare(valB as string)
        : (valB as string).localeCompare(valA as string);
    }

    return sortAsc ? (valA as number) - (valB as number) : (valB as number) - (valA as number);
  });

  return (
    <div className="bg-surface border border-surface-border rounded-xl shadow-sm overflow-hidden">
      {/* Table Header / Toggle Bar */}
      <div className="p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between border-b border-surface-border gap-3 bg-surface/90">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center gap-2 text-base font-semibold text-white hover:text-primary transition-colors focus:outline-none"
        >
          <Table className="w-4 h-4 text-primary" />
          <span>Raw Ledger Entries</span>
          <span className="text-xs font-mono text-gray-400 bg-background px-2 py-0.5 rounded border border-surface-border">
            n={runs.length} runs recorded
          </span>
          {isOpen ? (
            <ChevronUp className="w-4 h-4 text-gray-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-gray-400" />
          )}
        </button>

        <div className="flex items-center gap-3 w-full sm:w-auto justify-between sm:justify-end">
          {/* Filter */}
          <div className="flex items-center gap-1.5 text-xs text-gray-300">
            <Filter className="w-3.5 h-3.5 text-gray-400" />
            <select
              value={armFilter}
              onChange={(e) => setArmFilter(e.target.value as any)}
              className="bg-background border border-surface-border rounded px-2 py-1 text-xs text-gray-200 focus:outline-none focus:border-primary"
            >
              <option value="all">All Arms ({runs.length})</option>
              <option value="baseline">Baseline Only</option>
              <option value="icm">ICM Only</option>
            </select>
          </div>

          {/* Download JSON */}
          <a
            href="/data.json"
            download="antigravity_usage_ledger.json"
            className="flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded bg-background hover:bg-surface-hover text-primary border border-primary/30 transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download JSON</span>
          </a>
        </div>
      </div>

      {isOpen && (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-background/80 text-gray-400 border-b border-surface-border select-none">
              <tr>
                <th
                  onClick={() => handleSort('id')}
                  className="px-4 py-2.5 cursor-pointer hover:text-white"
                >
                  <div className="flex items-center gap-1">
                    ID <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th
                  onClick={() => handleSort('task_id')}
                  className="px-4 py-2.5 cursor-pointer hover:text-white"
                >
                  <div className="flex items-center gap-1">
                    Task <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th
                  onClick={() => handleSort('arm')}
                  className="px-4 py-2.5 cursor-pointer hover:text-white"
                >
                  <div className="flex items-center gap-1">
                    Arm <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th className="px-4 py-2.5">Model</th>
                <th
                  onClick={() => handleSort('run_index')}
                  className="px-4 py-2.5 cursor-pointer hover:text-white text-center"
                >
                  <div className="flex items-center justify-center gap-1">
                    Run # <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th
                  onClick={() => handleSort('cost_usd')}
                  className="px-4 py-2.5 cursor-pointer hover:text-white text-right"
                >
                  <div className="flex items-center justify-end gap-1">
                    Cost (USD) <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th className="px-4 py-2.5 text-right">Input Tokens</th>
                <th
                  onClick={() => handleSort('cache_read_tokens')}
                  className="px-4 py-2.5 cursor-pointer hover:text-white text-right"
                >
                  <div className="flex items-center justify-end gap-1">
                    Cache Read <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th className="px-4 py-2.5 text-right">Output Tokens</th>
                <th
                  onClick={() => handleSort('total_tokens')}
                  className="px-4 py-2.5 cursor-pointer hover:text-white text-right"
                >
                  <div className="flex items-center justify-end gap-1">
                    Total Tokens <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th className="px-4 py-2.5 text-center">Turns</th>
                <th
                  onClick={() => handleSort('duration_seconds')}
                  className="px-4 py-2.5 cursor-pointer hover:text-white text-right"
                >
                  <div className="flex items-center justify-end gap-1">
                    Duration <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border/60">
              {sortedRuns.map((r) => {
                const isBaseline = r.arm.toLowerCase() === 'baseline';
                return (
                  <tr
                    key={r.id}
                    className="hover:bg-surface-hover/60 transition-colors"
                  >
                    <td className="px-4 py-2 text-gray-500">#{r.id}</td>
                    <td className="px-4 py-2 font-semibold text-gray-200">{r.task_id}</td>
                    <td className="px-4 py-2">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                          isBaseline
                            ? 'bg-red-500/15 text-red-400 border border-red-500/30'
                            : 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                        }`}
                      >
                        {r.arm}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-gray-400 text-[11px]">{r.model}</td>
                    <td className="px-4 py-2 text-center text-gray-300">{r.run_index}</td>
                    <td className="px-4 py-2 text-right font-bold text-gray-100">
                      ${r.cost_usd.toFixed(5)}
                    </td>
                    <td className="px-4 py-2 text-right text-gray-300">
                      {r.input_tokens.toLocaleString()}
                    </td>
                    <td
                      className={`px-4 py-2 text-right font-medium ${
                        r.cache_read_tokens > 20000
                          ? 'text-emerald-400'
                          : 'text-gray-400'
                      }`}
                    >
                      {r.cache_read_tokens.toLocaleString()}
                    </td>
                    <td className="px-4 py-2 text-right text-gray-300">
                      {r.output_tokens.toLocaleString()}
                    </td>
                    <td className="px-4 py-2 text-right text-gray-200">
                      {r.total_tokens.toLocaleString()}
                    </td>
                    <td className="px-4 py-2 text-center text-gray-300">{r.num_turns}</td>
                    <td className="px-4 py-2 text-right text-gray-400">
                      {r.duration_seconds.toFixed(1)}s
                    </td>
                  </tr>
                );
              })}
              {sortedRuns.length === 0 && (
                <tr>
                  <td colSpan={12} className="px-4 py-8 text-center text-gray-500">
                    No runs match the selected filter.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
