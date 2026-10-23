# Task Stage Contract: 02_plan

## Task Metadata
- **Task ID:** TSK-019
- **Title:** Experiment Runner Hardening — Run Preservation & Real Verification
- **Status:** APPROVED
- **Date Created:** 2026-10-04
- **Owner:** Systems Engineering & Infrastructure Agent
- **Task Contract Ref:** ICM Pipeline

---

## 1. Technical Architecture & Impact Manifest
- File modifications:
  - `[MODIFY] scripts/run_experiment.py`:
    - Add `--clear` argument (default `False`).
    - Query highest existing `run_index` for the task and arm in `usage.db`, appending rather than overwriting.
    - Run `verify_cmd` using `subprocess.run` in target repo; evaluate exit code 0 as `passed`, non-zero as `failed`, missing command as `not_run`.
    - Compute SHA-256 of exact prompt string dispatched to CLI and store in run manifest/notes.
    - Remove all hardcoded `verification_status="passed"`.
  - `[NEW] tests/unit/test_runner_hardening.py`: Unit tests verifying that failing verification yields `verification_status="failed"` and runs append safely.

---

## 2. OKR Acceptance Matrix

| Objective | Key Result | Machine-Verifiable Exit Command | Expected Value | Status |
|---|---|---|---|---|
| **O1: No Hardcoded Status** | KR1.1: Zero hardcoded `verification_status="passed"` in runner | `Select-String -Path scripts/run_experiment.py -Pattern 'verification_status="passed"'` | Empty | PENDING |
| **O2: Hardening Test Suite** | KR2.1: Runner hardening tests pass | `python scripts/filter_output.py python -m pytest tests/unit/test_runner_hardening.py` | `exit=0` | PENDING |

---

## 3. Exit Criteria
- [ ] Runner appends runs and preserves history unless `--clear` specified.
- [ ] `verify_cmd` executes dynamically with honest status assignment.
- [ ] Pytest test suite green.
