# Task Stage Contract: 04_verify

## Task Metadata
- **Task ID:** TSK-025
- **Title:** Multi-Dimensional Benchmark Scoring Rubric (Quality, Design, Engineering, Process)
- **Status:** COMPLETE
- **Owner:** Systems Engineering & Research Agent

---

## 1. Automated Verification Assertions

All verification commands executed via `scripts/filter_output.py` per `.agents/rules/log-sanitation.md`:

| Objective | Command | Exit Code | Result |
|---|---|---|---|
| **O1: Pre-Registered Rubric** | `python scripts/filter_output.py -- python -c "import pathlib; assert pathlib.Path('tasks/TSK-025/01_intake.md').exists() and pathlib.Path('tasks/TSK-025/02_plan.md').exists()"` | `0` | `✓ Command succeeded` |
| **O2: Automated Scorer Unit Suite** | `python scripts/filter_output.py -- python -m pytest tests/unit/test_quality_rubric.py -q -p no:cacheprovider` | `0` | `✓ Command succeeded` (8 tests) |
| **O2: Campaign Regression Suite** | `python scripts/filter_output.py -- python -m pytest tests/unit/test_campaign.py -q -p no:cacheprovider` | `0` | `✓ Command succeeded` |
| **O3: OKF Frontmatter Linter** | `python scripts/filter_output.py -- python scripts/lint_frontmatter.py` | `0` | `✓ Command succeeded` |

---

## 2. Token Telemetry Ledger
- Exact runtime token telemetry is unavailable in IDE chat session; no synthetic figures recorded. Subagent execution delegated to `flash` (`dbb5ec97-f340-4ad2-a724-1fc76a40c73d`) with targeted line reads and sanitized test outputs.
