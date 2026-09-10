import React, { useState } from 'react';
import { TaskSummaryItem } from '../types';
import { ShieldCheck, AlertCircle } from 'lucide-react';
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

interface DonutGaugeProps {
  armLabel: string;
  labelColorClass: string;
  valueColorClass: string;
  strokeColor: string;
  ringGlow: boolean;
  cachedPercent: number;
  inputTokens: number;
  cacheTokens: number;
  ratio: number;
  n: number;
}

/** SVG donut gauge ported from code.html: r=15 viewBox 36, dasharray 100, dashoffset sweep. */
const DonutGauge: React.FC<DonutGaugeProps> = ({
  armLabel,
  labelColorClass,
  valueColorClass,
  strokeColor,
  ringGlow,
  cachedPercent,
  inputTokens,
  cacheTokens,
  ratio,
  n,
}) => {
  const clamped = Math.min(100, Math.max(0, cachedPercent));
  const offset = 100 - clamped;

  return (
    <div
      className={`flex flex-col items-center bg-card/60 p-3.5 rounded-lg border ${
        ringGlow ? 'border-primary/20' : 'border-surface-border'
      }`}
    >
      <div className="flex items-center justify-between w-full">
        <span className={`text-[11px] font-mono ${labelColorClass}`}>{armLabel}</span>
        <Badge variant="secondary" className="text-[10px] py-0 px-1 font-normal font-mono">
          n={n}
        </Badge>
      </div>

      <div className="relative w-28 h-28 my-2">
        <svg className="w-full h-full -rotate-90" viewBox="0 0 36 36">
          <circle cx="18" cy="18" fill="none" r="15" stroke="#232B3B" strokeWidth="3" />
          <circle
            cx="18"
            cy="18"
            fill="none"
            r="15"
            stroke={strokeColor}
            strokeDasharray="100"
            strokeDashoffset={offset}
            strokeLinecap="round"
            strokeWidth="3"
            className={ringGlow ? 'donut-glow-indigo' : undefined}
            style={{ transition: 'stroke-dashoffset 0.6s cubic-bezier(0.16, 1, 0.3, 1)' }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <span className={`text-base font-bold font-mono tabular-nums ${valueColorClass}`}>
            {cachedPercent.toFixed(1)}%
          </span>
          <span className="text-[9px] font-mono uppercase text-muted-foreground">Cached</span>
        </div>
      </div>

      <div className="w-full text-left font-mono text-[11px] space-y-1 text-muted-foreground mt-1">
        <div className="flex justify-between">
          <span>Fresh Input:</span>
          <span className="text-gray-200 tabular-nums">{formatTokens(inputTokens)}</span>
        </div>
        <div className="flex justify-between">
          <span>Cache Read:</span>
          <span className={`${valueColorClass} tabular-nums`}>{formatTokens(cacheTokens)}</span>
        </div>
        <div className="flex justify-between pt-1 border-t border-surface-border text-[10px]">
          <span>Cache/Input:</span>
          <span className="text-sage font-medium tabular-nums">{ratio.toFixed(2)}x</span>
        </div>
      </div>
    </div>
  );
};

/** Dual donut gauges ported from the code.html prototype (baseline terracotta vs ICM indigo sweep). */
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

  return (
    <Card className="flex flex-col justify-between">
      <div>
        <CardHeader className="flex flex-col gap-1 pb-3">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <ShieldCheck className="size-4 text-primary" />
              <CardTitle>Cache Hit Ratio & Token Shift</CardTitle>
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
            Share of prompt tokens served from cache (<code className="text-gray-300 font-mono">cache_read / (cache_read + fresh_input)</code>).
            High cache share converts expensive fresh tokens into fractional cache reads.
          </CardDescription>
        </CardHeader>

        <CardContent className="pt-4 flex flex-col gap-4">
          {/* Dual Donut Gauges (ported from code.html) */}
          <div className="grid grid-cols-2 gap-4 my-2 text-center">
            <DonutGauge
              armLabel="Baseline Arm"
              labelColorClass="text-muted-foreground"
              valueColorClass="text-baseline"
              strokeColor="#E06C54"
              ringGlow={false}
              cachedPercent={bCachePercent}
              inputTokens={bInput}
              cacheTokens={bCache}
              ratio={bRatio}
              n={bN}
            />
            <DonutGauge
              armLabel="ICM Pipeline"
              labelColorClass="text-primary-light font-medium"
              valueColorClass="text-primary-light"
              strokeColor="#6366F1"
              ringGlow={true}
              cachedPercent={iCachePercent}
              inputTokens={iInput}
              cacheTokens={iCache}
              ratio={iRatio}
              n={iN}
            />
          </div>
        </CardContent>
      </div>

      <CardFooter className="pt-0 pb-5">
        <div className="w-full p-3 bg-card/70 border border-surface-border rounded-lg text-xs text-muted-foreground leading-relaxed font-mono">
          <span className="text-primary-light font-semibold">ICM Context Isolation Advantage:</span>{' '}
          ICM achieves <span className="text-white font-medium">{iRatio.toFixed(2)}x ({iCachePercent.toFixed(1)}% cached)</span> vs.{' '}
          baseline's <span className="text-baseline font-medium">{bRatio.toFixed(2)}x ({bCachePercent.toFixed(1)}% cached)</span> by maintaining
          stable AST prefixes across CLI turns.
        </div>
      </CardFooter>
    </Card>
  );
};
