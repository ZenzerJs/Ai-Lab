# Task Stage Contract: 04_verify

## Task Metadata
- **Task ID:** TSK-027
- **Title:** Full Benchmark Quality Audit (`EXP-001`..`EXP-008`) & Live Multi-File Evaluation (`EXP-009`..`EXP-011`)
- **Status:** COMPLETE
- **Owner:** Systems Engineering & Research Agent

---

## 1. Automated Verification Assertions

| Objective | Command | Exit Code | Result |
|---|---|---|---|
| **O1: Retroactive + New Sweep** | `python scripts/filter_output.py -- python scripts/evaluate_all_quality.py` | `0` | `✓ Command succeeded` (11 tasks scored) |
| **O2: Multi-File Verification** | `python scripts/filter_output.py -- python -m pytest tests/unit/test_quality_rubric.py -q -p no:cacheprovider` | `0` | `✓ Command succeeded` |
| **O3: OKF Bundle Compliance** | `python scripts/filter_output.py -- python scripts/lint_frontmatter.py` | `0` | `✓ Command succeeded` |
