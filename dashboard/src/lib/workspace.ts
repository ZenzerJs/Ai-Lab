import { TaskSummaryItem } from "../types";

export type Destination =
  "overview" | "tasks" | "simulator" | "sandboxes" | "audit";
export const destinations: Destination[] = [
  "overview",
  "tasks",
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

export function governedArm(task: TaskSummaryItem) {
  const name =
    task.governed_arm ||
    ["icm-subagents", "icm", "delegation"].find((key) => task.arms[key]);
  return name
    ? task.arms[name]
    : Object.entries(task.arms).find(([key]) => key !== "baseline")?.[1];
}

export const experimentNames: Record<string, string> = {
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
