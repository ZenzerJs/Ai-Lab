# Task Stage Contract: 02_plan

## Task Metadata
- **Task ID:** TSK-XXX
- **Title:** [Task Name]
- **Status:** DRAFT | IN_REVIEW | APPROVED
- **Prerequisite:** `01_intake.md` exit criteria satisfied

---

## 1. Technical Approach & Architecture
[Detailed description of technical solution, design patterns, and modular interfaces.]

### Cognitive Reasoning Trace (Sequential Thinking)
*Operating constraint: Maximum 10 reasoning steps per invocation. Active exclusively during Stage 02_plan.*
1. Step 1: [Problem decomposition]
2. Step 2: [Boundary analysis]
3. Step 3: [Failure mode identification]
...

---

## 2. Impacted Files Manifest

| Target File Path | Action (`CREATE` / `MODIFY` / `DELETE`) | Description & Rationale | Diff Block Required (>50 lines) |
|---|---|---|---|
| `src/...` | `CREATE` | Net-new implementation module | No (new file) |
| `tests/...` | `MODIFY` | Unit test cases for new contracts | Yes (`<<<<<<< SEARCH`) |

---

## 3. OKR Acceptance Matrix (Machine-Verifiable Exit Criteria)

**Objective:** [State high-level technical objective to achieve in this task]

| Key Result (KR) | Deterministic Success Metric | Automated Verification Command (via `filter_output.py`) | Status |
|---|---|---|---|
| **KR 1** | Module exports defined interfaces with zero type errors | `python scripts/filter_output.py -- mypy src/module.py` | PENDING |
| **KR 2** | All new unit tests pass with exit code 0 | `python scripts/filter_output.py -- pytest tests/test_module.py` | PENDING |
| **KR 3** | OKF documentation frontmatter passes linting | `python scripts/filter_output.py -- python scripts/lint_frontmatter.py` | PENDING |

---

## 4. Stage Gate Transition Check
Per `.agents/rules/okr-gate.md`, implementation in `03_exec.md` must not commence until:
- [ ] Technical architecture reviewed and validated.
- [ ] Impacted files manifest completely populated.
- [ ] OKR Acceptance Matrix defined with automated verification commands.
- [ ] Sign-off approved to transition to `03_exec.md`.
