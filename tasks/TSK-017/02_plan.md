# Task Stage Contract: 02_plan

## Task Metadata
- **Task ID:** TSK-017
- **Experiment Ref:** EXP-001..EXP-007
- **Title:** Evidence Integrity & CRLF Disablement for Telemetry Artifacts
- **Status:** APPROVED
- **Date Created:** 2026-10-04
- **Owner:** Systems Engineering & Infrastructure Agent
- **Task Contract Ref:** ICM Pipeline

---

## 1. Technical Architecture & Impact Manifest
- File modifications:
  - `[NEW] .gitattributes`: `experiments/evidence/*.ndjson -text`
  - `[NEW] tests/unit/test_evidence_attrs.py`: unit test verifying `.ndjson` attributes and hash consistency
  - `[MODIFY] dashboard/public/data.json`: regenerated via `python dashboard/build_data.py`

---

## 2. OKR Acceptance Matrix

| Objective | Key Result | Machine-Verifiable Exit Command | Expected Value | Status |
|---|---|---|---|---|
| **O1: Evidence Integrity** | KR1.1: 7 of 7 tasks measured | `python scripts/ledger.py summary` | `Tasks Evaluated (Measured): 7 of 7` | PENDING |
| **O2: Regression Safety** | KR2.1: Pytest test suite passing | `python scripts/filter_output.py python -m pytest -q` | `exit=0` | PENDING |
| **O3: Dashboard Data Sync** | KR3.1: Public data reflects measured runs | `python dashboard/build_data.py` | `exit=0` | PENDING |

---

## 3. Exit Criteria
- [ ] `.gitattributes` added with binary rule for evidence ndjson files.
- [ ] Evidence files checked out with bit-exact LF endings.
- [ ] `ledger.py summary` shows 7 of 7 measured tasks.
- [ ] Unit tests pass.
