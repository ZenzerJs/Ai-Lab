# Task Stage Contract: 01_intake

## Task Metadata
- **Task ID:** TSK-017
- **Experiment Ref:** EXP-001..EXP-007
- **Title:** Evidence Integrity & CRLF Disablement for Telemetry Artifacts
- **Status:** APPROVED
- **Date Created:** 2026-10-04
- **Owner:** Systems Engineering & Infrastructure Agent
- **Task Contract Ref:** ICM Pipeline

---

## 1. Problem Statement & Scope Boundaries
- **Problem:** Git `autocrlf` converts LF to CRLF in `experiments/evidence/*.ndjson`, causing hash mismatches in `validate_evidence_file` and demoting all live benchmark runs to `historical` (0 measured tasks).
- **Scope In:**
  - Create `.gitattributes` setting `experiments/evidence/*.ndjson -text`.
  - Re-materialize raw LF bytes from git index.
  - Add regression test `tests/unit/test_evidence_attrs.py`.
  - Re-generate `dashboard/public/data.json`.
- **Scope Out:**
  - Modifying `validate_evidence_file` to tolerate CRLF (we maintain strict byte-exact integrity).
  - Modifying model prompt contents or rate cards.

---

## 2. Stage Token Budget & Resource Allocation
- **Intake Context Margin:** <= 4,000 tokens
- **Target Execution Limit:** <= 8,000 tokens per turn
