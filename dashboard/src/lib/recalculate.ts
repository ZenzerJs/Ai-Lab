import { DashboardPayload, RunRecord, TaskSummaryItem, ArmStats, TimelinePoint, CumulativeSummary } from '../types';

export function deriveDataForModel(
  data: DashboardPayload | null,
  selectedModel: string
): DashboardPayload | null {
  if (!data || !data.has_data || !selectedModel || selectedModel === 'recorded') {
    return data;
  }

  const rate = data.pricing.find((p) => p.model === selectedModel);
  if (!rate) {
    return data;
  }

  const computeCost = (input: number, cache: number, output: number) => {
    return (
      (input * rate.input_usd_per_mtok +
        cache * rate.cache_read_usd_per_mtok +
        output * rate.output_usd_per_mtok) /
      1_000_000
    );
  };

  // 1. Recalculate raw runs
  const updatedRuns: RunRecord[] = data.runs.map((r) => ({
    ...r,
    model: selectedModel,
    cost_usd: computeCost(r.input_tokens, r.cache_read_tokens, r.output_tokens),
  }));

  // 2. Recalculate tasks
  const updatedTasks: TaskSummaryItem[] = data.tasks.map((t) => {
    const taskRuns = updatedRuns.filter((r) => r.task_id === t.task_id);
    const bRuns = taskRuns.filter((r) => r.arm.toLowerCase() === 'baseline');
    const iRuns = taskRuns.filter((r) => r.arm.toLowerCase() === 'icm');

    const updateArm = (armRuns: RunRecord[], prevArm?: ArmStats): ArmStats | undefined => {
      if (!prevArm || armRuns.length === 0) return prevArm;
      const costs = armRuns.map((r) => r.cost_usd);
      return {
        ...prevArm,
        model: selectedModel,
        mean_cost_usd: costs.reduce((a, b) => a + b, 0) / costs.length,
        min_cost_usd: Math.min(...costs),
        max_cost_usd: Math.max(...costs),
        runs: armRuns,
      };
    };

    const newBaseline = updateArm(bRuns, t.arms.baseline);
    const newIcm = updateArm(iRuns, t.arms.icm);

    let newSavings = t.savings;
    if (newBaseline && newIcm) {
      const costDiff = newBaseline.mean_cost_usd - newIcm.mean_cost_usd;
      const costPct =
        newBaseline.mean_cost_usd > 0
          ? (costDiff / newBaseline.mean_cost_usd) * 100
          : 0;

      const baseTokens = newBaseline.mean_total_tokens;
      const icmTokens = newIcm.mean_total_tokens;
      const costPerMtokBase =
        baseTokens > 0 ? (newBaseline.mean_cost_usd / baseTokens) * 1_000_000 : 0;
      const costPerMtokIcm =
        icmTokens > 0 ? (newIcm.mean_cost_usd / icmTokens) * 1_000_000 : 0;
      const savingsPerMtok = costPerMtokBase - costPerMtokIcm;

      newSavings = {
        ...t.savings!,
        mean_savings_usd: costDiff,
        mean_savings_percent: costPct,
        cost_per_mtok_baseline: costPerMtokBase,
        cost_per_mtok_icm: costPerMtokIcm,
        savings_usd_per_mtok: savingsPerMtok,
        projected_savings_10m: savingsPerMtok * 10,
        projected_savings_100m: savingsPerMtok * 100,
      };
    }

    return {
      ...t,
      arms: {
        ...t.arms,
        baseline: newBaseline,
        icm: newIcm,
      },
      savings: newSavings,
    };
  });

  // 3. Recalculate timeline & cumulative total
  let totalBaselineCost = 0;
  let totalIcmCost = 0;
  let totalBaselineTokens = 0;
  let totalIcmTokens = 0;
  let totalRunsCount = 0;

  // Group runs by task and run_index
  const taskPairs: Record<string, Record<number, Record<string, RunRecord>>> = {};
  for (const r of updatedRuns) {
    const tid = r.task_id;
    const ridx = r.run_index;
    const arm = r.arm.toLowerCase();
    if (!taskPairs[tid]) taskPairs[tid] = {};
    if (!taskPairs[tid][ridx]) taskPairs[tid][ridx] = {};
    taskPairs[tid][ridx][arm] = r;
  }

  const updatedTimeline: TimelinePoint[] = [];
  let runningSaved = 0;
  let step = 1;

  for (const tid of Object.keys(taskPairs).sort()) {
    const indexes = taskPairs[tid];
    for (const ridxStr of Object.keys(indexes).sort((a, b) => Number(a) - Number(b))) {
      const ridx = Number(ridxStr);
      const arms = indexes[ridx];
      if (arms.baseline && arms.icm) {
        const bCost = arms.baseline.cost_usd;
        const iCost = arms.icm.cost_usd;
        const delta = bCost - iCost;
        runningSaved += delta;

        totalBaselineCost += bCost;
        totalIcmCost += iCost;
        totalBaselineTokens += arms.baseline.total_tokens;
        totalIcmTokens += arms.icm.total_tokens;
        totalRunsCount += 2;

        updatedTimeline.push({
          step,
          label: `${tid} Run ${ridx}`,
          task_id: tid,
          run_index: ridx,
          timestamp: arms.icm.timestamp,
          baseline_cost_usd: bCost,
          icm_cost_usd: iCost,
          delta_saved_usd: delta,
          cumulative_savings_usd: runningSaved,
        });
        step++;
      }
    }
  }

  const measuredSavings = totalBaselineCost - totalIcmCost;
  const savingsPct =
    totalBaselineCost > 0 ? (measuredSavings / totalBaselineCost) * 100 : 0;
  const costPerMtokBase =
    totalBaselineTokens > 0
      ? (totalBaselineCost / totalBaselineTokens) * 1_000_000
      : 0;
  const costPerMtokIcm =
    totalIcmTokens > 0 ? (totalIcmCost / totalIcmTokens) * 1_000_000 : 0;
  const savingsPerMtok = costPerMtokBase - costPerMtokIcm;

  const updatedCumulative: CumulativeSummary = {
    ...data.cumulative,
    total_runs: totalRunsCount,
    total_baseline_cost_usd: totalBaselineCost,
    total_icm_cost_usd: totalIcmCost,
    total_baseline_tokens: totalBaselineTokens,
    total_icm_tokens: totalIcmTokens,
    cumulative_savings_usd: measuredSavings,
    cumulative_savings_percent: savingsPct,
    cost_per_mtok_baseline: costPerMtokBase,
    cost_per_mtok_icm: costPerMtokIcm,
    savings_usd_per_mtok: savingsPerMtok,
    projected_savings_10m: savingsPerMtok * 10,
    projected_savings_100m: savingsPerMtok * 100,
    tasks: updatedTasks,
  };

  return {
    ...data,
    runs: updatedRuns,
    tasks: updatedTasks,
    timeline: updatedTimeline,
    cumulative: updatedCumulative,
  };
}
