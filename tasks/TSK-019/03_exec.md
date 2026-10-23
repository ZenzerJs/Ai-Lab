# Task Stage Contract: 03_exec

## Task Metadata
- **Task ID:** TSK-019
- **Title:** Experiment Runner Hardening — Run Preservation & Real Verification
- **Status:** COMPLETE
- **Date Created:** 2026-10-04
- **Owner:** Systems Engineering & Infrastructure Agent
- **Task Contract Ref:** ICM Pipeline

---

## 1. Modifications Ledger
- Updated `scripts/run_experiment.py`:
  - Added `execute_verification` to run `verify_cmd` dynamically and assign `passed`, `failed`, or `not_run`.
  - Added `get_next_run_index` to append runs sequentially instead of erasing previous runs.
  - Added `--clear` flag to allow explicit clearing only when requested.
  - Hashed the exact effective prompt per arm (`prompt_hash`) and saved in run notes.
  - Removed all hardcoded `verification_status="passed"`.
- Added unit tests in `tests/unit/test_runner_hardening.py` covering verification outcomes and sequential run indexing.
