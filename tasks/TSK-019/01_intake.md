# Task Stage Contract: 01_intake

## Task Metadata
- **Task ID:** TSK-019
- **Title:** Experiment Runner Hardening — Run Preservation & Real Verification
- **Status:** APPROVED
- **Date Created:** 2026-10-04
- **Owner:** Systems Engineering & Infrastructure Agent
- **Task Contract Ref:** ICM Pipeline

---

## 1. Problem Statement & Scope Boundaries
- **Problem:**
  1. `run_experiment.py` called `clear_task_runs()` unconditionally, wiping prior live runs whenever a task was re-run.
  2. `run_experiment.py` hardcoded `verification_status="passed"` instead of executing the task's automated verification command.
  3. The exact prompt bytes dispatched to the CLI were not hashed or recorded per arm.
- **Scope In:**
  - Update `run_experiment.py` to preserve existing live runs by computing `run_index = max(existing_runs) + 1` unless an explicit `--clear` flag is provided.
  - Implement real automated verification execution: execute task `verify_cmd` (e.g. `pytest ...`), record actual status (`passed` vs `failed`), and set `verification_status="not_run"` when no command is provided.
  - Record the exact prompt SHA-256 in the ledger metadata.
  - Add unit tests in `tests/unit/test_runner_hardening.py`.
- **Scope Out:** Fabricating benchmark fixtures.
