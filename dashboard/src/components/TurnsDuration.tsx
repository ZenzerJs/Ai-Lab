import React from 'react';
import { TaskSummaryItem } from '../types';
import { Clock, GitCommit, AlertCircle } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from './ui/card';
import { Empty, EmptyIcon, EmptyTitle, EmptyDescription } from './ui/empty';

interface TurnsDurationProps {
  tasks: TaskSummaryItem[];
}

interface MeterRow {
  taskId: string;
  baselineValue: number;
  icmValue: number;
  baselineN: number;
  icmN: number;
  saved: number;
}

/** Split horizontal bar meters ported from the code.html prototype (Base share vs ICM share per task). */
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

  const toRows = (
    pickBaseline: (t: TaskSummaryItem) => number,
    pickIcm: (t: TaskSummaryItem) => number,
  ): MeterRow[] =>
    tasks.map((t) => {
      const b = t.arms.baseline;
      const i = t.arms.icm;
      const baselineValue = pickBaseline(t);
      const icmValue = pickIcm(t);
      return {
        taskId: t.task_id,
        baselineValue,
        icmValue,
        baselineN: b?.n ?? 0,
        icmN: i?.n ?? 0,
        saved: Number((baselineValue - icmValue).toFixed(1)),
      };
    });

  const turnsRows = toRows(
    (t) => Number((t.arms.baseline?.mean_num_turns ?? 0).toFixed(1)),
    (t) => Number((t.arms.icm?.mean_num_turns ?? 0).toFixed(1)),
  );

  const durationRows = toRows(
    (t) => Number((t.arms.baseline?.mean_duration_seconds ?? 0).toFixed(1)),
    (t) => Number((t.arms.icm?.mean_duration_seconds ?? 0).toFixed(1)),
  );

  const renderMeter = (rows: MeterRow[], unit: string) => {
    const max = Math.max(1e-9, ...rows.map((r) => Math.max(r.baselineValue, r.icmValue)));
    return (
      <div className="space-y-3">
        {rows.map((r) => {
          const basePct = (r.baselineValue / max) * 100;
          const icmPct = (r.icmValue / max) * 100;
          const total = basePct + icmPct || 1;
          const baseShare = (basePct / total) * 100;
          const icmShare = (icmPct / total) * 100;
          return (
            <div
              key={r.taskId}
              data-task-id={r.taskId}
              className="interactive-task-row p-2 rounded border border-transparent cursor-pointer transition-opacity hover:border-surface-border/40"
            >
              <div className="flex justify-between text-muted-foreground mb-1 text-xs gap-2 flex-wrap">
                <span>{r.taskId}</span>
                <span>
                  Base: <span className="text-baseline font-medium tabular-nums">{r.baselineValue.toFixed(1)}{unit}</span>{' '}
                  vs ICM: <span className="text-primary-light font-medium tabular-nums">{r.icmValue.toFixed(1)}{unit}</span>
                  {r.saved > 0 && (
                    <span className="text-sage ml-1.5 tabular-nums">(-{r.saved.toFixed(1)}{unit})</span>
                  )}
                </span>
              </div>
              <div className="h-2 w-full bg-background rounded flex overflow-hidden border border-surface-border/40">
                <div className="bg-baseline/80 h-full" style={{ width: `${baseShare}%` }} />
                <div className="bg-primary h-full" style={{ width: `${icmShare}%` }} />
              </div>
            </div>
          );
        })}
        <div className="flex justify-between text-[10px] text-muted-foreground font-mono pt-1">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-sm bg-baseline inline-block" /> Baseline arm (n={rows[0]?.baselineN ?? 0})
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-sm bg-primary inline-block" /> ICM arm (n={rows[0]?.icmN ?? 0})
          </span>
        </div>
      </div>
    );
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
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 font-mono text-xs">
          {/* Turns meters */}
          <div className="bg-background/40 border border-surface-border/80 rounded-lg p-3.5 flex flex-col gap-2">
            <div className="flex justify-between items-center">
              <span className="text-white font-medium flex items-center gap-1.5">
                <GitCommit className="size-3.5 text-primary" />
                Mean Conversational Turns
              </span>
              <span className="text-sage text-[11px] font-medium">Lower is better</span>
            </div>
            {renderMeter(turnsRows, '')}
          </div>

          {/* Latency meters */}
          <div className="bg-background/40 border border-surface-border/80 rounded-lg p-3.5 flex flex-col gap-2">
            <div className="flex justify-between items-center">
              <span className="text-white font-medium flex items-center gap-1.5">
                <Clock className="size-3.5 text-sage" />
                Mean Wall-Clock Latency (Seconds)
              </span>
              <span className="text-sage text-[11px] font-medium">Lower is better</span>
            </div>
            {renderMeter(durationRows, 's')}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
