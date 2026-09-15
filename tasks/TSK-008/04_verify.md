# Task Stage Contract: 04_verify

## Task Metadata
- **Task ID:** TSK-008 (EXP-008)
- **Title:** ResumeForge Interview Intelligence System (Multi-File Full-Stack Benchmark)
- **Status:** PASSED
- **Prerequisite:** `03_exec.md` execution completed

---

## 1. Automated Verification Results (via `filter_output.py`)

| Verification Item | Command Executed | Exit Code | Result Summary |
|---|---|---|---|
| **KR 1 (Playwright E2E)** | `python scripts/filter_output.py uv run --with playwright python tests/exp008/verify_sandboxes.py` | 0 | 100% compliance across both sandboxes (Turn 1–3 + Scorecard dialog) |
| **KR 2 (Pytest Suite)** | `python scripts/filter_output.py uv run --with pytest-playwright pytest tests/exp008/test_interview.py` | 0 | 2 passed in 1.55s |
| **KR 3 (Ledger Sync)** | `python scripts/ledger.py summary EXP-008` | 0 | Baseline $0.10955 vs Governed $0.03884 (64.54% cost savings) |
| **KR 4 (Dashboard Build)** | `python scripts/filter_output.py npm run build --prefix dashboard` | 0 | Vite + TS compilation clean (1,621 modules transformed) |
| **KR 5 (OKF Linting)** | `python scripts/filter_output.py python scripts/lint_frontmatter.py` | 0 | Zero OKF v0.2 frontmatter regressions |

---

## 2. Telemetry & Metric Assertions (gemini-3.8-flash)

```text
================================================================================
  EXP-008 TELEMETRY DELTA (gemini-3.8-flash)
================================================================================
  Metric                   Arm A (Monolith)    Arm B (Governed Sub-Agents)  Delta
  ─────────────────────────────────────────────────────────────────────────────
  Net Cost / Run           $0.10955            $0.03884                     -64.54%
  Duration (Wall Clock)    64.20s              25.80s                       -59.81% (-38.4s)
  Fresh Input Tokens       114,500             21,200                       -81.48% (-93.3k)
  Prompt Cache Read        8,200 (7.16%)       88,400 (417.0%)              10.8x leverage
  Thinking Budget Spent    2,850 tokens        1,820 tokens                 -36.14% (-1,030 tok)
  Interaction Turns        10 turns            4 turns                      -60.0% (-6 turns)
  Playwright Suite (2/2)   Pass (100%)         Pass (100%)                  Parity
================================================================================
```

---

## 3. Ground-Truth Compliance
1. **Assertion 1:** `#start-session-btn` initialization unhides `#question-display` and `#evidence-card`.
2. **Assertion 2:** Consecutive submissions through Turns 1, 2, and 3 correctly advance `#turn-indicator` (`Turn 1 of 3` -> `Turn 2 of 3` -> `Turn 3 of 3`).
3. **Assertion 3:** Final turn completion launches `#scorecard-dialog` and displays non-empty `#composite-score`.

