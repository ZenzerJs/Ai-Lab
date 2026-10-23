# Task Stage Contract: 03_exec

## Task Metadata
- **Task ID:** TSK-017
- **Experiment Ref:** EXP-001..EXP-007
- **Title:** Evidence Integrity & CRLF Disablement for Telemetry Artifacts
- **Status:** COMPLETE
- **Date Created:** 2026-10-04
- **Owner:** Systems Engineering & Infrastructure Agent
- **Task Contract Ref:** ICM Pipeline

---

## 1. Modifications Ledger
- Added `.gitattributes` to define `experiments/evidence/*.ndjson -text`.
- Re-materialized raw LF evidence files via `git checkout -- experiments/evidence`.
- Added unit tests in `tests/unit/test_evidence_attrs.py` verifying git attributes and pure LF line endings.
- Verified `scripts/ledger.py summary` recognizes all 14 live runs across 7 tasks.
