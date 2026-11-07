# Task Stage Contract: 02_plan

## Task Metadata
- **Task ID:** TSK-027
- **Title:** Full Benchmark Quality Audit (`EXP-001`..`EXP-008`) & Live Multi-File Evaluation (`EXP-009`..`EXP-011`)
- **Status:** APPROVED
- **Owner:** Systems Engineering & Research Agent
- **Task Contract Ref:** ICM Pipeline

---

## 1. Execution Architecture & Impacted Files
1. **Retroactive Audit (`EXP-001`..`EXP-008`):**
   - Extract tool-error counts, out-of-scope file touches, test pass status, AST function lengths (`src/*.py`), and HTML/a11y structure (`sandbox/vanilla`, `sandbox/governed`, `sandbox/exp007_*`, `sandbox/exp008_*`) from existing on-disk builds and `.ndjson` evidence logs.
2. **Live Multi-File Execution (`EXP-009`..`EXP-011`):**
   - Run independent `flash` Baseline subagent (unconstrained, no ICM stage contracts or `repo_map`/`filter_output` rules) vs. `flash` ICM subagent (governed with `repo_map`, `filter_output`, diff-only edits) on isolated workspaces scaffolded via `scripts/scaffold_outlines.py`.
3. **Consolidated Quality Report (`scripts/evaluate_all_quality.py` & `docs/concepts/quality-benchmark-findings.md`):**
   - Compute deterministic 5-dimension scores, blind A/B packets, and 95% bootstrap CIs across all 11 tasks (`EXP-001`..`EXP-011`).

---

## 2. OKR Acceptance Matrix

| Objective | Key Result | Machine-Verifiable Exit Command | Expected Value | Status |
|---|---|---|---|---|
| **O1: Retroactive + New Sweep** | KR1.1: `scripts/evaluate_all_quality.py` scores `EXP-001`..`EXP-011` and outputs JSON + summary table | `python scripts/filter_output.py -- python scripts/evaluate_all_quality.py` | `exit=0` | COMPLETE |
| **O2: Multi-File Verification** | KR2.1: `EXP-009`..`EXP-011` test suites pass on ICM builds | `python scripts/filter_output.py -- python -m pytest tests/unit/test_quality_rubric.py -q -p no:cacheprovider` | `exit=0` | COMPLETE |
| **O3: OKF Bundle Compliance** | KR3.1: `docs/concepts/quality-benchmark-findings.md` passes OKF frontmatter linter | `python scripts/filter_output.py -- python scripts/lint_frontmatter.py` | `exit=0` | COMPLETE |
