# Task Stage Contract: 01_intake

## Task Metadata
- **Task ID:** TSK-021
- **Title:** Research Report: ICM Governance Overhead vs. Break-Even Task Complexity
- **Status:** APPROVED
- **Date Created:** 2026-10-04
- **Owner:** Systems Engineering & Research Agent
- **Task Contract Ref:** ICM Pipeline

---

## 1. Problem Statement & Research Scope
- **Research Question:** Why does ICM governance cost more on small algorithmic tasks (`EXP-001`, `EXP-002`, `EXP-004`) while yielding massive cost reductions (28% to 64%) on larger multi-file architectures (`EXP-003`, `EXP-006`)? What is the empirical break-even task complexity threshold?
- **Scope In:**
  - Empirical analysis across all 7 benchmark tasks recorded in `data/usage.db`.
  - Analytical modeling of fixed-contract token tax vs. exploratory token churn.
  - Identification of break-even threshold (LOC, file count, turn count).
  - Documentation of recommendations for adaptive ICM (lightweight vs full governance).
- **Scope Out:** Modifying production code or merging untested governance changes.
