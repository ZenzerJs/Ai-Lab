# Task Stage Contract: 04_verify

## Task Metadata
- **Task ID:** TSK-009
- **Title:** GitHub Pages Dashboard — Real Data, Few Impactful Statistics
- **Status:** PASSED
- **Prerequisite:** `03_exec.md` execution completed
- **Verification Date:** 2026-10-03

---

## 1. Automated Verification Results (via `filter_output.py`)

| Verification Item | Command Executed | Exit Code | Result Summary |
|---|---|---|---|
| **KR 1 (Dashboard Build)** | `npm --prefix dashboard run build` | 0 | Vite + TS compilation clean (1,616 modules transformed, 1.58s) |
| **KR 2 (Python Test Suite)** | `python scripts/filter_output.py python -m pytest` | 0 | 126/126 passed in 31.50s (100% pass rate) |
| **KR 3 (OKF Linting)** | `python scripts/filter_output.py python scripts/lint_frontmatter.py` | 0 | Zero OKF v0.2 frontmatter or link regressions |
| **KR 4 (Live Telemetry & Hash)** | `python scripts/run_experiment.py --task EXP-001 --runs 1 --db data/usage_live.db` | 0 | Live execution via `agy` with byte-exact SHA-256 evidence hashing |
| **KR 5 (Zero Synthetic Claim)** | `python dashboard/build_data.py --db data/usage_live.db` | 0 | Headline stats reflect verified runs with 95% CI and tradeoff transparency |

---

## 2. Telemetry & Provenance Integrity
1. **Provenance Invariant:** Zero fixture replay rows from `data/usage.db` are represented in the live benchmark dashboard.
2. **Honesty Invariant:** Duration overhead (+65%) and higher planning turns from the ICM governance contract are explicitly highlighted in `TradeoffCallout.tsx`.
3. **Data Integrity:** `dashboard/public/data.json` contains `has_data: true`, `is_demo_report: false`, and links to cryptographic SHA-256 evidence hashes in `experiments/evidence/`.
