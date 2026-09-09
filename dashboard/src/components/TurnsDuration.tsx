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
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { Empty, EmptyIcon, EmptyTitle, EmptyDescription } from './ui/empty';

interface TurnsDurationProps {
  tasks: TaskSummaryItem[];
}

export const TurnsDuration: React.FC<TurnsDurationProps> = ({ tasks }) => {
  if (!tasks || tasks.length === 0) {
    return (
      <Card>
        <CardContent className="p-0">
          <Empty>
            <EmptyIcon>
              <AlertCircle className="size-6 text-muted-foreground" />
            </EmptyIcon>
            <EmptyTitle>No turn & duration data available</EmptyTitle>
            <EmptyDescription>
              Conversational turn and duration telemetry will appear after executing experimental arms.
            </EmptyDescription>
          </Empty>
        </CardContent>
      </Card>
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
      const isSaved = d.turnsSaved > 0;
      const isExtra = d.turnsSaved < 0;
      return (
        <div className="bg-surface border border-surface-border p-3 rounded-lg shadow-xl text-xs flex flex-col gap-1 min-w-[180px]">
          <div className="font-semibold text-white border-b border-surface-border pb-1">Task: {label}</div>
          <div className="text-red-400">Baseline (n={d.baselineN}): {d.baselineTurns} turns</div>
          <div className="text-blue-400">ICM (n={d.icmN}): {d.icmTurns} turns</div>
          <div className="pt-1 border-t border-surface-border font-medium flex justify-between">
            <span className="text-gray-300">Delta:</span>
            <span className={isSaved ? "text-emerald-300 font-mono" : isExtra ? "text-red-300 font-mono" : "text-gray-300 font-mono"}>
              {isSaved ? `Saved ${d.turnsSaved} turns` : isExtra ? `Extra ${Math.abs(d.turnsSaved)} turns` : '0 turns delta'}
            </span>
          </div>
        </div>
      );
    }
    return null;
  };

  const CustomDurationTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const d = payload[0].payload;
      const isSaved = d.durationSaved > 0;
      const isExtra = d.durationSaved < 0;
      return (
        <div className="bg-surface border border-surface-border p-3 rounded-lg shadow-xl text-xs flex flex-col gap-1 min-w-[180px]">
          <div className="font-semibold text-white border-b border-surface-border pb-1">Task: {label}</div>
          <div className="text-red-400">Baseline (n={d.baselineN}): {d.baselineDuration}s</div>
          <div className="text-emerald-400">ICM (n={d.icmN}): {d.icmDuration}s</div>
          <div className="pt-1 border-t border-surface-border font-medium flex justify-between">
            <span className="text-gray-300">Delta:</span>
            <span className={isSaved ? "text-emerald-300 font-mono" : isExtra ? "text-red-300 font-mono" : "text-gray-300 font-mono"}>
              {isSaved ? `Saved ${d.durationSaved}s` : isExtra ? `Extra ${Math.abs(d.durationSaved)}s` : '0s delta'}
            </span>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <Clock className="size-4 text-primary" />
          <CardTitle>Execution Overhead: Turns & Duration Telemetry</CardTitle>
        </div>
        <CardDescription>
          Comparing conversational round-trips and wall-clock execution latency between baseline and ICM arms.
        </CardDescription>
      </CardHeader>

      <CardContent className="pt-4">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Turns Chart */}
          <div className="bg-background/40 border border-surface-border/80 rounded-lg p-3.5 flex flex-col gap-2">
            <div className="flex justify-between items-center">
              <span className="text-xs font-semibold text-gray-300 flex items-center gap-1.5">
                <GitCommit className="size-3.5 text-primary" />
                Mean Conversational Turns
              </span>
              <Badge variant="secondary" className="text-[10px] py-0 font-mono font-normal">Lower is better</Badge>
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
                  <Bar name="Baseline Turns" dataKey="baselineTurns" fill="#f85149" radius={[4, 4, 0, 0]} />
                  <Bar name="ICM Turns" dataKey="icmTurns" fill="#388bfd" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Duration Chart */}
          <div className="bg-background/40 border border-surface-border/80 rounded-lg p-3.5 flex flex-col gap-2">
            <div className="flex justify-between items-center">
              <span className="text-xs font-semibold text-gray-300 flex items-center gap-1.5">
                <Clock className="size-3.5 text-emerald-400" />
                Mean Wall-Clock Latency (Seconds)
              </span>
              <Badge variant="secondary" className="text-[10px] py-0 font-mono font-normal">Lower is better</Badge>
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
                  <Bar name="Baseline Latency" dataKey="baselineDuration" fill="#f85149" radius={[4, 4, 0, 0]} />
                  <Bar name="ICM Latency" dataKey="icmDuration" fill="#2ea043" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
