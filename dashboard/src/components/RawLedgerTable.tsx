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

export const RawLedgerTable: React.FC<RawLedgerTableProps> = ({ runs }) => {
  const [isOpen, setIsOpen] = useState(true);
  const [sortField, setSortField] = useState<SortField>('id');
  const [sortAsc, setSortAsc] = useState(true);
  const [armFilter, setArmFilter] = useState<'all' | 'baseline' | 'icm'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(true);
    }
  };

  const filteredRuns = useMemo(() => {
    return runs.filter((r) => {
      if (armFilter !== 'all' && r.arm.toLowerCase() !== armFilter) {
        return false;
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchTask = r.task_id.toLowerCase().includes(q);
        const matchModel = r.model.toLowerCase().includes(q);
        if (!matchTask && !matchModel) return false;
      }
      return true;
    });
  }, [runs, armFilter, searchQuery]);

  const sortedRuns = useMemo(() => {
    return [...filteredRuns].sort((a, b) => {
      const valA = a[sortField];
      const valB = b[sortField];

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
            n={runs.length} runs
          </Badge>
          {isOpen ? (
            <ChevronUp className="size-4 text-gray-400" />
          ) : (
            <ChevronDown className="size-4 text-gray-400" />
          )}
        </button>

        <div className="flex flex-wrap items-center gap-3 w-full sm:w-auto justify-between sm:justify-end">
          {/* Quick Search */}
          <div className="relative flex items-center">
            <Search className="size-3.5 text-gray-400 absolute left-2.5 pointer-events-none" />
            <Input
              type="text"
              placeholder="Search task or model..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
              aria-label="Filter runs by task or model"
              className="pl-8 w-40 sm:w-48"
            />
          </div>

          {/* Arm Filter */}
          <div className="flex items-center gap-1.5 text-xs text-gray-300">
            <Filter className="size-3.5 text-gray-400" />
            <SelectNative
              aria-label="Filter runs by arm"
              value={armFilter}
              onChange={(e) => {
                setArmFilter(e.target.value as any);
                setCurrentPage(1);
              }}
            >
              <option value="all">All Arms ({runs.length})</option>
              <option value="baseline">Baseline Only</option>
              <option value="icm">ICM Only</option>
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
              className: "gap-1.5 text-xs text-primary border-primary/30 hover:bg-surface-hover",
            })}
          >
            <Download className="size-3.5" />
            <span>Export JSON</span>
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
                <TableHead className="text-right">Input Tokens</TableHead>
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
                <TableHead className="text-right">Output Tokens</TableHead>
                <TableHead className="text-right">
                  <button
                    type="button"
                    onClick={() => handleSort('total_tokens')}
                    aria-sort={sortField === 'total_tokens' ? (sortAsc ? 'ascending' : 'descending') : 'none'}
                    className="inline-flex items-center justify-end gap-1 font-medium hover:text-white focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary rounded ml-auto"
                  >
                    Total Tokens <ArrowUpDown className="size-3" />
                  </button>
                </TableHead>
                <TableHead className="text-center">Turns</TableHead>
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
                return (
                  <TableRow
                    key={r.id}
                    className="hover:bg-surface-hover/60 transition-colors"
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
                    <TableCell className="text-gray-400 text-[11px]">{r.model}</TableCell>
                    <TableCell className="text-center text-gray-300">{r.run_index}</TableCell>
                    <TableCell className="text-right font-bold text-gray-100">
                      {formatCurrency(r.cost_usd, 5)}
                    </TableCell>
                    <TableCell className="text-right text-gray-300">
                      {formatTokens(r.input_tokens)}
                    </TableCell>
                    <TableCell
                      className={cn(
                        "text-right font-medium",
                        r.cache_read_tokens > 20000 ? "text-emerald-400 font-bold" : "text-gray-400"
                      )}
                    >
                      {formatTokens(r.cache_read_tokens)}
                    </TableCell>
                    <TableCell className="text-right text-gray-300">
                      {formatTokens(r.output_tokens)}
                    </TableCell>
                    <TableCell className="text-right text-gray-200">
                      {formatTokens(r.total_tokens)}
                    </TableCell>
                    <TableCell className="text-center text-gray-300">{r.num_turns}</TableCell>
                    <TableCell className="text-right text-gray-400">
                      {r.duration_seconds.toFixed(1)}s
                    </TableCell>
                  </TableRow>
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
                        Try adjusting your search query or switching the arm filter.
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
