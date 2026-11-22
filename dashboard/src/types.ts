export interface OperationalArmSummary {
  runs: number;
  total_turns: number;
  total_duration_seconds: number;
  defect_runs: number | null;
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

export type ScaleMode = '1x' | '1m' | '10m' | '100m';

export type ArmName = 'baseline' | 'icm' | 'icm_lite' | 'icm-subagents' | 'delegation' | (string & {});

export type CostSource = 'billed_direct' | 'estimated_acu_derived' | 'unavailable';

export interface RunRecord {
  id: number;
  task_id: string;
  arm: ArmName;
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
  cost_status?: 'usage_estimate' | 'estimated_acu_derived' | 'simulation' | 'incomplete' | 'unavailable' | 'unknown' | string;
  cost_source?: CostSource | string;
  acus_consumed?: number | null;
  acu_usd_rate?: number | null;
  estimated_cost_usd?: number | null;
  source_kind?: 'live' | 'fixture' | 'imported' | 'unknown' | string;
  evidence_status?: 'verified' | 'unverified' | 'invalid' | 'missing' | string;
  exclusion_reasons?: string[];
  is_eligible?: boolean;
  is_comparison_eligible?: boolean;
  is_simulation?: number | boolean;
  execution_status?: 'completed' | 'failed' | 'timed_out' | 'unexecuted' | 'interrupted' | string;
  verification_status?: 'passed' | 'failed' | 'evaluator_error' | 'not_run' | string;
  evaluator_hash?: string | null;
  manifest_id?: string | null;
  evidence_ref?: string;
  notes?: string;
  tool_calls_count?: number | null;
  tool_errors_count?: number | null;
  max_consecutive_tool_streak?: number | null;
  loop_detected?: boolean | number | null;
}

export interface ArmStats {
  n: number;
  scheduled_count?: number;
  evaluated_count?: number;
  completed_count?: number;
  verified_count?: number;
  passed_count?: number;
  pass_rate?: number | null;
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
  cost_per_passing_patch_usd?: number | null;
  tokens_per_passing_patch?: number | null;
  total_tool_calls?: number;
  total_tool_errors?: number;
  loop_runs_count?: number;
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
  model?: string;
  series_id?: string;
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
  governed_arm?: ArmName;
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
    icm_lite?: ArmStats;
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
  thinking_tokens_saved_percent?: number | null;
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
  is_simulation?: boolean;
  counter_semantics_qualification?: string | null;
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

export interface HeadlineStat {
  id: string;
  label: string;
  value: number | string;
  unit: string;
  baseline: string;
  icm: string;
  n_baseline: number;
  n_icm: number;
  n_tasks: number;
  source: string;
  cost_basis?: string | null;
  ci95?: [number, number] | null;
  cost_delta_pct?: number | null;
  signed_cost_label?: string | null;
  pooling_method?: string | null;
  macro_average_savings_pct?: number | null;
  priced_run_count?: number | null;
  total_run_count?: number | null;
}

export interface HeadlineScope {
  unique_task_count: number;
  paired_priced_task_count: number;
  total_run_count: number;
  priced_run_count: number;
  billed_direct_run_count?: number;
  estimated_acu_derived_run_count?: number;
  unpriced_run_count?: number;
  cost_basis?: string;
  pooling_method: string;
  macro_average_savings_pct?: number | null;
  pooling_note: string;
  signed_cost_label?: string | null;
  cost_delta_pct?: number | null;
  savings_pct?: number | null;
}

export interface HeadlineBlock {
  sentence: string | null;
  scope?: HeadlineScope | null;
  stats: HeadlineStat[];
}

export interface DeclaredBenchmarkStatus {
  task_id: string;
  measured_runs: number;
  status: string;
}

export interface QualityDimensionCI {
  mean_delta: number | null;
  ci_95: [number, number] | null;
  n: number;
}

export interface QualityScoreRecord {
  correctness: number;
  engineering: number;
  maintainability: number;
  process: number;
  design: number | null;
  total: number;
  max_possible: number;
  normalized_pct: number;
}

export interface MultiFileOutlineItem {
  task_id: string;
  title: string;
  files: number;
  baseline_turns: number;
  icm_turns: number;
  baseline_cost_usd: number;
  icm_cost_raw_usd: number;
  icm_cost_normalized_usd: number;
  raw_savings_percent: number;
  normalized_savings_percent: number;
}

export interface QualityRubricBlock {
  has_data: boolean;
  tasks: {
    task_id: string;
    baseline: QualityScoreRecord;
    governed: QualityScoreRecord;
  }[];
  quality_ci: {
    correctness: QualityDimensionCI;
    engineering: QualityDimensionCI;
    maintainability: QualityDimensionCI;
    process: QualityDimensionCI;
    design: QualityDimensionCI;
    normalized_pct: QualityDimensionCI;
    sample_count: number;
  };
  multi_file_outlines?: MultiFileOutlineItem[];
  tool_errors?: {
    baseline: number;
    icm: number;
    reduction_percent: number | null;
  } | null;
}

export type QualityRubricData = QualityRubricBlock;

export interface DashboardPayload {
  operational?: OperationalBenchmark;
  quality_rubric?: QualityRubricBlock | null;
  generated_at: string;
  build_identity?: string;
  has_data: boolean;
  is_demo_report?: boolean;
  is_simulation?: boolean;
  headline?: HeadlineBlock | null;
  declared_benchmarks?: DeclaredBenchmarkStatus[] | null;
  campaign?: any;
  cumulative: CumulativeSummary;
  tasks: TaskSummaryItem[];
  runs: RunRecord[];
  timeline: TimelinePoint[];
  pricing: PricingRecord[];
  acu_pricing?: {
    devin_acu_usd_rate: number;
    default_rate: number;
    currency: string;
  };
  cascade?: ModelCascadeItem[];
}
