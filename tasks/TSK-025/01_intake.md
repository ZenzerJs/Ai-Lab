# Task Stage Contract: 01_intake

## Task Metadata
- **Task ID:** TSK-025
- **Title:** Multi-Dimensional Benchmark Scoring Rubric (Quality, Design, Engineering, Process)
- **Status:** APPROVED
- **Owner:** Systems Engineering & Research Agent
- **Task Contract Ref:** ICM Pipeline

---

## 1. Problem Statement & Scope
- **Problem:** Current AI-Lab benchmarks evaluate ICM governance vs. baseline primarily on token spend (`cost_usd`) and binary test pass/fail (`verification_status`). Cost alone misses whether governed execution produces superior architecture, cleaner diffs, better accessibility/UI design, and stronger engineering hygiene.
- **Scope In:**
  - Pre-registered 5-dimension evaluation rubric (0–5 scale per dimension, total 0–25) covering Correctness, Engineering Practices, Maintainability, Process Discipline, and Design/UX.
  - Automated objective extractors (test pass rate, diff size/churn, linter/typecheck errors, cyclomatic complexity, Lighthouse/axe a11y checks) paired with blind A/B judge protocol for subjective design/architecture review.
  - Storage convention utilizing existing `CampaignSlot.notes` / `runs.notes` JSON payload (`quality_scores`) to avoid schema bloat before live execution.
  - Confidence interval (95% CI) reporting requirement across quality dimensions alongside cost.
- **Scope Out:**
  - Paid live LLM benchmark campaign execution (deferred until user triggers next benchmark run).
  - Modifying historical verified snapshot data (`dashboard/public/data.json` build `6e55094`).
  - Adding third-party heavy grading dependencies (stick to stdlib + existing pytest/ruff/Playwright toolchain).

---

## 2. Constraints & Context Budgets
- **Skills Active:** `caveman` (full), `ponytail` (full).
- **Stage Token Budgets:**
  - `01_intake`: 2,000 tokens
  - `02_plan`: 3,000 tokens
  - `03_exec`: 6,000 tokens (deferred until execution requested)
  - `04_verify`: 3,000 tokens
  - `05_retro`: 1,500 tokens
