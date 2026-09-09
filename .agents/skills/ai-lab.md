---
name: Ai-Lab
description: Launch, inspect, and benchmark ICM vs. Baseline agent experiments and open the savings dashboard.
trigger: /Ai-Lab
---
# AI-Lab Benchmarking & Dashboard Control

When the user invokes `/Ai-Lab`, determine the intended sub-action from their prompt arguments (defaulting to `--status` if no flags are provided):

### Subcommand Handlers:
1. **`/Ai-Lab --status`** (Default):
   - Run `python scripts/ledger.py summary` across all recorded tasks.
   - Report baseline vs. ICM cumulative USD savings and cache hit ratios.
2. **`/Ai-Lab --run <TASK-ID>`**:
   - Verify `experiments/tasks/<TASK-ID>.md` exists.
   - Run `python scripts/run_experiment.py --task <TASK-ID>`.
   - Update the ledger and refresh `dashboard/public/data.json` via `python dashboard/build_data.py`.
3. **`/Ai-Lab --dashboard`**:
   - Run `python dashboard/build_data.py`.
   - Launch the local Vite dev server: `cd dashboard && npm run dev`.
   - Surface the local URL (`http://localhost:5173`) in an Antigravity browser preview or artifact.
4. **`/Ai-Lab --dry-run`**:
   - Execute `python scripts/run_experiment.py --task MOCK-001 --dry-run` to populate synthetic fixtures without spending model quota.
