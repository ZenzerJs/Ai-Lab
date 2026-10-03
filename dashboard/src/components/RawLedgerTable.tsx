import React, { useState, useMemo } from 'react';
import { RunRecord } from '../types';
import {
  ChevronDown,
  ChevronUp,
  Download,
  ArrowUpDown,
  Filter,
  Search,
  Layers,
  ChevronLeft,
  ChevronRight,
  Database,
} from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from './ui/table';
import { Badge } from './ui/badge';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Button, buttonVariants } from './ui/button';
import { Input } from './ui/input';
import { SelectNative } from './ui/select-native';
import { Empty, EmptyIcon, EmptyTitle, EmptyDescription } from './ui/empty';
import { formatCurrency, formatTokens } from '../lib/formatters';
import { cn, getPublicUrl } from '../lib/utils';

interface RawLedgerTableProps {
  runs: RunRecord[];
  generatedAt?: string;
  buildIdentity?: string;
}

type SortField =
  | 'id'
  | 'task_id'
  | 'arm'
  | 'run_index'
  | 'cost_usd'
  | 'total_tokens'
  | 'cache_read_tokens'
  | 'duration_seconds';

export const RawLedgerTable: React.FC<RawLedgerTableProps> = ({ runs, generatedAt, buildIdentity }) => {
  const [isOpen, setIsOpen] = useState(true);
  const [sortField, setSortField] = useState<SortField>('id');
  const [sortAsc, setSortAsc] = useState(true);
  const [taskFilter, setTaskFilter] = useState<string>('all');
  const [armFilter, setArmFilter] = useState<string>('all');
  const [sourceFilter, setSourceFilter] = useState<string>('all');
  const [evidenceFilter, setEvidenceFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [expandedRunId, setExpandedRunId] = useState<number | null>(null);
  const pageSize = 10;

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(true);
    }
  };

  const distinctTasks = useMemo(() => {
    return Array.from(new Set(runs.map((r) => r.task_id))).sort();
  }, [runs]);

  const distinctArms = useMemo(() => {
    return Array.from(new Set(runs.map((r) => r.arm.toLowerCase()))).sort();
  }, [runs]);

  const distinctSources = useMemo(() => {
    return Array.from(new Set(runs.map((r) => String(r.source_kind || 'unknown')))).sort();
  }, [runs]);

  const distinctEvidence = useMemo(() => {
    return Array.from(new Set(runs.map((r) => String(r.evidence_status || 'unverified')))).sort();
  }, [runs]);

  const filteredRuns = useMemo(() => {
    return runs.filter((r) => {
      if (taskFilter !== 'all' && r.task_id !== taskFilter) {
        return false;
      }
      if (armFilter !== 'all' && r.arm.toLowerCase() !== armFilter) {
        return false;
      }
      if (sourceFilter !== 'all' && String(r.source_kind || 'unknown') !== sourceFilter) {
        return false;
      }
      if (evidenceFilter !== 'all' && String(r.evidence_status || 'unverified') !== evidenceFilter) {
        return false;
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchTask = r.task_id.toLowerCase().includes(q);
        const matchModel = r.model.toLowerCase().includes(q);
        const matchNotes = (r.notes || '').toLowerCase().includes(q);
        const matchReasons = (r.exclusion_reasons || []).some((re) => re.toLowerCase().includes(q));
        if (!matchTask && !matchModel && !matchNotes && !matchReasons) return false;
      }
      return true;
    });
  }, [runs, taskFilter, armFilter, sourceFilter, evidenceFilter, searchQuery]);

  const sortedRuns = useMemo(() => {
    return [...filteredRuns].sort((a, b) => {
      const valA = a[sortField];
      const valB = b[sortField];

      if (valA === null || valA === undefined) return sortAsc ? 1 : -1;
      if (valB === null || valB === undefined) return sortAsc ? -1 : 1;

      if (typeof valA === 'string') {
        return sortAsc
          ? (valA as string).localeCompare(valB as string)
          : (valB as string).localeCompare(valA as string);
      }

      return sortAsc ? (valA as number) - (valB as number) : (valB as number) - (valA as number);
    });
  }, [filteredRuns, sortField, sortAsc]);

  // Pagination calculations
  const totalPages = Math.max(1, Math.ceil(sortedRuns.length / pageSize));
  const effectivePage = Math.min(currentPage, totalPages);
  const paginatedRuns = useMemo(() => {
    const startIndex = (effectivePage - 1) * pageSize;
    return sortedRuns.slice(startIndex, startIndex + pageSize);
  }, [sortedRuns, effectivePage, pageSize]);

  return (
    <Card className="overflow-hidden">
      {/* Table Header / Toggle Bar */}
      <CardHeader className="p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 bg-surface/90">
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          aria-expanded={isOpen}
          className="flex items-center gap-2 text-base font-semibold text-white hover:text-primary transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary rounded-md px-1"
        >
          <Layers className="size-4 text-primary" />
          <CardTitle className="text-base">Raw Ledger Entries</CardTitle>
          <Badge variant="secondary" className="font-mono text-xs">
            Showing {filteredRuns.length} of {runs.length} runs
          </Badge>
          {isOpen ? (
            <ChevronUp className="size-4 text-gray-400" />
          ) : (
            <ChevronDown className="size-4 text-gray-400" />
          )}
        </button>

        {(generatedAt || buildIdentity) && (
          <p className="text-[10px] text-gray-500 font-mono mt-0.5 sm:mt-0 sm:ml-1 shrink-0">
            {buildIdentity && <span title="Build identity">build:{buildIdentity}</span>}
            {generatedAt && buildIdentity && <span className="mx-1">·</span>}
            {generatedAt && (
              <span title="Snapshot generated at">{new Date(generatedAt).toLocaleString()}</span>
            )}
          </p>
        )}

        <div className="flex flex-wrap items-center gap-2.5 w-full sm:w-auto justify-between sm:justify-end">
          {/* Quick Search */}
          <div className="relative flex items-center">
            <Search className="size-3.5 text-gray-400 absolute left-2.5 pointer-events-none" />
            <Input
              type="text"
              placeholder="Search task, model, notes..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
              aria-label="Filter runs by search"
              className="pl-8 w-36 sm:w-44 h-8 text-xs"
            />
          </div>

          {/* Task Filter */}
          <div className="flex items-center gap-1 text-xs text-gray-300">
            <SelectNative
              aria-label="Filter runs by task"
              value={taskFilter}
              onChange={(e) => {
                setTaskFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="h-8 text-xs font-mono"
            >
              <option value="all">All Tasks</option>
              {distinctTasks.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </SelectNative>
          </div>

          {/* Arm Filter */}
          <div className="flex items-center gap-1 text-xs text-gray-300">
            <Filter className="size-3.5 text-gray-400 shrink-0" />
            <SelectNative
              aria-label="Filter runs by arm"
              value={armFilter}
              onChange={(e) => {
                setArmFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="h-8 text-xs font-mono"
            >
              <option value="all">All Arms</option>
              {distinctArms.map((a) => (
                <option key={a} value={a}>
                  {a.toUpperCase()}
                </option>
              ))}
            </SelectNative>
          </div>

          {/* Source Filter */}
          <div className="flex items-center gap-1 text-xs text-gray-300">
            <SelectNative
              aria-label="Filter runs by source kind"
              value={sourceFilter}
              onChange={(e) => {
                setSourceFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="h-8 text-xs font-mono"
            >
              <option value="all">All Sources</option>
              {distinctSources.map((s) => (
                <option key={s} value={s}>
                  Source: {s}
                </option>
              ))}
            </SelectNative>
          </div>

          {/* Evidence Filter */}
          <div className="flex items-center gap-1 text-xs text-gray-300">
            <SelectNative
              aria-label="Filter runs by evidence status"
              value={evidenceFilter}
              onChange={(e) => {
                setEvidenceFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="h-8 text-xs font-mono"
            >
              <option value="all">All Evidence</option>
              {distinctEvidence.map((ev) => (
                <option key={ev} value={ev}>
                  Evidence: {ev}
                </option>
              ))}
            </SelectNative>
          </div>

          {/* Download JSON */}
          <a
            href={getPublicUrl('data.json')}
            download="antigravity_usage_ledger.json"
            aria-label="Download raw ledger data as JSON"
            className={buttonVariants({
              variant: "outline",
              size: "sm",
              className: "gap-1.5 text-xs text-primary border-primary/30 hover:bg-surface-hover h-8",
            })}
          >
            <Download className="size-3.5" />
            <span>Export</span>
          </a>
        </div>
      </CardHeader>

      {isOpen && (
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="border-b border-surface-border select-none">
                <TableHead>
                  <button
                    type="button"
                    onClick={() => handleSort('id')}
                    aria-sort={sortField === 'id' ? (sortAsc ? 'ascending' : 'descending') : 'none'}
                    className="flex items-center gap-1 font-medium hover:text-white focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary rounded"
                  >
                    ID <ArrowUpDown className="size-3" />
                  </button>
                </TableHead>
                <TableHead>
                  <button
                    type="button"
                    onClick={() => handleSort('task_id')}
                    aria-sort={sortField === 'task_id' ? (sortAsc ? 'ascending' : 'descending') : 'none'}
                    className="flex items-center gap-1 font-medium hover:text-white focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary rounded"
                  >
                    Task <ArrowUpDown className="size-3" />
                  </button>
                </TableHead>
                <TableHead>
                  <button
                    type="button"
                    onClick={() => handleSort('arm')}
                    aria-sort={sortField === 'arm' ? (sortAsc ? 'ascending' : 'descending') : 'none'}
                    className="flex items-center gap-1 font-medium hover:text-white focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary rounded"
                  >
                    Arm <ArrowUpDown className="size-3" />
                  </button>
                </TableHead>
                <TableHead>Source</TableHead>
                <TableHead>Evidence</TableHead>
                <TableHead>Status / Eligibility</TableHead>
                <TableHead>Model</TableHead>
                <TableHead className="text-center">
                  <button
                    type="button"
                    onClick={() => handleSort('run_index')}
                    aria-sort={sortField === 'run_index' ? (sortAsc ? 'ascending' : 'descending') : 'none'}
                    className="inline-flex items-center justify-center gap-1 font-medium hover:text-white focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary rounded"
                  >
                    Run # <ArrowUpDown className="size-3" />
                  </button>
                </TableHead>
                <TableHead className="text-right">
                  <button
                    type="button"
                    onClick={() => handleSort('cost_usd')}
                    aria-sort={sortField === 'cost_usd' ? (sortAsc ? 'ascending' : 'descending') : 'none'}
                    className="inline-flex items-center justify-end gap-1 font-medium hover:text-white focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary rounded ml-auto"
                  >
                    Cost (USD) <ArrowUpDown className="size-3" />
                  </button>
                </TableHead>
                <TableHead className="text-right">Total Tokens</TableHead>
                <TableHead className="text-right">
                  <button
                    type="button"
                    onClick={() => handleSort('cache_read_tokens')}
                    aria-sort={sortField === 'cache_read_tokens' ? (sortAsc ? 'ascending' : 'descending') : 'none'}
                    className="inline-flex items-center justify-end gap-1 font-medium hover:text-white focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary rounded ml-auto"
                  >
                    Cache Read <ArrowUpDown className="size-3" />
                  </button>
                </TableHead>
                <TableHead className="text-right">
                  <button
                    type="button"
                    onClick={() => handleSort('duration_seconds')}
                    aria-sort={sortField === 'duration_seconds' ? (sortAsc ? 'ascending' : 'descending') : 'none'}
                    className="inline-flex items-center justify-end gap-1 font-medium hover:text-white focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary rounded ml-auto"
                  >
                    Duration <ArrowUpDown className="size-3" />
                  </button>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {paginatedRuns.map((r) => {
                const isBaseline = r.arm.toLowerCase() === 'baseline';
                const isExpanded = expandedRunId === r.id;
                const source = r.source_kind || 'unknown';
                const evidence = r.evidence_status || 'unverified';
                const isEligible = r.is_comparison_eligible;

                let sourceBadgeColor = 'bg-gray-500/10 text-gray-400 border-gray-500/30';
                if (source === 'live') sourceBadgeColor = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
                else if (source === 'fixture') sourceBadgeColor = 'bg-sky-500/10 text-sky-400 border-sky-500/30';
                else if (source === 'imported') sourceBadgeColor = 'bg-purple-500/10 text-purple-400 border-purple-500/30';

                let evBadgeColor = 'bg-amber-500/10 text-amber-400 border-amber-500/30';
                if (evidence === 'verified') evBadgeColor = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
                else if (evidence === 'invalid') evBadgeColor = 'bg-red-500/10 text-red-400 border-red-500/30';
                else if (evidence === 'missing') evBadgeColor = 'bg-gray-500/10 text-gray-400 border-gray-500/30';

                return (
                  <React.Fragment key={r.id}>
                    <TableRow
                      onClick={() => setExpandedRunId(isExpanded ? null : r.id)}
                      className="hover:bg-surface-hover/60 transition-colors cursor-pointer"
                      title="Click to view run details and evidence provenance"
                    >
                      <TableCell className="text-gray-500 font-mono">#{r.id}</TableCell>
                      <TableCell className="font-semibold text-gray-200">{r.task_id}</TableCell>
                      <TableCell>
                        <Badge
                          variant={isBaseline ? 'destructive' : 'success'}
                          className="text-[10px] uppercase tracking-wider py-0"
                        >
                          {r.arm}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <span className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-mono border ${sourceBadgeColor}`}>
                          {source}
                        </span>
                      </TableCell>
                      <TableCell>
                        <span className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-mono border ${evBadgeColor}`}>
                          {evidence}
                        </span>
                      </TableCell>
                      <TableCell>
                        {isEligible ? (
                          <span className="inline-block px-1.5 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                            Eligible
                          </span>
                        ) : (
                          <span className="inline-block px-1.5 py-0.5 rounded text-[10px] font-mono bg-red-500/10 text-red-400 border border-red-500/30">
                            Excluded
                          </span>
                        )}
                      </TableCell>
                      <TableCell className="text-gray-400 text-[11px] font-mono">{r.model}</TableCell>
                      <TableCell className="text-center text-gray-300 font-mono">{r.run_index}</TableCell>
                      <TableCell className="text-right font-bold text-gray-100 font-mono">
                        {formatCurrency(r.cost_usd, 5)}
                      </TableCell>
                      <TableCell className="text-right text-gray-200 font-mono">
                        {formatTokens(r.total_tokens)}
                      </TableCell>
                      <TableCell
                        className={cn(
                          "text-right font-medium font-mono",
                          r.cache_read_tokens > 20000 ? "text-emerald-400 font-bold" : "text-gray-400"
                        )}
                      >
                        {formatTokens(r.cache_read_tokens)}
                      </TableCell>
                      <TableCell className="text-right text-gray-400 font-mono">
                        {r.duration_seconds.toFixed(1)}s
                      </TableCell>
                    </TableRow>

                    {/* Expandable Evidence & Provenance Details Row */}
                    {isExpanded && (
                      <TableRow className="bg-background/80 border-b border-surface-border">
                        <TableCell colSpan={12} className="p-4 text-xs font-mono">
                          <div className="p-3 rounded-lg bg-surface/90 border border-surface-border space-y-2">
                            <div className="flex items-center justify-between text-muted-foreground border-b border-surface-border/50 pb-2">
                              <span className="text-white font-semibold">Run #{r.id} Evidence & Provenance Ledger</span>
                              <span>Task: {r.task_id} • Arm: {r.arm} • Run {r.run_index}</span>
                            </div>
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-1">
                              <div>
                                <span className="text-gray-400 text-[11px] block">Execution Status:</span>
                                <span className="text-white font-medium">{r.execution_status || 'completed'}</span>
                              </div>
                              <div>
                                <span className="text-gray-400 text-[11px] block">Verification Status:</span>
                                <span className={r.verification_status === 'passed' ? 'text-emerald-400 font-medium' : 'text-amber-400 font-medium'}>
                                  {r.verification_status || 'not_run'}
                                </span>
                              </div>
                              <div>
                                <span className="text-gray-400 text-[11px] block">Cost Calculation:</span>
                                <span className="text-gray-200">{r.cost_status || 'usage_estimate'}</span>
                              </div>
                              <div>
                                <span className="text-gray-400 text-[11px] block">Safe Evidence Ref:</span>
                                <span className="text-primary-light truncate block" title={r.evidence_ref || 'None'}>
                                  {r.evidence_ref || 'None'}
                                </span>
                              </div>
                            </div>

                            {/* Exclusion Reasons */}
                            {r.exclusion_reasons && r.exclusion_reasons.length > 0 && (
                              <div className="pt-2 border-t border-surface-border/40">
                                <span className="text-amber-400 text-[11px] block mb-1">Exclusion Reasons (from comparison sample):</span>
                                <div className="flex flex-wrap gap-1.5">
                                  {r.exclusion_reasons.map((reason, idx) => (
                                    <span key={idx} className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/30 text-[10px]">
                                      {reason}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Notes */}
                            {r.notes && (
                              <div className="pt-2 border-t border-surface-border/40">
                                <span className="text-gray-400 text-[11px] block mb-0.5">Notes:</span>
                                <p className="text-gray-300 text-[11px] leading-relaxed break-all bg-background/50 p-2 rounded border border-surface-border/30">
                                  {r.notes}
                                </p>
                              </div>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    )}
                  </React.Fragment>
                );
              })}
              {sortedRuns.length === 0 && (
                <TableRow>
                  <TableCell colSpan={12} className="py-8">
                    <Empty>
                      <EmptyIcon>
                        <Database className="size-6 text-muted-foreground" />
                      </EmptyIcon>
                      <EmptyTitle>No matching ledger runs found</EmptyTitle>
                      <EmptyDescription>
                        Try adjusting your search query, task filter, arm filter, or source filter.
                      </EmptyDescription>
                    </Empty>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>

          {/* Pagination Controls */}
          {sortedRuns.length > pageSize && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-surface-border bg-surface/50 text-xs text-muted-foreground">
              <div className="font-mono">
                Showing {((effectivePage - 1) * pageSize) + 1}–{Math.min(effectivePage * pageSize, sortedRuns.length)} of {sortedRuns.length} runs
              </div>
              <div className="flex items-center gap-1.5">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={effectivePage <= 1}
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  aria-label="Previous page"
                  className="size-7 p-0"
                >
                  <ChevronLeft className="size-3.5" />
                </Button>
                <span className="font-mono px-2 text-gray-300">
                  {effectivePage} / {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={effectivePage >= totalPages}
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  aria-label="Next page"
                  className="size-7 p-0"
                >
                  <ChevronRight className="size-3.5" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      )}
    </Card>
  );
};
