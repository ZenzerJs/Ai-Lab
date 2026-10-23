# Task Stage Contract: 02_plan

## Task Metadata
- **Task ID:** TSK-021
- **Title:** Research Report: ICM Governance Overhead vs. Break-Even Task Complexity
- **Status:** APPROVED
- **Date Created:** 2026-10-04
- **Owner:** Systems Engineering & Research Agent
- **Task Contract Ref:** ICM Pipeline

---

## 1. Technical Architecture & Analysis Framework
1. **Empirical Token Accounting Model:**
   $$\text{Spend}_{\text{ICM}} = \text{Fixed Contract Overhead} + \text{Bounded Execution Spend}$$
   $$\text{Spend}_{\text{Baseline}} = \text{Minimal Intake Overhead} + \text{Unbounded Discovery Churn}$$
2. **Analysis Dimensions:**
   - Baseline vs. ICM token breakdown (input, output, cache-read, total tokens).
   - Task complexity markers: Lines of Code (LOC), number of target files, cyclomatic complexity, test requirements.
   - Break-even derivation.

---

## 2. OKR Acceptance Matrix

| Objective | Key Result | Machine-Verifiable Exit Command | Expected Value | Status |
|---|---|---|---|---|
| **O1: Quantitative Derivation** | KR1.1: Break-even complexity threshold identified | `python scripts/filter_output.py python scripts/lint_frontmatter.py` | `exit=0` | PENDING |
| **O2: Concept Documentation** | KR2.1: Concept document created in `docs/concepts/` | File existence of `docs/concepts/icm-breakeven-analysis.md` | Exists & valid OKF | PENDING |

---

## 3. Exit Criteria
- [ ] Empirical break-even threshold calculated and documented.
- [ ] Frontmatter linting passes.
