import React, { useState } from 'react';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import { TaskSummaryItem } from '../types';
import { Zap, AlertCircle } from 'lucide-react';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from './ui/card';
import { Badge } from './ui/badge';
import { SelectNative } from './ui/select-native';
import { Empty, EmptyIcon, EmptyTitle, EmptyDescription } from './ui/empty';
import { formatTokens } from '../lib/formatters';

interface CacheHitRatioProps {
  tasks: TaskSummaryItem[];
}

export const CacheHitRatio: React.FC<CacheHitRatioProps> = ({ tasks }) => {
  const [selectedTaskIndex, setSelectedTaskIndex] = useState(0);

  if (!tasks || tasks.length === 0) {
    return (
      <Card>
        <CardContent className="p-0">
          <Empty>
            <EmptyIcon>
              <AlertCircle className="size-6 text-muted-foreground" />
            </EmptyIcon>
            <EmptyTitle>No cache telemetry data available</EmptyTitle>
            <EmptyDescription>
              Telemetry will populate once prompt caching metrics are recorded in the usage ledger.
            </EmptyDescription>
          </Empty>
        </CardContent>
      </Card>
    );
  }

  const currentTask = tasks[selectedTaskIndex] || tasks[0];
  const b = currentTask.arms.baseline;
  const i = currentTask.arms.icm;

  const bInput = b?.mean_input_tokens ?? 0;
  const bCache = b?.mean_cache_read_tokens ?? 0;
  const bRatio = b?.cache_hit_ratio ?? 0;
  const bN = b?.n ?? 0;
  const bTotalPrompt = bInput + bCache;
  const bCachePercent = bTotalPrompt > 0 ? (bCache / bTotalPrompt) * 100 : 0;

  const iInput = i?.mean_input_tokens ?? 0;
  const iCache = i?.mean_cache_read_tokens ?? 0;
  const iRatio = i?.cache_hit_ratio ?? 0;
  const iN = i?.n ?? 0;
  const iTotalPrompt = iInput + iCache;
  const iCachePercent = iTotalPrompt > 0 ? (iCache / iTotalPrompt) * 100 : 0;

  // Pie chart datasets with fallback for 0 total tokens
  const baselinePieData = bTotalPrompt > 0
    ? [
        { name: 'Fresh Input Tokens', value: Math.round(bInput), color: '#f85149' },
        { name: 'Cache Read Tokens', value: Math.round(bCache), color: '#ffa198' },
      ]
    : [{ name: 'No Tokens Recorded', value: 1, color: '#30363d' }];

  const icmPieData = iTotalPrompt > 0
    ? [
        { name: 'Fresh Input Tokens', value: Math.round(iInput), color: '#3fb950' },
        { name: 'Cache Read Tokens', value: Math.round(iCache), color: '#238636' },
      ]
    : [{ name: 'No Tokens Recorded', value: 1, color: '#30363d' }];

  const CustomPieTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0];
      return (
        <div className="bg-surface border border-surface-border p-2.5 rounded-md shadow-lg text-xs">
          <span className="font-semibold text-white">{data.name}:</span>{' '}
          <span className="font-mono text-gray-300">
            {data.color === '#30363d' ? '0' : formatTokens(data.value)} tokens
          </span>
        </div>
      );
    }
    return null;
  };

  return (
    <Card className="flex flex-col justify-between">
      <div>
        <CardHeader className="flex flex-col gap-1 pb-3">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <Zap className="size-4 text-warning" />
              <CardTitle>Cache Hit Ratio & Token Distribution</CardTitle>
            </div>

            {tasks.length > 1 && (
              <SelectNative
                aria-label="Select benchmark task"
                value={selectedTaskIndex}
                onChange={(e) => setSelectedTaskIndex(Number(e.target.value))}
              >
                {tasks.map((t, idx) => (
                  <option key={t.task_id} value={idx}>
                    Task {t.task_id}
                  </option>
                ))}
              </SelectNative>
            )}
          </div>

          <CardDescription>
            Ratio of prompt cache reads to fresh input tokens (<code className="text-gray-300 font-mono">cache_read / input</code>).
            High cache ratios convert expensive fresh tokens into fractional cache reads.
          </CardDescription>
        </CardHeader>

        <CardContent className="pt-4 flex flex-col gap-4">
          {/* Dual Donut Visualizer */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Baseline Donut */}
            <div className="flex flex-col items-center bg-background/40 border border-surface-border/80 rounded-lg p-3">
              <div className="text-xs font-semibold text-gray-300 flex items-center justify-between w-full pb-1 border-b border-surface-border/50">
                <span className="text-red-400">Baseline Arm</span>
                <Badge variant="secondary" className="text-[10px] py-0 px-1 font-normal font-mono">n={bN}</Badge>
              </div>

              <div className="size-36 relative mt-2">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Tooltip content={<CustomPieTooltip />} />
                    <Pie
                      data={baselinePieData}
                      innerRadius={36}
                      outerRadius={56}
                      paddingAngle={bTotalPrompt > 0 ? 3 : 0}
                      dataKey="value"
                    >
                      {baselinePieData.map((entry, index) => (
                        <Cell key={`cell-b-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
                <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                  <span className="text-xs font-bold text-red-300 font-mono">
                    {bCachePercent.toFixed(1)}%
                  </span>
                  <span className="text-[9px] text-gray-500 uppercase tracking-tight">Cached</span>
                </div>
              </div>

              <div className="w-full mt-2 flex flex-col gap-1 text-[11px] text-gray-400 font-mono">
                <div className="flex justify-between">
                  <span>Fresh Input:</span>
                  <span className="text-gray-200">{formatTokens(bInput)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Cache Read:</span>
                  <span className="text-red-300">{formatTokens(bCache)}</span>
                </div>
                <div className="flex justify-between pt-1 border-t border-surface-border/40 text-gray-300">
                  <span>Cache/Input Ratio:</span>
                  <span className="font-semibold text-red-300">{bRatio.toFixed(2)}x</span>
                </div>
              </div>
            </div>

            {/* ICM Donut */}
            <div className="flex flex-col items-center bg-background/40 border border-surface-border/80 rounded-lg p-3">
              <div className="text-xs font-semibold text-gray-300 flex items-center justify-between w-full pb-1 border-b border-surface-border/50">
                <span className="text-emerald-400">ICM Pipeline</span>
                <Badge variant="secondary" className="text-[10px] py-0 px-1 font-normal font-mono">n={iN}</Badge>
              </div>

              <div className="size-36 relative mt-2">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Tooltip content={<CustomPieTooltip />} />
                    <Pie
                      data={icmPieData}
                      innerRadius={36}
                      outerRadius={56}
                      paddingAngle={iTotalPrompt > 0 ? 3 : 0}
                      dataKey="value"
                    >
                      {icmPieData.map((entry, index) => (
                        <Cell key={`cell-i-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
                <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                  <span className="text-xs font-bold text-emerald-400 font-mono">
                    {iCachePercent.toFixed(1)}%
                  </span>
                  <span className="text-[9px] text-gray-500 uppercase tracking-tight">Cached</span>
                </div>
              </div>

              <div className="w-full mt-2 flex flex-col gap-1 text-[11px] text-gray-400 font-mono">
                <div className="flex justify-between">
                  <span>Fresh Input:</span>
                  <span className="text-gray-200">{formatTokens(iInput)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Cache Read:</span>
                  <span className="text-emerald-400">{formatTokens(iCache)}</span>
                </div>
                <div className="flex justify-between pt-1 border-t border-surface-border/40 text-gray-300">
                  <span>Cache/Input Ratio:</span>
                  <span className="font-semibold text-emerald-300">{iRatio.toFixed(2)}x</span>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </div>

      <CardFooter className="pt-0 pb-5">
        <div className="w-full text-xs bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-3">
          <span className="font-semibold text-emerald-400">ICM Context Isolation Advantage:</span>{' '}
          <span className="text-gray-300">
            ICM achieves <span className="font-mono font-bold text-emerald-300">{iRatio.toFixed(2)}x ({iCachePercent.toFixed(1)}% cached)</span> vs.{' '}
            baseline's <span className="font-mono font-bold text-red-300">{bRatio.toFixed(2)}x ({bCachePercent.toFixed(1)}% cached)</span> by keeping system prompts and OKF slices deterministic across stage boundaries.
          </span>
        </div>
      </CardFooter>
    </Card>
  );
};
