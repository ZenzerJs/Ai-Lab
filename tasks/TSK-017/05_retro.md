# Task Stage Contract: 05_retro

## Task Metadata
- **Task ID:** TSK-017
- **Experiment Ref:** EXP-001..EXP-007
- **Title:** Evidence Integrity & CRLF Disablement for Telemetry Artifacts
- **Status:** CLOSED
- **Date Completed:** 2026-10-04
- **Owner:** Systems Engineering & Infrastructure Agent

---

## 1. Retrospective & Learnings
- **Root Cause:** In Windows environments with default `core.autocrlf=true`, git converts LF to CRLF in text files upon checkout. Since NDJSON telemetry evidence files are hashed byte-for-byte by SHA-256 in `validate_evidence_file()`, CRLF translation mutated the hashes, causing 12 of 14 live runs to be categorized as `historical` due to `evidence_hash_mismatch`.
- **Remediation:** Added `.gitattributes` marking `experiments/evidence/*.ndjson -text` to prevent automatic CRLF normalization while preserving byte-exact SHA-256 verification.
- **Propagation:** Updated `docs/log.md`.
