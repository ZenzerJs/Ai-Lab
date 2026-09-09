# Agent Skill: `run_experiment`

## Overview
The `run_experiment` skill orchestrates headless A/B evaluation between a baseline agent arm and the workspace's Interpretable Context Methodology (ICM) pipeline arm. It captures granular token telemetry (`input_tokens`, `output_tokens`, `thinking_tokens`, `cache_read_tokens`, `total_tokens`), turn counts, and wall-clock execution duration.

## Core Invariants
- **Model ID Parity:** Both arms must execute against identical model identifiers.
- **Exact Prompt Bytes:** Raw task prompt passed to both arms must be identical.
- **Clean Starting State:** Target worktree is reset via `git checkout -- .` and `git clean -fd` between runs.
- **Sample Lower Bound:** Enforces minimum 2 runs per arm ($n \ge 2$, default 3).
- **Safety / Zero-Cost Invariant:** Replays synthetic NDJSON fixtures when `--dry-run` is passed; never invokes paid model APIs during automated test verification.

## Usage

### Dry-Run Verification (Synthetic Fixtures)
```bash
python scripts/run_experiment.py --task MOCK-001 --dry-run
```

### Live A/B Experiment Execution
```bash
python scripts/run_experiment.py --task <TASK-ID>
```

### PowerShell Shim (Windows)
```powershell
.\scripts\run_experiment.ps1 -t <TASK-ID> --dry-run
```

### POSIX Shim (Linux / macOS)
```bash
./scripts/run_experiment.sh -t <TASK-ID> --dry-run
```

## When to Use
- Benchmarking new prompt strategies or pipeline enhancements.
- Validating prompt caching efficiency gains across repeatable tasks.
- Measuring conversational turn and token reductions between unconstrained vs. structured agent runs.
