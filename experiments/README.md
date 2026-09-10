# Antigravity A/B Experimentation & Measurement Guide

This directory houses task definitions, benchmark fixtures, and configuration for running empirical A/B experiments comparing baseline agent execution against the workspace's Interpretable Context Methodology (ICM) pipeline.

---

## 1. How to Author a Task Definition (`experiments/tasks/<TASK-ID>.md`)

Every experiment requires a declarative task specification formatted in Markdown with YAML frontmatter:

```markdown
---
task_id: MYTASK-001
model: gemini-2.5-pro
target_repo: .
runs_per_arm: 3
---

# Task Prompt

[Insert the exact, verbatim user prompt to be executed by both arms]
```

### Required Fields
- **`task_id`**: Unique alphanumeric identifier matching the filename stem (e.g. `OPT-001`).
- **`model`**: Upstream model identifier (e.g. `gemini-2.5-pro`, `claude-3-7-sonnet`, `gpt-4o`).
- **`target_repo`**: Path to target repository or worktree (relative to the task file or absolute).
- **`runs_per_arm`**: Number of runs per arm (integer $\ge 2$, default: 3).

### Fairness Invariants
The runner automatically asserts:
1. Both arms use the identical `model`.
2. Exact prompt byte parity between baseline and ICM arms.
3. Clean starting worktree state (`git checkout -- .` and `git clean -fd`) between runs.
4. $n \ge 2$ runs per arm.

---

## 2. Running A/B Trials

### Dry-Run Verification (Synthetic Fixtures — No Model Costs)
To verify harness mechanics, populate SQLite ledger tables, and validate dashboard data without consuming API quotas:
```bash
python scripts/run_experiment.py --task MOCK-001 --dry-run
```

### Live Experimental Run (Paid Model Execution)
To execute a real A/B trial using the headless Antigravity CLI:
```bash
python scripts/run_experiment.py --task MYTASK-001
```

*Note: In live mode, the runner executes the Baseline Arm ($n$ runs) with raw prompts, followed by the ICM Pipeline Arm ($n$ runs) with structured stage contracts, recording exact usage tokens to `data/usage.db`.*

---

## 3. Updating Pricing Rates (`config/PRICING.json`)

Pricing rates are never hardcoded in Python. Token rates are maintained in `config/PRICING.json` in USD per million tokens (MTok):

```json
{
  "models": {
    "gemini-2.5-pro": {
      "input_usd_per_mtok": 1.25,
      "cache_read_usd_per_mtok": 0.125,
      "output_usd_per_mtok": 10.00,
      "source_url": "https://ai.google.dev/pricing",
      "fetched_at": "2026-09-09T00:00:00Z"
    }
  }
}
```

To sync updated pricing into SQLite:
```bash
python scripts/ledger.py seed-pricing
```

---

## 4. Launching the Local Savings Dashboard

1. Export latest usage ledger data:
   ```bash
   python dashboard/build_data.py
   ```
2. Start the local Vite development server:
   ```bash
   cd dashboard && npm run dev
   ```
3. Open `http://localhost:5173` in your browser to inspect charts, cache ratios, and ledger entries.
