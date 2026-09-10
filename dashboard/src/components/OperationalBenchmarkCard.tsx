import React from 'react';
import { OperationalBenchmark } from '../types';
import { Activity, AlertTriangle, CheckCircle2, Clock, GitCommit } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { Empty, EmptyIcon, EmptyTitle, EmptyDescription } from './ui/empty';

interface OperationalBenchmarkProps {
  ops?: OperationalBenchmark;
}

/** EXP-005 operational benchmark: turns/duration/defect comparison for the GLM 5.3 Flash runs (no token telemetry exists for this provider). */
export const OperationalBenchmarkCard: React.FC<OperationalBenchmarkProps> = ({ ops }) => {
  if (!ops || !ops.has_data || !ops.summary) {
    return (
      <Card>
        <CardContent className="p-0">
          <Empty>
            <EmptyIcon>
              <Activity className="size-6 text-muted-foreground" />
            </EmptyIcon>
            <EmptyTitle>No operational benchmark data available</EmptyTitle>
            <EmptyDescription>
              Execute the EXP-005 GLM 5.3 Flash group to record turns, duration, and outcome telemetry.
            </EmptyDescription>
          </Empty>
        </CardContent>
      </Card>
    );
  }

  const { baseline, icm, duration_overhead_percent } = ops.summary;
  const maxDur = Math.max(baseline.total_duration_seconds, icm.total_duration_seconds, 1);

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="flex flex-col gap-1 pb-3">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <Activity className="size-4 text-warning" />
            <CardTitle>Operational Benchmark (EXP-005)</CardTitle>
          </div>
          <Badge variant="outline" className="font-normal font-mono text-xs border-warning/40 text-warning bg-warning/10">
            {ops.model ?? 'glm-5.3-flash'} · {ops.provider ?? 'FreeBuff'}
          </Badge>
        </div>
        <CardDescription>
          {ops.mode ?? 'Operational telemetry'} — provider exposes no token accounting, so no USD/token figures are derived here.
        </CardDescription>
      </CardHeader>

      <CardContent className="pt-4 flex flex-col gap-5">
        {/* Headline comparison */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="p-3 rounded-lg bg-background/60 border border-surface-border flex flex-col gap-1">
            <span className="text-[11px] uppercase tracking-wide text-muted-foreground font-mono flex items-center gap-1.5">
              <Clock className="size-3" /> Total Duration
            </span>
            <span className="text-lg font-bold font-mono text-baseline tabular-nums">
              {baseline.total_duration_seconds.toFixed(1)}s
            </span>
            <span className="text-[11px] font-mono text-primary-light tabular-nums">
              vs ICM {icm.total_duration_seconds.toFixed(1)}s
            </span>
            {duration_overhead_percent !== undefined && (
              <span className="text-[10px] text-warning font-mono">ICM +{duration_overhead_percent.toFixed(0)}% overhead</span>
            )}
          </div>

          <div className="p-3 rounded-lg bg-background/60 border border-surface-border flex flex-col gap-1">
            <span className="text-[11px] uppercase tracking-wide text-muted-foreground font-mono flex items-center gap-1.5">
              <GitCommit className="size-3" /> Conversational Turns
            </span>
            <span className="text-lg font-bold font-mono text-baseline tabular-nums">{baseline.total_turns}</span>
            <span className="text-[11px] font-mono text-primary-light tabular-nums">vs ICM {icm.total_turns}</span>
            <span className="text-[10px] text-muted-foreground font-mono">4 stage turns per ICM run</span>
          </div>

          <div className="p-3 rounded-lg bg-background/60 border border-sage/30 flex flex-col gap-1">
            <span className="text-[11px] uppercase tracking-wide text-muted-foreground font-mono flex items-center gap-1.5">
              <AlertTriangle className="size-3" /> Defect Runs
            </span>
            <span className="text-lg font-bold font-mono text-baseline tabular-nums">{baseline.defect_runs}/8</span>
            <span className="text-[11px] font-mono text-sage tabular-nums">vs ICM {icm.defect_runs}/8</span>
            <span className="text-[10px] text-sage font-mono flex items-center gap-1">
              <CheckCircle2 className="size-3" /> ICM 100% clean
            </span>
          </div>
        </div>

        {/* Per-task bars */}
        {ops.tasks && ops.tasks.length > 0 && (
          <div className="space-y-3 font-mono text-xs">
            {ops.tasks.map((t) => {
              const bDur = t.baseline?.mean_duration_seconds ?? 0;
              const iDur = t.icm?.mean_duration_seconds ?? 0;
              const bPct = (bDur / maxDur) * 100;
              const iPct = (iDur / maxDur) * 100;
              return (
                <div key={t.task_id} className="p-2 rounded-lg border border-surface-border/40 bg-card/50">
                  <div className="flex justify-between mb-1.5 gap-2 flex-wrap">
                    <span className="text-gray-200 font-medium">{t.task_id}</span>
                    <span className="text-muted-foreground tabular-nums">
                      Base {bDur.toFixed(1)}s · ICM {iDur.toFixed(1)}s
                    </span>
                  </div>
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="w-10 text-[10px] text-muted-foreground shrink-0">Base</span>
                      <div className="flex-1 h-2.5 bg-background rounded overflow-hidden border border-surface-border/40">
                        <div className="bg-baseline h-full rounded-sm" style={{ width: `${bPct}%` }} />
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="w-10 text-[10px] text-muted-foreground shrink-0">ICM</span>
                      <div className="flex-1 h-2.5 bg-background rounded overflow-hidden border border-surface-border/40">
                        <div className="bg-primary h-full rounded-sm" style={{ width: `${iPct}%` }} />
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        <div className="p-3 bg-background/60 rounded-lg border border-surface-border text-xs text-muted-foreground leading-relaxed font-mono">
          <span className="text-warning font-semibold">Reading:</span> ICM adds stage-contract overhead (
          {duration_overhead_percent !== undefined ? `+${duration_overhead_percent.toFixed(0)}%` : 'slower'} wall-clock, 2× turns) but
          eliminated both shipped defects (baseline wall-clock bug, AST visitor bug). Reliability vs. latency trade-off — cost-per-working-delivery narrows the gap.
        </div>
      </CardContent>
    </Card>
  );
};
