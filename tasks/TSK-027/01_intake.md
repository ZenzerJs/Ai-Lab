# Task Stage Contract: 01_intake

## Task Metadata
- **Task ID:** TSK-027
- **Title:** Full Benchmark Quality Audit (`EXP-001`..`EXP-008`) & Live Multi-File Evaluation (`EXP-009`..`EXP-011`)
- **Status:** APPROVED
- **Owner:** Systems Engineering & Research Agent
- **Task Contract Ref:** ICM Pipeline

---

## 1. Problem Statement & Scope
- **Problem:** User approved running the new 5-dimension quality judge (`score_workspace`, `prepare_blind_ab_packet`, `compute_quality_ci`) across all existing experiment artifacts (`EXP-001`..`EXP-008`) without rebuilding them, plus executing head-to-head Baseline vs. ICM evaluations on the three new multi-file benchmarks (`EXP-009`..`EXP-011`).
- **Scope In:**
  - Retroactive quality audit of existing `EXP-001`..`EXP-008` artifacts (`experiments/evidence/*.ndjson`, `src/*.py`, `sandbox/*`) without rebuilding.
  - Head-to-head Baseline vs. ICM execution and 5-dimension quality grading on `EXP-009`, `EXP-010`, and `EXP-011` in isolated disposable workspaces.
  - Blind A/B judge evaluation + 95% bootstrap confidence intervals across all 11 experiments (`EXP-001`..`EXP-011`).
- **Scope Out:**
  - Mutating historical verified cost rows in `data/usage.db` (`EXP-001`..`EXP-007` cost snapshot remains untouched).

---

## 2. Stage Token Budgets
- `01_intake`: 1,500 tokens | `02_plan`: 2,000 tokens | `03_exec`: 10,000 tokens | `04_verify`: 3,000 tokens | `05_retro`: 1,500 tokens
