# Task Stage Contract: 01_intake

## Task Metadata
- **Task ID:** TSK-018
- **Title:** Honest Benchmark Reporting & Sandbox Cleanup
- **Status:** APPROVED
- **Date Created:** 2026-10-04
- **Owner:** Systems Engineering & Documentation Agent
- **Task Contract Ref:** ICM Pipeline

---

## 1. Problem Statement & Scope Boundaries
- **Problem:** `README.md`, `OVERNIGHT_HANDOFF_VERIFICATION.md`, and dashboard references contained unverified headline claims of 61.58% net savings. Pre-baked HTML generators produced synthetic showcases.
- **Scope In:**
  - Update `README.md` to reflect honest empirical savings from measured data in `data/usage.db` (1.92% net cost reduction across measured runs on Gemini 3.8 Flash, with transparent task-level trade-offs: +65% duration and overhead on small tasks, up to 64% savings on large modular tasks).
  - Update `OVERNIGHT_HANDOFF_VERIFICATION.md` with an audit correction notice.
  - Delete `scripts/html_generator.py` and remove dead `--output` references per ponytail minimalism.
  - Re-generate `dashboard/public/data.json` and verify Vite build.
- **Scope Out:** Fabricating synthetic numbers.
