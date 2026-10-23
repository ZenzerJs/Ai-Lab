# Task Stage Contract: 02_plan

## Task Metadata
- **Task ID:** TSK-018
- **Title:** Honest Benchmark Reporting & Sandbox Cleanup
- **Status:** APPROVED
- **Date Created:** 2026-10-04
- **Owner:** Systems Engineering & Documentation Agent
- **Task Contract Ref:** ICM Pipeline

---

## 1. Technical Architecture & Impact Manifest
- `[MODIFY] README.md`: Update headline badges and empirical results tables to match `ledger.py summary`.
- `[MODIFY] OVERNIGHT_HANDOFF_VERIFICATION.md`: Add audit correction notice.
- `[DELETE] scripts/html_generator.py`: Remove pre-baked HTML template generator.
- `[MODIFY] scripts/run_experiment.py`: Remove `--output` pre-baked HTML generation logic.

---

## 2. OKR Acceptance Matrix

| Objective | Key Result | Machine-Verifiable Exit Command | Expected Value | Status |
|---|---|---|---|---|
| **O1: Claim Honesty** | KR1.1: No stale 61.58% claims in README | `Select-String README.md -Pattern '61\.58'` | Empty | PENDING |
| **O2: Build & Lint Integrity** | KR2.1: Frontmatter lint, pytest, dashboard build pass | `python scripts/filter_output.py python scripts/lint_frontmatter.py` | `exit=0` | PENDING |

---

## 3. Exit Criteria
- [ ] Stale 61.58% claims replaced with ledger-reproducible 1.92% headline figures and nuanced task breakdown.
- [ ] `html_generator.py` deleted.
- [ ] Frontmatter lint and pytest pass.
