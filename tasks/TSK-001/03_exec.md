# Task Stage Contract: 03_exec

## Task Metadata
- **Task ID:** TSK-001
- **Title:** Measurement Layer — Usage Harness & Savings Dashboard
- **Status:** COMPLETE
- **Prerequisite:** `02_plan.md` OKR Gate signed off

---

## 1. Execution Summary
1. Expanded `.agents/mcp_config.json` mounts for filesystem server (`./data`, `./experiments`, `./dashboard`, `./config`).
2. Authored `config/PRICING.json` with externalized token pricing per MTok for Gemini, Claude, and GPT models.
3. Implemented `scripts/ledger.py` with SQLite storage engine, schema initialization, auto-seeding, and cache-aware cost formulas.
4. Implemented `scripts/run_experiment.py` orchestrating headless A/B evaluation, enforcing 4 fairness invariants, and supporting `--dry-run`.
5. Created `experiments/fixtures/mock_stream.ndjson` simulating 2 arms × 3 runs of task `MOCK-001`.
6. Authored `dashboard/build_data.py` generating `dashboard/public/data.json`.
7. Scaffolded `dashboard/` using Vite + React + TypeScript + Tailwind CSS + Recharts implementing 5 responsive views with sample size labels ($n=X$) and zero projections.
8. Authored `docs/concepts/measurement-layer.md`, updated `docs/index.md`, appended to `docs/log.md`, and documented `experiments/README.md`.
9. Registered skills `.agents/skills/run_experiment.md`, `.agents/skills/usage_dashboard.md`, `.agents/skills/ai-lab.md`, and global `C:\Users\jayde\.gemini\config\skills\ai-lab\SKILL.md`.

---

## 2. Search/Replace Change Tracking Ledger

### Target File: `.agents/mcp_config.json`
```text
<<<<<<< SEARCH
        "./tasks",
        "./src",
        "./docs",
        "./scripts"
      ],
      "description": "Sandboxed multi-root file access restricted to ./tasks, ./src, ./docs, and ./scripts"
=======
        "./tasks",
        "./src",
        "./docs",
        "./scripts",
        "./data",
        "./experiments",
        "./dashboard",
        "./config"
      ],
      "description": "Sandboxed multi-root file access restricted to ./tasks, ./src, ./docs, ./scripts, ./data, ./experiments, ./dashboard, and ./config"
>>>>>>> REPLACE
```

### Target File: `docs/index.md`
```text
<<<<<<< SEARCH
* [Architecture Overview](/concepts/architecture-overview.md) - System topology, module boundaries, MCP layer, and execution rules.
* [Coding Standards](/concepts/coding-standards.md) - Code conventions, typing invariants, error boundaries, and diff protocols.
=======
* [Architecture Overview](/concepts/architecture-overview.md) - System topology, module boundaries, MCP layer, and execution rules.
* [Coding Standards](/concepts/coding-standards.md) - Code conventions, typing invariants, error boundaries, and diff protocols.
* [Measurement Layer](/concepts/measurement-layer.md) - A/B experiment harness, fairness invariants, and cache-aware pricing economics.
>>>>>>> REPLACE
```

---

## 3. Symbol Modification Ledger

| Symbol Name | Symbol Type | File Path | Modification Summary |
|---|---|---|---|
| `get_connection` | Function | `scripts/ledger.py` | SQLite connection factory with auto-init |
| `init_db` | Function | `scripts/ledger.py` | Idempotent schema initialization for runs, tasks, pricing |
| `seed_pricing` | Function | `scripts/ledger.py` | Seed pricing rates from `config/PRICING.json` |
| `calculate_cost` | Function | `scripts/ledger.py` | Cache-aware USD cost formula per million tokens |
| `record_run` | Function | `scripts/ledger.py` | Record single experimental run with telemetry |
| `task_summary` | Function | `scripts/ledger.py` | Per-arm means, error bands, and savings calculation |
| `cumulative_savings` | Function | `scripts/ledger.py` | Running total of savings across all tasks |
| `parse_task_file` | Function | `scripts/run_experiment.py` | Parse task markdown frontmatter and prompt |
| `verify_fairness_invariants` | Function | `scripts/run_experiment.py` | Assert model ID, prompt bytes, and run count invariants |
| `reset_workspace_state` | Function | `scripts/run_experiment.py` | Clean worktree reset between runs |
| `execute_dry_run` | Function | `scripts/run_experiment.py` | Replay NDJSON fixtures and populate ledger |
| `build_data_payload` | Function | `dashboard/build_data.py` | Query SQLite and construct JSON payload for frontend |

---

## 4. Escape-Hatch Justification Log

| Target File Path | File Size (lines) | Overwrite Rationale | Architect Approval |
|---|---|---|---|
| `config/PRICING.json` | 27 | Net-new file creation | APPROVED |
| `scripts/ledger.py` | 338 | Net-new file creation | APPROVED |
| `scripts/run_experiment.py` | 336 | Net-new file creation | APPROVED |
| `experiments/fixtures/mock_stream.ndjson` | 18 | Net-new file creation | APPROVED |
| `experiments/tasks/MOCK-001.md` | 12 | Net-new file creation | APPROVED |
| `dashboard/build_data.py` | 115 | Net-new file creation | APPROVED |
| `dashboard/src/*` | Various | Net-new frontend source files | APPROVED |
| `docs/concepts/measurement-layer.md` | 78 | Net-new file creation | APPROVED |
| `experiments/README.md` | 72 | Net-new file creation | APPROVED |
| `.agents/skills/*.md` | Various | Net-new skill documentation files | APPROVED |
