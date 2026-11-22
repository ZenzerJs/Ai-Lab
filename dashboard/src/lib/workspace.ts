import { RunRecord, TaskSummaryItem } from "../types";

export type Destination =
  "overview" | "tasks" | "simulator" | "sandboxes" | "audit" | "analytics";
export const destinations: Destination[] = [
  "overview",
  "tasks",
  "analytics",
  "simulator",
  "sandboxes",
  "audit",
];

export function readDestination(): Destination {
  const hash = window.location.hash.slice(1);
  return destinations.includes(hash as Destination)
    ? (hash as Destination)
    : "overview";
}

// Match build_data.GOVERNED_ARMS and preserve the exporter-selected comparison.
export function selectGovernedArmName(
  arms: Record<string, unknown>,
  preferred?: string,
) {
  if (preferred && preferred !== "baseline" && arms[preferred]) return preferred;
  return ["icm-subagents", "icm", "delegation", "governed", "icm_lite"].find(
    (key) => arms[key],
  ) || Object.keys(arms).find((key) => key !== "baseline" && arms[key]);
}

export function governedArmName(task: TaskSummaryItem) {
  return selectGovernedArmName(task.arms, task.governed_arm);
}

export function governedArm(task: TaskSummaryItem) {
  const name = governedArmName(task);
  return name ? task.arms[name] : undefined;
}

// Every populated arm on a task, baseline first, then governed arms in
// precedence order (icm before icm_lite), then any extras alphabetically.
export function armNames(task: TaskSummaryItem): string[] {
  const order = ["baseline", "icm", "icm_lite"];
  const present = Object.keys(task.arms).filter((n) => task.arms[n]);
  return present.sort(
    (a, b) =>
      (order.indexOf(a) === -1 ? order.length : order.indexOf(a)) -
        (order.indexOf(b) === -1 ? order.length : order.indexOf(b)) ||
      a.localeCompare(b),
  );
}

// Deterministic paired bootstrap: resamples run pairs (baseline, governed)
// with a seeded LCG, returning a 95% CI on the percent cost change.
export function bootstrapPercentCI(
  pairs: [number, number][],
): [number, number] | null {
  const n = pairs.length;
  if (n < 2) return null;
  const baseMean = pairs.reduce((s, [b]) => s + b, 0) / n;
  if (!baseMean) return null;
  let seed = 9 >>> 0;
  const next = () =>
    (seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296;
  const samples: number[] = [];
  for (let i = 0; i < 2000; i++) {
    let b = 0,
      g = 0;
    for (let j = 0; j < n; j++) {
      const k = Math.floor(next() * n);
      b += pairs[k][0];
      g += pairs[k][1];
    }
    if (b > 0) samples.push(((g / n - b / n) / (b / n)) * 100);
  }
  samples.sort((a, b) => a - b);
  return [
    samples[Math.floor(0.025 * samples.length)],
    samples[Math.floor(0.975 * samples.length)],
  ];
}

// Per-suite bootstrap CI for one arm vs baseline: pairs runs by run_index
// on cost_usd (finite, comparison-eligible preferred).
export function suiteBootstrapCI(
  task: TaskSummaryItem,
  armName: string,
): [number, number] | null {
  const base = task.arms.baseline?.runs || [];
  const gov = task.arms[armName]?.runs || [];
  const eligible = (r: RunRecord) =>
    r.is_comparison_eligible !== false && finite(r.cost_usd);
  const baseByIdx = new Map(
    base.filter(eligible).map((r) => [r.run_index, r.cost_usd as number]),
  );
  const pairs: [number, number][] = [];
  for (const r of gov) {
    const b = baseByIdx.get(r.run_index);
    if (b !== undefined && eligible(r)) pairs.push([b, r.cost_usd as number]);
  }
  return bootstrapPercentCI(pairs);
}

export const experimentNames: Record<string, string> = {
  "BENCH-001": "Date range boundaries",
  "BENCH-002": "Cross-file API contract",
  "BENCH-003": "Event parser refactor",
  "BENCH-004": "Stateful filter table",
  "BENCH-005": "Config precedence scope",
  "BENCH-006": "Accounting mutation suite",
  "BENCH-007": "Cache & billing precision",
  "BENCH-008": "Worker lease & rollback",
  "EXP-001": "Text normalization",
  "EXP-002": "Rate limiting",
  "EXP-003": "Code analysis",
  "EXP-004": "Resilient transport",
  "EXP-005": "Marketing website",
  "EXP-006": "Transactional ledger",
  "EXP-007": "API gateway topology",
  "EXP-008": "Interview intelligence",
  "EXP-009": "Event-driven job queue",
  "EXP-010": "Knowledge graph & BM25",
  "EXP-011": "Policy API gateway",
};

export function finite(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

export function downloadJson(value: unknown, name: string) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function snapshotDate(value?: string) {
  if (!value || Number.isNaN(Date.parse(value))) return "Date unavailable";
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(value));
}
