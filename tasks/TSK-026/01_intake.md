# Task Stage Contract: 01_intake

## Task Metadata
- **Task ID:** TSK-026
- **Title:** Large-Scale Multi-File Benchmark Suite (`EXP-009`..`EXP-011`) & Blind Judge Protocol
- **Status:** APPROVED
- **Owner:** Systems Engineering & Research Agent
- **Task Contract Ref:** ICM Pipeline

---

## 1. Problem Statement & Scope
- **Problem:** Existing benchmarks (`EXP-001`..`EXP-007`) are mostly small tasks (48–420 LOC, 1–3 files), sitting below or right at the ~150 LOC / 2+ file ICM break-even threshold. We need larger, realistic multi-file repository outlines (~1,000–1,800 LOC target across 6–8 files) plus an automated blind pairwise A/B packet generator and quality CI calculator to test both cost and the 5-dimension quality rubric (`TSK-025`).
- **Scope In:**
  - Define 3 large-scale benchmark task specifications (`experiments/tasks/EXP-009.md`, `EXP-010.md`, `EXP-011.md`) combining pre-seeded multi-file repo outlines (6–8 files) with 1,000–1,800 LOC implementation targets and explicit 5-dimension rubric checks.
  - Create deterministic starter repo outline generator (`scripts/scaffold_outlines.py`) that materializes the broken/partial 6–8 file starter repos for `EXP-009`, `EXP-010`, and `EXP-011` into any disposable workspace.
  - Extend `scripts/campaign.py` with:
    - `prepare_blind_ab_packet(campaign_id, task_id, baseline_diff, governed_diff, seed)`: strips `tasks/TSK-XXX/` and arm names, randomizes `Arm_Alpha` vs `Arm_Beta` assignment deterministically from seed, and emits a blind evaluation bundle + sealed key.
    - `compute_quality_ci(paired_scores, seed)`: computes paired quality delta ($\Delta = \text{Governed} - \text{Baseline}$) and 95% bootstrap confidence intervals across each rubric dimension.
  - Register `EXP-009`, `EXP-010`, and `EXP-011` display names in `dashboard/src/lib/workspace.ts`.
- **Scope Out:**
  - Paid live LLM API execution (deferred until user authorizes live campaign).
  - Modifying historical verified snapshot data (`dashboard/public/data.json`).

---

## 2. Constraints & Context Budgets
- **Skills Active:** `caveman` (full), `ponytail` (full).
- **Stage Token Budgets:**
  - `01_intake`: 2,000 tokens
  - `02_plan`: 3,000 tokens
  - `03_exec`: 8,000 tokens (delegated to `flash` subagent)
  - `04_verify`: 3,000 tokens
  - `05_retro`: 1,500 tokens
