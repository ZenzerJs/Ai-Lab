import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from 'recharts';
import { TaskSummaryItem } from '../types';
import { Clock, GitCommit, AlertCircle } from 'lucide-react';

interface TurnsDurationProps {
  tasks: TaskSummaryItem[];
}

export const TurnsDuration: React.FC<TurnsDurationProps> = ({ tasks }) => {
  if (!tasks || tasks.length === 0) {
    return (
      <div className="bg-surface border border-surface-border rounded-xl p-6 text-center">
        <AlertCircle className="w-8 h-8 text-gray-500 mx-auto mb-2" />
        <p className="text-gray-400 text-sm">No turn & duration data available.</p>
      </div>
    );
  }

  const turnsData = tasks.map((t) => {
    const b = t.arms.baseline;
    const i = t.arms.icm;
    return {
      taskId: t.task_id,
      baselineTurns: Number((b?.mean_num_turns ?? 0).toFixed(1)),
      baselineN: b?.n ?? 0,
      icmTurns: Number((i?.mean_num_turns ?? 0).toFixed(1)),
      icmN: i?.n ?? 0,
      turnsSaved: Number(((b?.mean_num_turns ?? 0) - (i?.mean_num_turns ?? 0)).toFixed(1)),
    };
  });

  const durationData = tasks.map((t) => {
    const b = t.arms.baseline;
    const i = t.arms.icm;
    return {
      taskId: t.task_id,
      baselineDuration: Number((b?.mean_duration_seconds ?? 0).toFixed(1)),
      baselineN: b?.n ?? 0,
      icmDuration: Number((i?.mean_duration_seconds ?? 0).toFixed(1)),
      icmN: i?.n ?? 0,
      durationSaved: Number(((b?.mean_duration_seconds ?? 0) - (i?.mean_duration_seconds ?? 0)).toFixed(1)),
    };
  });

  const CustomTurnsTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const d = payload[0].payload;
      return (
        <div className="bg-surface-hover border border-surface-border p-2.5 rounded shadow-lg text-xs space-y-1">
          <div className="font-semibold text-white">Task: {label}</div>
          <div className="text-red-400">Baseline (n={d.baselineN}): {d.baselineTurns} turns</div>
          <div className="text-blue-400">ICM (n={d.icmN}): {d.icmTurns} turns</div>
          <div className="text-emerald-300 pt-1 border-t border-surface-border">Saved: {d.turnsSaved} turns</div>
        </div>
      );
    }
    return null;
  };

  const CustomDurationTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const d = payload[0].payload;
      return (
        <div className="bg-surface-hover border border-surface-border p-2.5 rounded shadow-lg text-xs space-y-1">
          <div className="font-semibold text-white">Task: {label}</div>
          <div className="text-red-400">Baseline (n={d.baselineN}): {d.baselineDuration}s</div>
          <div className="text-emerald-400">ICM (n={d.icmN}): {d.icmDuration}s</div>
          <div className="text-emerald-300 pt-1 border-t border-surface-border">Saved: {d.durationSaved}s</div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="bg-surface border border-surface-border rounded-xl p-5 shadow-sm">
      <div className="pb-3 border-b border-surface-border">
        <h2 className="text-base font-semibold text-white flex items-center gap-2">
          <Clock className="w-4 h-4 text-primary" />
          Execution Overhead: Turns & Duration Telemetry
        </h2>
        <p className="text-xs text-gray-400 mt-0.5">
          Comparing conversational round-trips and wall-clock execution latency between baseline and ICM arms.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-4">
        {/* Turns Chart */}
        <div className="bg-background/40 border border-surface-border/80 rounded-lg p-3">
          <div className="flex justify-between items-center mb-2">
            <span className="text-xs font-semibold text-gray-300 flex items-center gap-1.5">
              <GitCommit className="w-3.5 h-3.5 text-primary" />
              Mean Conversational Turns
            </span>
            <span className="text-[11px] font-mono text-gray-400">Lower is better</span>
          </div>

          <div className="h-52 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={turnsData} margin={{ top: 15, right: 10, left: -15, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#21262d" vertical={false} />
                <XAxis dataKey="taskId" stroke="#8b949e" fontSize={11} tickLine={false} />
                <YAxis stroke="#8b949e" fontSize={11} tickLine={false} />
                <Tooltip content={<CustomTurnsTooltip />} />
                <Legend
                  verticalAlign="top"
                  align="right"
                  wrapperStyle={{ fontSize: '10px' }}
                  formatter={(val, entry: any) => {
                    const isB = entry.dataKey === 'baselineTurns';
                    const nList = turnsData.map((d) => (isB ? d.baselineN : d.icmN));
                    const allEqual = nList.every((v) => v === nList[0]);
                    const nLabel = allEqual ? `n=${nList[0] || 0}` : 'per-task n in tooltip';
                    return <span className="text-gray-300">{val} ({nLabel})</span>;
                  }}
                />
                <Bar name="Baseline Turns" dataKey="baselineTurns" fill="#f85149" radius={[3, 3, 0, 0]} />
                <Bar name="ICM Turns" dataKey="icmTurns" fill="#388bfd" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Duration Chart */}
        <div className="bg-background/40 border border-surface-border/80 rounded-lg p-3">
          <div className="flex justify-between items-center mb-2">
            <span className="text-xs font-semibold text-gray-300 flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-emerald-400" />
              Mean Wall-Clock Latency (Seconds)
            </span>
            <span className="text-[11px] font-mono text-gray-400">Lower is better</span>
          </div>

          <div className="h-52 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={durationData} margin={{ top: 15, right: 10, left: -15, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#21262d" vertical={false} />
                <XAxis dataKey="taskId" stroke="#8b949e" fontSize={11} tickLine={false} />
                <YAxis stroke="#8b949e" fontSize={11} tickLine={false} tickFormatter={(v) => `${v}s`} />
                <Tooltip content={<CustomDurationTooltip />} />
                <Legend
                  verticalAlign="top"
                  align="right"
                  wrapperStyle={{ fontSize: '10px' }}
                  formatter={(val, entry: any) => {
                    const isB = entry.dataKey === 'baselineDuration';
                    const nList = durationData.map((d) => (isB ? d.baselineN : d.icmN));
                    const allEqual = nList.every((v) => v === nList[0]);
                    const nLabel = allEqual ? `n=${nList[0] || 0}` : 'per-task n in tooltip';
                    return <span className="text-gray-300">{val} ({nLabel})</span>;
                  }}
                />
                <Bar name="Baseline Latency" dataKey="baselineDuration" fill="#f85149" radius={[3, 3, 0, 0]} />
                <Bar name="ICM Latency" dataKey="icmDuration" fill="#2ea043" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};
