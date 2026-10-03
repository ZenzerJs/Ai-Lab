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
  const updatedRuns: RunRecord[] = data.runs.map((r) => {
    const isCostUnavailable =
      r.cost_status === 'incomplete' ||
      r.cost_status === 'unavailable' ||
      r.input_tokens === null ||
      r.output_tokens === null ||
      r.cost_usd === null;

    return {
      ...r,
      model: selectedModel,
      is_simulation: true,
      cost_usd: isCostUnavailable
        ? null
        : computeCost(r.input_tokens, r.cache_read_tokens, r.output_tokens),
      cost_status: isCostUnavailable ? r.cost_status : 'simulation',
    };
  });

  // 2. Recalculate tasks
  const updatedTasks: TaskSummaryItem[] = data.tasks.map((t) => {
    const taskRuns = updatedRuns.filter((r) => r.task_id === t.task_id);

    const updateArm = (armRuns: RunRecord[], prevArm?: ArmStats): ArmStats | undefined => {
      if (!prevArm || armRuns.length === 0) return prevArm;
      const qualifyingCosts = armRuns
        .filter((r) => r.is_comparison_eligible && r.cost_usd !== null)
        .map((r) => r.cost_usd as number);
      return {
        ...prevArm,
        model: selectedModel,
        mean_cost_usd: qualifyingCosts.length > 0 ? qualifyingCosts.reduce((a, b) => a + b, 0) / qualifyingCosts.length : null,
        min_cost_usd: qualifyingCosts.length > 0 ? Math.min(...qualifyingCosts) : null,
        max_cost_usd: qualifyingCosts.length > 0 ? Math.max(...qualifyingCosts) : null,
        runs: armRuns,
      };
    };

    const updatedArms: Record<string, ArmStats | undefined> = {};
    for (const [armName, armStats] of Object.entries(t.arms)) {
      if (!armStats) continue;
      const armRuns = taskRuns.filter((r) => r.arm.toLowerCase() === armName.toLowerCase());
      updatedArms[armName] = updateArm(armRuns, armStats);
    }

    const baselineArm = updatedArms.baseline;
    const govArmName =
      'icm-subagents' in updatedArms
        ? 'icm-subagents'
        : 'icm' in updatedArms
        ? 'icm'
        : 'delegation' in updatedArms
        ? 'delegation'
        : Object.keys(updatedArms).find((k) => k !== 'baseline');
    const govArm = govArmName ? updatedArms[govArmName] : undefined;

    let newSavings = t.savings;
    if (baselineArm && govArm && baselineArm.mean_cost_usd !== null && govArm.mean_cost_usd !== null) {
      const costDiff = baselineArm.mean_cost_usd - govArm.mean_cost_usd;
      const costPct =
        baselineArm.mean_cost_usd > 0
          ? (costDiff / baselineArm.mean_cost_usd) * 100
          : null;

      const baseTokens = baselineArm.mean_total_tokens;
      const icmTokens = govArm.mean_total_tokens;
      const costPerMtokBase =
        baseTokens && baseTokens > 0 ? (baselineArm.mean_cost_usd / baseTokens) * 1_000_000 : null;
      const costPerMtokIcm =
        icmTokens && icmTokens > 0 ? (govArm.mean_cost_usd / icmTokens) * 1_000_000 : null;
      const savingsPerMtok =
        costPerMtokBase !== null && costPerMtokIcm !== null ? costPerMtokBase - costPerMtokIcm : null;

      newSavings = {
        ...t.savings!,
        mean_savings_usd: costDiff,
        mean_savings_percent: costPct,
        cost_per_mtok_baseline: costPerMtokBase,
        cost_per_mtok_icm: costPerMtokIcm,
        savings_usd_per_mtok: savingsPerMtok,
        projected_savings_10m: savingsPerMtok !== null ? savingsPerMtok * 10 : null,
        projected_savings_100m: savingsPerMtok !== null ? savingsPerMtok * 100 : null,
      };
    }

    return {
      ...t,
      is_simulation: true,
      arms: {
        ...t.arms,
        ...updatedArms,
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

  // Group runs by task and run_index (only eligible comparison runs)
  const taskPairs: Record<string, Record<number, Record<string, RunRecord>>> = {};
  for (const r of updatedRuns) {
    if (!r.is_comparison_eligible || r.cost_usd === null) continue;
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

  let hasValidPairs = false;

  for (const tid of Object.keys(taskPairs).sort()) {
    const indexes = taskPairs[tid];
    for (const ridxStr of Object.keys(indexes).sort((a, b) => Number(a) - Number(b))) {
      const ridx = Number(ridxStr);
      const arms = indexes[ridx];
      const bRun = arms.baseline;
      const gArmName =
        'icm-subagents' in arms
          ? 'icm-subagents'
          : 'icm' in arms
          ? 'icm'
          : 'delegation' in arms
          ? 'delegation'
          : Object.keys(arms).find((k) => k !== 'baseline');
      const gRun = gArmName ? arms[gArmName] : undefined;

      if (bRun && gRun && bRun.cost_usd !== null && gRun.cost_usd !== null) {
        hasValidPairs = true;
        const bCost = bRun.cost_usd;
        const iCost = gRun.cost_usd;
        const delta = bCost - iCost;
        runningSaved += delta;

        totalBaselineCost += bCost;
        totalIcmCost += iCost;
        totalBaselineTokens += bRun.total_tokens || 0;
        totalIcmTokens += gRun.total_tokens || 0;
        totalRunsCount += 2;

        updatedTimeline.push({
          step,
          label: `${tid} Run ${ridx}`,
          task_id: tid,
          run_index: ridx,
          governed_arm: gArmName,
          timestamp: gRun.timestamp,
          baseline_cost_usd: bCost,
          icm_cost_usd: iCost,
          delta_saved_usd: delta,
          cumulative_savings_usd: runningSaved,
        });
        step++;
      }
    }
  }

  const measuredSavings = hasValidPairs ? totalBaselineCost - totalIcmCost : null;
  const savingsPct =
    hasValidPairs && totalBaselineCost > 0
      ? (measuredSavings! / totalBaselineCost) * 100
      : null;
  const costPerMtokBase =
    hasValidPairs && totalBaselineTokens > 0
      ? (totalBaselineCost / totalBaselineTokens) * 1_000_000
      : null;
  const costPerMtokIcm =
    hasValidPairs && totalIcmTokens > 0 ? (totalIcmCost / totalIcmTokens) * 1_000_000 : null;
  const savingsPerMtok =
    costPerMtokBase !== null && costPerMtokIcm !== null ? costPerMtokBase - costPerMtokIcm : null;

  const updatedCumulative: CumulativeSummary = {
    ...data.cumulative,
    is_simulation: true,
    total_runs: totalRunsCount,
    total_baseline_cost_usd: hasValidPairs ? totalBaselineCost : null,
    total_icm_cost_usd: hasValidPairs ? totalIcmCost : null,
    total_baseline_tokens: hasValidPairs ? totalBaselineTokens : null,
    total_icm_tokens: hasValidPairs ? totalIcmTokens : null,
    cumulative_savings_usd: measuredSavings,
    cumulative_savings_percent: savingsPct,
    cost_per_mtok_baseline: costPerMtokBase,
    cost_per_mtok_icm: costPerMtokIcm,
    savings_usd_per_mtok: savingsPerMtok,
    projected_savings_10m: savingsPerMtok !== null ? savingsPerMtok * 10 : null,
    projected_savings_100m: savingsPerMtok !== null ? savingsPerMtok * 100 : null,
    tasks: updatedTasks,
  };

  return {
    ...data,
    is_simulation: true,
    runs: updatedRuns,
    tasks: updatedTasks,
    timeline: updatedTimeline,
    cumulative: updatedCumulative,
  };
}
