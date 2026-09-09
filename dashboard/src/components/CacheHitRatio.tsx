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

interface CacheHitRatioProps {
  tasks: TaskSummaryItem[];
}

export const CacheHitRatio: React.FC<CacheHitRatioProps> = ({ tasks }) => {
  const [selectedTaskIndex, setSelectedTaskIndex] = useState(0);

  if (!tasks || tasks.length === 0) {
    return (
      <div className="bg-surface border border-surface-border rounded-xl p-6 text-center">
        <AlertCircle className="w-8 h-8 text-gray-500 mx-auto mb-2" />
        <p className="text-gray-400 text-sm">No cache telemetry data available.</p>
      </div>
    );
  }

  const currentTask = tasks[selectedTaskIndex] || tasks[0];
  const b = currentTask.arms.baseline;
  const i = currentTask.arms.icm;

  const bInput = b?.mean_input_tokens ?? 0;
  const bCache = b?.mean_cache_read_tokens ?? 0;
  const bRatio = b?.cache_hit_ratio ?? 0;
  const bN = b?.n ?? 0;

  const iInput = i?.mean_input_tokens ?? 0;
  const iCache = i?.mean_cache_read_tokens ?? 0;
  const iRatio = i?.cache_hit_ratio ?? 0;
  const iN = i?.n ?? 0;

  // Pie chart datasets
  const baselinePieData = [
    { name: 'Fresh Input Tokens', value: Math.round(bInput), color: '#f85149' },
    { name: 'Cache Read Tokens', value: Math.round(bCache), color: '#ffa198' },
  ];

  const icmPieData = [
    { name: 'Fresh Input Tokens', value: Math.round(iInput), color: '#3fb950' },
    { name: 'Cache Read Tokens', value: Math.round(iCache), color: '#238636' },
  ];

  const CustomPieTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0];
      return (
        <div className="bg-surface-hover border border-surface-border p-2.5 rounded-md shadow-lg text-xs">
          <span className="font-semibold text-white">{data.name}:</span>{' '}
          <span className="font-mono text-gray-300">{Number(data.value).toLocaleString()} tokens</span>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="bg-surface border border-surface-border rounded-xl p-5 shadow-sm flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between pb-3 border-b border-surface-border">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-warning" />
            <h2 className="text-base font-semibold text-white">Cache Hit Ratio & Token Distribution</h2>
          </div>

          {tasks.length > 1 && (
            <select
              value={selectedTaskIndex}
              onChange={(e) => setSelectedTaskIndex(Number(e.target.value))}
              className="bg-background border border-surface-border text-xs text-gray-200 rounded px-2 py-1 font-mono focus:outline-none focus:border-primary"
            >
              {tasks.map((t, idx) => (
                <option key={t.task_id} value={idx}>
                  Task {t.task_id}
                </option>
              ))}
            </select>
          )}
        </div>

        <p className="text-xs text-gray-400 mt-2">
          Ratio of prompt cache reads to fresh input tokens (<code className="text-gray-300">cache_read / input</code>).
          High cache ratios dramatically reduce effective token pricing.
        </p>

        {/* Dual Donut Visualizer */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
          {/* Baseline Donut */}
          <div className="flex flex-col items-center bg-background/40 border border-surface-border/80 rounded-lg p-3">
            <div className="text-xs font-semibold text-gray-300 flex items-center justify-between w-full pb-1 border-b border-surface-border/50">
              <span className="text-red-400">Baseline Arm</span>
              <span className="text-gray-400 font-mono text-[11px]">(n={bN})</span>
            </div>

            <div className="w-36 h-36 relative mt-2">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Tooltip content={<CustomPieTooltip />} />
                  <Pie
                    data={baselinePieData}
                    innerRadius={36}
                    outerRadius={56}
                    paddingAngle={3}
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
                  {(bRatio * 100).toFixed(1)}%
                </span>
                <span className="text-[9px] text-gray-500 uppercase tracking-tight">Hit Ratio</span>
              </div>
            </div>

            <div className="w-full mt-2 space-y-1 text-[11px] text-gray-400 font-mono">
              <div className="flex justify-between">
                <span>Fresh Input:</span>
                <span className="text-gray-200">{Math.round(bInput).toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span>Cache Read:</span>
                <span className="text-red-300">{Math.round(bCache).toLocaleString()}</span>
              </div>
            </div>
          </div>

          {/* ICM Donut */}
          <div className="flex flex-col items-center bg-background/40 border border-surface-border/80 rounded-lg p-3">
            <div className="text-xs font-semibold text-gray-300 flex items-center justify-between w-full pb-1 border-b border-surface-border/50">
              <span className="text-emerald-400">ICM Pipeline</span>
              <span className="text-gray-400 font-mono text-[11px]">(n={iN})</span>
            </div>

            <div className="w-36 h-36 relative mt-2">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Tooltip content={<CustomPieTooltip />} />
                  <Pie
                    data={icmPieData}
                    innerRadius={36}
                    outerRadius={56}
                    paddingAngle={3}
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
                  {(iRatio * 100).toFixed(1)}%
                </span>
                <span className="text-[9px] text-gray-500 uppercase tracking-tight">Hit Ratio</span>
              </div>
            </div>

            <div className="w-full mt-2 space-y-1 text-[11px] text-gray-400 font-mono">
              <div className="flex justify-between">
                <span>Fresh Input:</span>
                <span className="text-gray-200">{Math.round(iInput).toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span>Cache Read:</span>
                <span className="text-emerald-400">{Math.round(iCache).toLocaleString()}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-4 pt-3 border-t border-surface-border text-xs bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-3">
        <span className="font-semibold text-emerald-400">ICM Context Isolation Advantage:</span>{' '}
        <span className="text-gray-300">
          ICM achieves a <span className="font-mono font-bold text-emerald-300">{(iRatio * 100).toFixed(1)}%</span> cache hit ratio vs.
          baseline's <span className="font-mono font-bold text-red-300">{(bRatio * 100).toFixed(1)}%</span> by keeping system prompts and OKF slices deterministic across stage boundaries.
        </span>
      </div>
    </div>
  );
};
