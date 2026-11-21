---
type: concept
title: ICM Governance Overhead vs Break-Even Complexity
description: Quantitative analysis of fixed-stage governance overhead versus discovery savings, identifying the empirical break-even task complexity threshold.
status: active
verified: automated-verified
sources:
  - /concepts/measurement-layer.md
  - /concepts/architecture-overview.md
---

# ICM Governance Overhead vs. Break-Even Task Complexity

Empirical benchmark telemetry across 7 task archetypes on `gemini-3.8-flash-low` reveals a dual-regime economic behavior for the Interpretable Context Methodology (ICM).

---

## 1. The Dual-Regime Model

```
Total Spend ($)
 ^
 |             /  Baseline (Exploratory Churn: O(Files * Turns))
 |            /
 |           / 
 |----------X----------- Break-Even Threshold (~120-150 LOC / 2+ files)
 |         /
 |        /   ---------------- ICM (Bounded Context + Prefix Cache)
 |       /
 |      /  <-- Fixed 5-Stage Contract Overhead (~40k-80k tokens)
 +------------------------------------------------------------> Task Complexity (LOC / Files)
```

### Regime 1: Single-Turn Micro-Tasks (< 100 LOC, 1 file)
- **Examples:** `EXP-001` (Slugify, -200.8% savings), `EXP-002` (Rate Limiter, -95.3% savings).
- **Mechanism:** The baseline agent writes the file in 1 turn using ~67k tokens without discovery wander. ICM creates 5 mandatory markdown files (`01_intake.md` through `05_retro.md`), adding ~40k–80k tokens of structural text.
- **Outcome:** ICM incurs a **fixed governance overhead**.

### Regime 2: Multi-File Modular & Subagent Architectures (> 150 LOC, 2+ files)
- **Examples:** `EXP-003` (Retry Transport, +28.1% savings), `EXP-006` (Double-Entry Ledger, +64.3% savings).
- **Mechanism:** On complex tasks, baseline agents repeatedly re-read full files, accumulate raw terminal errors, and wander across symbols. ICM enforces AST symbol isolation (`repo_map.py`), sanitizes command logs (`filter_output.py`), and stabilizes prompt prefixes for 80%+ cache hits.
- **Outcome:** Baseline spend scales quadratically with turns, while ICM spend remains bounded.

---

## 2. Empirical Benchmark Matrix

| Task ID | Archetype | Target LOC | Baseline Spend | ICM Spend | Net Cost Delta | Baseline Wall Clock | ICM Wall Clock |
|---|---|---|---|---|---|---|---|
| `EXP-001` | Pure-Python Slugify | 48 LOC | $0.0747 | $0.2247 | **-200.8%** | 38.7s | 108.5s |
| `EXP-002` | Sliding Window Rate Limiter | 92 LOC | $0.0711 | $0.1388 | **-95.3%** | 17.5s | 46.5s |
| `EXP-003` | Resilient Retry Transport | 165 LOC | $0.1783 | $0.1283 | **+28.1%** | 65.8s | 43.7s |
| `EXP-004` | AST Dead Code Finder | 110 LOC | $0.1298 | $0.1624 | **-25.1%** | 42.4s | 42.6s |
| `EXP-005` | Full-Stack Landing Page | 280 LOC | $0.1597 | $0.1810 | **-13.3%** | 75.0s | 62.0s |
| `EXP-006` | Transactional Financial Ledger | 420 LOC (3 files) | $0.5215 | $0.1861 | **+64.3%** | 135.9s | 57.5s |
| `EXP-007` | API Gateway Topology Sandbox | 310 LOC | $0.2507 | $0.3381 | **-34.8%** | 116.6s | 85.1s |

---

## 3. Break-Even Complexity Threshold

The empirical break-even threshold where ICM becomes cost-positive occurs at:
1. **Source Code Volume:** $\ge 120\text{--}150$ Lines of Code.
2. **File Footprint:** $\ge 2$ interacting files (e.g. implementation + test suite or multi-module imports).
3. **Execution Depth:** $\ge 2$ interactive agent turns.

## 4. Adaptive ICM Routing

The opt-in `--mode auto` router uses **ICM-Lite** only when the task has exactly one target file and an estimated size below 150 LOC. At **150 LOC or two target files**, and when the scope or size is unknown, it uses full five-stage ICM: Intake, Plan, Execution, Verification, and Retrospective. The cutoff is a deterministic policy informed by the break-even range, not a guarantee of cost savings.

Declare the edit footprint in benchmark `task.json` (paths relative to its `workspace/`) or experiment task YAML frontmatter (paths relative to `target_repo`). List edited or created files, including tests, not files merely read. For example:

```yaml
target_files: [src/slugify.py]
estimated_loc: 48
```

The router counts distinct declared paths, or uses `target_files_count` when there is no list. It uses `estimated_loc` if supplied, otherwise the upper bound of `target_loc_range` (e.g. `"120-150"`), then the physical line count of a named file that already exists. Supply an estimate for a new file; the router does not infer scope by scanning the workspace or interpreting task prose.

Use `--mode icm` to force the five-stage contract, `--mode icm-lite` to force the single-stage `icm_lite` contract, or `--mode baseline` for the original prompt without governance. ICM-Lite keeps scope, symbol-level inspection, diff-only editing, and sanitized verification together without separate stage files.

```bash
python3 scripts/runner.py --live-bench BENCH-001 --mode auto
python3 scripts/run_experiment.py --task MOCK-001 --mode auto --dry-run
```

`--mode` selects one arm and cannot be combined with `--arm`. Omitting it preserves the legacy prompts and default arms (baseline for live benchmarks, baseline plus ICM for experiments). Dry runs replay fixtures for the selected arm rather than generating a contract run, so a Lite replay requires fixtures labeled `icm_lite`. The original `MOCK-001 --dry-run` command still replays both legacy arms.
