# Task Stage Contract: 02_plan

## Task Metadata
- **Task ID:** TSK-001
- **Title:** Measurement Layer — Usage Harness & Savings Dashboard
- **Status:** APPROVED
- **Prerequisite:** `01_intake.md` exit criteria satisfied

---

## 1. Technical Approach & Architecture

### Cognitive Reasoning Trace (Sequential Thinking)
1. **Stage 0 (MCP Expansion):** Update `.agents/mcp_config.json` adding `./data`, `./experiments`, `./dashboard`, `./config` mounts.
2. **Stage 1 (Runner):** Build `scripts/run_experiment.py` parsing `experiments/tasks/*.md`, executing headless CLI with `--output-format stream-json`, parsing NDJSON events, and enforcing fairness invariants.
3. **Stage 2 (Ledger):** Build `scripts/ledger.py` with SQLite schema (`runs`, `tasks`, `pricing`), auto-seeding rates from `config/PRICING.json`, computing cache-aware costs.
4. **Stage 3 (Dashboard):** Scaffold Vite + React + TS dashboard with Tailwind CSS and Recharts. Build exporter `dashboard/build_data.py` outputting to `dashboard/public/data.json`. Implement 5 responsive views with sample size labels ($n=X$) and no projections.
5. **Stage 4 (Mock Fixtures & Smoke Tests):** Construct `experiments/fixtures/mock_stream.ndjson` simulating 2 arms × 3 runs of task `MOCK-001`. Run and record all 5 smoke verification tests.
6. **Stage 5 (OKF Docs & Skills):** Create `docs/concepts/measurement-layer.md`, update `docs/index.md` and `docs/log.md`, write `experiments/README.md`, and register skills.

---

## 2. Impacted Files Manifest

| Target File Path | Action | Description & Rationale |
|---|---|---|
| `.agents/mcp_config.json` | `MODIFY` | Expanded filesystem mount paths |
| `config/PRICING.json` | `CREATE` | Auditable token pricing rates with source URLs |
| `scripts/ledger.py` | `CREATE` | SQLite usage persistence engine |
| `scripts/run_experiment.py` | `CREATE` | A/B experiment runner with fairness assertions |
| `experiments/fixtures/mock_stream.ndjson` | `CREATE` | Synthetic NDJSON stream for 6 runs |
| `experiments/tasks/MOCK-001.md` | `CREATE` | Benchmark task definition file |
| `dashboard/build_data.py` | `CREATE` | Data exporter from SQLite to JSON |
| `dashboard/` | `CREATE` | Vite + React + TS dashboard application |
| `docs/concepts/measurement-layer.md` | `CREATE` | OKF v0.2 concept specification |
| `docs/index.md` | `MODIFY` | Root catalog index update |
| `docs/log.md` | `MODIFY` | Chronological update log entry |
| `experiments/README.md` | `CREATE` | Developer documentation for experiments |
| `.agents/skills/*.md` | `CREATE` | Skill specifications for runner, dashboard, ai-lab |

---

## 3. OKR Acceptance Matrix (Machine-Verifiable Exit Criteria)

**Objective:** Build and smoke-verify a zero-cost empirical measurement layer and savings dashboard.

| Key Result (KR) | Deterministic Success Metric | Automated Verification Command | Status |
|---|---|---|---|
| **KR 1** | A/B Runner records 6 mock runs to SQLite ledger in dry-run mode | `python scripts/filter_output.py python scripts/run_experiment.py --task MOCK-001 --dry-run` | PASSED |
| **KR 2** | Ledger summarizes per-arm metrics, turns, and savings | `python scripts/ledger.py summary MOCK-001` | PASSED |
| **KR 3** | Data exporter generates static JSON for dashboard | `python scripts/filter_output.py python dashboard/build_data.py` | PASSED |
| **KR 4** | Dashboard compiles cleanly without TypeScript or Vite errors | `python scripts/filter_output.py npm run build --prefix dashboard` | PASSED |
| **KR 5** | OKF documentation adheres to schema rules and link integrity | `python scripts/filter_output.py python scripts/lint_frontmatter.py` | PASSED |

---

## 4. Stage Gate Transition Check
All exit criteria defined and machine-verifiable. Proceed to `03_exec.md`.
