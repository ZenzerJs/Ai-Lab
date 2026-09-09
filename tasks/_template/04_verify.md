# Task Stage Contract: 04_verify

## Task Metadata
- **Task ID:** TSK-XXX
- **Title:** [Task Name]
- **Status:** ACTIVE | PASSED | FAILED
- **Prerequisite:** `03_exec.md` execution completed

---

## 1. Automated Verification Results (via `filter_output.py`)
*All test executions must be routed through `scripts/filter_output.py`.*

| Verification Item | Command Executed | Exit Code | Result Summary |
|---|---|---|---|
| Unit Test Suite | `python scripts/filter_output.py -- pytest tests/` | 0 | `✓ Command succeeded: pytest tests/` |
| Type Check | `python scripts/filter_output.py -- mypy src/` | 0 | `✓ Command succeeded: mypy src/` |
| Frontmatter Linter | `python scripts/filter_output.py -- python scripts/lint_frontmatter.py` | 0 | `✓ OKF v0.2 Frontmatter Lint Passed` |

---

## 2. Static Analysis & Linter Assertions
- **Linter Findings:** [Zero errors / warnings reported]
- **Type Checking Invariants:** [All public symbols statically typed]
- **AST Structural Conformance:** [Verified via `ast-grep` and `repo_map.py`]

---

## 3. Browser & Interactive Verification Notes
*(Applicable for frontend, UI, or interactive visualization assets)*
- **Target Surface:** `docs/viz.html`
- **Render Status:** Verified in headless / local browser inspection
- **Console Errors:** None detected

---

## 4. Token Telemetry Ledger
*Tracks input and output token consumption per lifecycle stage and tool invocation.*

| Lifecycle Stage | Tool Invocations | Est. Input Tokens | Est. Output Tokens | Stage Total Tokens | Context Limit Compliance (<= 8,000) |
|---|---|---|---|---|---|
| **01_intake** | Read tools, ast-grep | ~2,500 | ~600 | ~3,100 | PASS |
| **02_plan** | Sequential thinking, repo_map | ~3,800 | ~1,200 | ~5,000 | PASS |
| **03_exec** | replace_file_content | ~4,200 | ~900 | ~5,100 | PASS |
| **04_verify** | filter_output, pytest | ~2,800 | ~500 | ~3,300 | PASS |
| **05_retro** | Knowledge ingestion | ~2,000 | ~400 | ~2,400 | PASS |
| **Task Aggregate** | — | — | — | **~18,900** | **ALL TURNS <= 8K** |

---

## 5. Verification Verdict & Sign-Off
- [ ] All OKR Acceptance Matrix key results achieved.
- [ ] Automated commands returned exit code 0.
- [ ] Zero unhandled regression or test failures.
- [ ] Approved to transition to `05_retro.md`.
