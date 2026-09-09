# Task Stage Contract: 01_intake

## Task Metadata
- **Task ID:** TSK-001
- **Title:** Measurement Layer — Usage Harness & Savings Dashboard
- **Status:** APPROVED
- **Date Created:** 2026-09-09
- **Owner:** Lead Software Architect
- **Task Contract Ref:** ICM Pipeline

---

## 1. Problem Statement & Objectives
Establish an empirical measurement layer within the Antigravity AI-Lab workspace:
1. Construct an A/B experiment harness (`scripts/run_experiment.py`) executing identical tasks across an unconstrained baseline arm and the workspace's structured ICM pipeline arm.
2. Build an auditable SQLite usage ledger (`scripts/ledger.py` + `data/usage.db`) enforcing cache-aware pricing formulas seeded from `config/PRICING.json`.
3. Develop a local Vite + React + TypeScript web dashboard (`dashboard/`) with Tailwind CSS and Recharts visualizing cost differences, error bands, cache hit ratios, duration, and conversational turns.
4. Provide zero-cost dry-run verification via synthetic NDJSON fixtures (`experiments/fixtures/mock_stream.ndjson`).

---

## 2. Scope Boundaries
The following components are within the implementation boundary:
- `.agents/mcp_config.json`: Multi-root filesystem expansion to include `./data`, `./experiments`, `./dashboard`, `./config`.
- `config/PRICING.json`: Auditable model token rates with upstream source URLs.
- `scripts/run_experiment.py` + `.ps1` + `.sh`: A/B runner with headless stream-json parsing, dry-run playback, and fairness assertions.
- `scripts/ledger.py` + `.ps1` + `.sh`: SQLite engine managing `runs`, `tasks`, and `pricing` tables with cache-aware cost formulas.
- `dashboard/`: Full Vite + React + TS dashboard with five responsive views and static export via `dashboard/build_data.py`.
- `experiments/fixtures/mock_stream.ndjson`: 2 arms × 3 runs simulation of task `MOCK-001`.
- `docs/concepts/measurement-layer.md` and `docs/log.md`: OKF v0.2 concept and chronological updates.
- `.agents/skills/`: Skills for `run_experiment`, `usage_dashboard`, and `ai-lab`.

---

## 3. Out-of-Scope Declarations
- No paid model calls during this setup/verification task (all verification must use mock data).
- No production cloud hosting or remote databases (local SQLite and Vite only).
- No speculative cost forecasting or synthetic projections on charts.

---

## 4. Technical Constraints & Invariants
- **Zero Paid Model Calls:** All testing strictly uses `--dry-run` and synthetic NDJSON fixtures.
- **Fairness Invariants:** Identical model ID, identical prompt bytes, clean workspace reset between runs, $n \ge 2$.
- **Cache-Aware Formula:** Cost calculated as `((input * rate) + (cache_read * rate) + (output * rate)) / 1_000_000`.
- **Rate Auditing:** Token rates seeded exclusively from `config/PRICING.json`; never hardcoded in Python.
- **Log Sanitation:** All test and build executions wrapped via `scripts/filter_output.py`.
- **OKF v0.2 Compliance:** Strict adherence to schema keys and bundle-relative link integrity.

---

## 5. Per-Stage Token Budget Allocation Table

| Slice Component | Allocated Token Budget | Target Description / Pruning Control |
|---|---|---|
| **System Persona & Rules** | 1,500 tokens | Fixed directives from `AGENTS.md` and `.agents/rules/` |
| **Tool Definitions (MCP/CLI)** | 1,200 tokens | Compact JSON-RPC tool definitions |
| **OKF Knowledge Base Slice** | 1,500 tokens | Targeted excerpts from `docs/concepts/` |
| **Active Task Contract** | 2,500 tokens | Current stage contract markdown |
| **Working Memory Margin** | 1,300 tokens | Ephemeral search queries and diff chunks |
| **Total Turn Context Limit** | **8,000 tokens** | Hard bound enforced by prompt assembly |
