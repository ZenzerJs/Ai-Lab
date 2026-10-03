export interface OperationalArmSummary {
  runs: number;
  total_turns: number;
  total_duration_seconds: number;
  defect_runs: number;
}

export interface OperationalTaskArm {
  n: number;
  mean_turns: number;
  mean_duration_seconds: number;
}

export interface OperationalTask {
  task_id: string;
  baseline?: OperationalTaskArm;
  icm?: OperationalTaskArm;
}

export interface OperationalSummary {
  total_runs: number;
  baseline: OperationalArmSummary;
  icm: OperationalArmSummary;
  duration_overhead_percent?: number;
}

export interface OperationalBenchmark {
  has_data: boolean;
  model?: string;
  provider?: string;
  mode?: string;
  summary?: OperationalSummary;
  tasks?: OperationalTask[];
  runs?: {
    task_id: string;
    arm: string;
    run_index: number;
    num_turns: number;
    duration_seconds: number;
    timestamp: string;
  }[];
}

export interface RunRecord {
  id: number;
  task_id: string;
  arm: 'baseline' | 'icm' | 'icm-subagents' | 'delegation' | string;
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
  cost_usd: number | null;
  cost_status?: 'usage_estimate' | 'simulation' | 'incomplete' | 'unavailable' | 'unknown' | string;
  source_kind?: 'live' | 'fixture' | 'imported' | 'unknown' | string;
  evidence_status?: 'verified' | 'unverified' | 'invalid' | 'missing' | string;
  exclusion_reasons?: string[];
  is_eligible?: boolean;
  is_comparison_eligible?: boolean;
  is_simulation?: number | boolean;
  execution_status?: 'completed' | 'failed' | 'timed_out' | 'unexecuted' | 'interrupted' | string;
  verification_status?: 'passed' | 'failed' | 'evaluator_error' | 'not_run' | string;
  evidence_ref?: string;
  notes?: string;
}

export interface ArmStats {
  n: number;
  scheduled_count?: number;
  completed_count?: number;
  verified_count?: number;
  failed_count?: number;
  excluded_count?: number;
  cost_eligible_count?: number;
  cost_complete_n?: number;
  exclusion_reasons?: string[];
  source_kinds?: string[];
  evidence_statuses?: string[];
  model: string;
  mean_cost_usd: number | null;
  min_cost_usd: number | null;
  max_cost_usd: number | null;
  mean_input_tokens: number | null;
  mean_cache_read_tokens: number | null;
  mean_output_tokens: number | null;
  mean_thinking_tokens?: number | null;
  mean_total_tokens: number | null;
  mean_num_turns: number;
  mean_duration_seconds: number;
  cache_hit_ratio: number;
  runs: RunRecord[];
}

export interface TaskSavings {
  mean_savings_usd: number | null;
  mean_savings_percent: number | null;
  mean_total_tokens_saved?: number | null;
  mean_thinking_tokens_saved?: number | null;
  mean_turns_saved?: number | null;
  mean_duration_seconds_saved?: number | null;
  cache_hit_ratio_baseline: number;
  cache_hit_ratio_icm: number;
  cost_per_mtok_baseline?: number | null;
  cost_per_mtok_icm?: number | null;
  savings_usd_per_mtok?: number | null;
  projected_savings_10m?: number | null;
  projected_savings_100m?: number | null;
}

export interface TaskSummaryItem {
  task_id: string;
  total_runs: number;
  has_measured_data?: boolean;
  is_demo_report?: boolean;
  is_simulation?: boolean;
  status?: string;
  measured_runs_count?: number;
  comparison_eligible_runs_count?: number;
  passed_runs_count?: number;
  failed_runs_count?: number;
  unverified_runs_count?: number;
  cost_incomplete_runs_count?: number;
  fixture_runs_count?: number;
  historical_runs_count?: number;
  imported_runs_count?: number;
  simulated_runs_count?: number;
  excluded_runs?: RunRecord[];
  governed_arm?: string;
  cost_eligible_count?: number;
  scheduled_count?: number;
  completed_count?: number;
  verified_count?: number;
  failed_count?: number;
  excluded_count?: number;
  source_kinds?: string[];
  evidence_statuses?: string[];
  exclusion_reasons?: string[];
  arms: {
    baseline?: ArmStats;
    icm?: ArmStats;
    [key: string]: ArmStats | undefined;
  };
  savings?: TaskSavings | null;
}

export interface PerArmAggregatedCounts {
  scheduled: number;
  completed: number;
  verified: number;
  failed: number;
  excluded: number;
  cost_eligible: number;
  exclusion_reasons?: string[];
}

export interface CumulativeSummary {
  tasks_evaluated: number;
  total_tasks?: number;
  total_runs: number;
  has_measured_data?: boolean;
  is_demo_report?: boolean;
  is_simulation?: boolean;
  scheduled_count?: number;
  completed_count?: number;
  verified_count?: number;
  failed_count?: number;
  excluded_count?: number;
  per_arm_counts?: Record<string, PerArmAggregatedCounts>;
  source_kind_counts?: Record<string, number>;
  evidence_status_counts?: Record<string, number>;
  fixture_runs_count?: number;
  historical_runs_count?: number;
  imported_runs_count?: number;
  simulated_runs_count?: number;
  passed_runs_count?: number;
  failed_runs_count?: number;
  cost_incomplete_runs_count?: number;
  comparison_eligible_runs_count?: number;
  total_baseline_cost_usd: number | null;
  total_icm_cost_usd: number | null;
  total_baseline_tokens?: number | null;
  total_icm_tokens?: number | null;
  cumulative_savings_usd: number | null;
  cumulative_savings_percent: number | null;
  pct_saved_usd?: number | null;
  baseline_cache_hit_pct?: number | null;
  icm_cache_hit_pct?: number | null;
  cost_per_mtok_baseline?: number | null;
  cost_per_mtok_icm?: number | null;
  savings_usd_per_mtok?: number | null;
  projected_savings_10m?: number | null;
  projected_savings_100m?: number | null;
  tasks: TaskSummaryItem[];
}

export interface TimelinePoint {
  step: number;
  label: string;
  task_id: string;
  run_index: number;
  governed_arm?: string;
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
  pricing_mode?: string;
  provider_note?: string;
}

export interface ModelCascadeItem {
  model: string;
  input_usd_per_mtok: number;
  cache_read_usd_per_mtok: number;
  output_usd_per_mtok: number;
  pricing_mode?: string | null;
  provider_note?: string | null;
  total_baseline_cost_usd: number | null;
  total_icm_cost_usd: number | null;
  cumulative_savings_usd: number | null;
  cumulative_savings_percent: number | null;
  cost_per_mtok_baseline: number | null;
  cost_per_mtok_icm: number | null;
  savings_usd_per_mtok: number | null;
  projected_savings_10m: number | null;
  projected_savings_100m: number | null;
  projected_savings_1b: number | null;
  source_url: string;
}

export interface DashboardPayload {
  operational?: OperationalBenchmark;
  generated_at: string;
  has_data: boolean;
  is_demo_report?: boolean;
  is_simulation?: boolean;
  campaign?: any;
  cumulative: CumulativeSummary;
  tasks: TaskSummaryItem[];
  runs: RunRecord[];
  timeline: TimelinePoint[];
  pricing: PricingRecord[];
  cascade?: ModelCascadeItem[];
}
