# Task Stage Contract: 01_intake

## Task Metadata
- **Task ID:** TSK-020
- **Title:** Task Backlog Retrospectives & Documentation Consistency Cleanup
- **Status:** APPROVED
- **Date Created:** 2026-10-04
- **Owner:** Systems Engineering & Infrastructure Agent
- **Task Contract Ref:** ICM Pipeline

---

## 1. Problem Statement & Scope Boundaries
- **Problem:** Several completed tasks (`TSK-010`, `TSK-011`, `TSK-013`, `TSK-014`, `TSK-016`) lacked formal `05_retro.md` stage contracts. `TSK-009/02_plan.md` still reported status `IN_REVIEW`. The `repo_map` skill lacked explicit examples showing that positional file arguments fail and `--target` is required.
- **Scope In:**
  - Create standard `05_retro.md` files for `TSK-010`, `TSK-011`, `TSK-013`, `TSK-014`, `TSK-016`.
  - Update `TSK-009/02_plan.md` status to `COMPLETE`.
  - Add `--target` examples to `.agents/skills/repo_map.md`.
  - Run `scripts/lint_frontmatter.py` to ensure 100% OKF compliance.
- **Scope Out:** Modifying source business logic or experiment benchmarks.
