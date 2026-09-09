export interface RunRecord {
  id: number;
  task_id: string;
  arm: 'baseline' | 'icm' | string;
  model: string;
  run_index: number;
  timestamp: string;
  input_tokens: number;
  output_tokens: number;
  thinking_tokens: number;
  cache_read_tokens: number;
  total_tokens: number;
  num_turns: number;
  duration_seconds: number;
  cost_usd: number;
}

export interface ArmStats {
  n: number;
  model: string;
  mean_cost_usd: number;
  min_cost_usd: number;
  max_cost_usd: number;
  mean_input_tokens: number;
  mean_cache_read_tokens: number;
  mean_output_tokens: number;
  mean_total_tokens: number;
  mean_num_turns: number;
  mean_duration_seconds: number;
  cache_hit_ratio: number;
  runs: RunRecord[];
}

export interface TaskSavings {
  mean_savings_usd: number;
  mean_savings_percent: number;
  mean_total_tokens_saved: number;
  mean_turns_saved: number;
  mean_duration_seconds_saved: number;
  cache_hit_ratio_baseline: number;
  cache_hit_ratio_icm: number;
  cost_per_mtok_baseline?: number;
  cost_per_mtok_icm?: number;
  savings_usd_per_mtok?: number;
  projected_savings_10m?: number;
  projected_savings_100m?: number;
}

export interface TaskSummaryItem {
  task_id: string;
  total_runs: number;
  arms: {
    baseline?: ArmStats;
    icm?: ArmStats;
    [key: string]: ArmStats | undefined;
  };
  savings?: TaskSavings;
}

export interface CumulativeSummary {
  tasks_evaluated: number;
  total_runs: number;
  total_baseline_cost_usd: number;
  total_icm_cost_usd: number;
  total_baseline_tokens?: number;
  total_icm_tokens?: number;
  cumulative_savings_usd: number;
  cumulative_savings_percent: number;
  cost_per_mtok_baseline?: number;
  cost_per_mtok_icm?: number;
  savings_usd_per_mtok?: number;
  projected_savings_10m?: number;
  projected_savings_100m?: number;
  tasks: TaskSummaryItem[];
}

export interface TimelinePoint {
  step: number;
  label: string;
  task_id: string;
  run_index: number;
  timestamp: string;
  baseline_cost_usd: number;
  icm_cost_usd: number;
  delta_saved_usd: number;
  cumulative_savings_usd: number;
}

export interface PricingRecord {
  model: string;
  input_usd_per_mtok: number;
  cache_read_usd_per_mtok: number;
  output_usd_per_mtok: number;
  source_url: string;
  fetched_at: string;
}

export interface DashboardPayload {
  generated_at: string;
  has_data: boolean;
  cumulative: CumulativeSummary;
  tasks: TaskSummaryItem[];
  runs: RunRecord[];
  timeline: TimelinePoint[];
  pricing: PricingRecord[];
}
