---
type: concept
title: Multi-Dimensional Quality Benchmark Findings
description: Empirical evaluation of ICM vs. Baseline across 11 benchmark tasks using the 5-dimension quality rubric and 95% bootstrap confidence intervals.
status: active
verified: automated-verified
sources:
  - /concepts/measurement-layer.md
  - /concepts/icm-breakeven-analysis.md
---

# Multi-Dimensional Quality Benchmark Findings (`EXP-001`..`EXP-011`)

Evaluated across **11 paired tasks** (`EXP-001`..`EXP-008` retroactive artifact & NDJSON audit + `EXP-009`..`EXP-011` live 6–8 file repository outline runs) using the pre-registered 5-dimension rubric (`TSK-025`/`TSK-026`).

---

## 1. Per-Task Quality Matrix

| Task ID | Archetype | Files | Baseline Score | ICM Score | Quality Delta ($\Delta$) | Key Differentiator |
|---|---|---|---|---|---|---|
| `EXP-001` | Pure-Python Slugify | 2 | 18/20 (90.0%) | 20/20 (100.0%) | **+10.0%** | Baseline hit 1 invalid path tool error (`C:\Users\jayde\AI-Lab\...`) |
| `EXP-002` | Sliding Window Rate Limiter | 2 | 20/20 (100.0%) | 20/20 (100.0%) | **+0.0%** | Parity on single-module backend task |
| `EXP-003` | Resilient Retry Transport | 2 | 8/20 (40.0%) | 16/20 (80.0%) | **+40.0%** | Baseline suffered 4 file-overwrite tool errors; both hit 110 LOC `execute()` |
| `EXP-004` | AST Dead Code Finder | 2 | 20/20 (100.0%) | 20/20 (100.0%) | **+0.0%** | Parity on AST visitor module |
| `EXP-005` | Full-Stack Landing Page | 1 | 23/25 (92.0%) | 24/25 (96.0%) | **+4.0%** | Governed added `aria-label` + semantic `<main>` (+43% fuller UI) |
| `EXP-006` | Transactional Financial Ledger | 3 | 17/25 (68.0%) | 25/25 (100.0%) | **+32.0%** | Baseline had 3 tool errors + missing a11y landmarks; ICM hit 25/25 |
| `EXP-007` | API Gateway Topology Sandbox | 1 | 22/25 (88.0%) | 24/25 (96.0%) | **+8.0%** | Governed included `<main>`, accessible controls, p50/p95/p99 sparklines |
| `EXP-008` | ResumeForge Interview System | 4 | 23/25 (92.0%) | 24/25 (96.0%) | **+4.0%** | Governed added semantic landmarks + live grounding inspector (+174% UI depth) |
| `EXP-009` | Event-Driven Job Queue (Outline) | 7 | 24/25 (96.0%) | 24/25 (96.0%) | **+0.0%** | Both fixed 3-color DFS DAG cycles, atomic lock leasing, and retry jitter |
| `EXP-010` | Knowledge Graph & BM25 (Outline) | 8 | 24/25 (96.0%) | 24/25 (96.0%) | **+0.0%** | Both fixed `#anchor` regex, BM25 zero-div, and inverted-index ghost postings |
| `EXP-011` | Policy API Gateway (Outline) | 6 | 24/25 (96.0%) | 24/25 (96.0%) | **+0.0%** | Both fixed sliding-window burst boundary, `hmac.compare_digest`, and fractional billing |

---

## 2. Pooled 95% Bootstrap Confidence Intervals ($n = 11$ Paired Tasks)

| Rubric Dimension | Mean Delta ($\text{ICM} - \text{Baseline}$) | 95% Bootstrap CI | Statistical Verdict |
|---|---|---|---|
| **Overall Quality (`normalized_pct`)** | **+8.91 percentage points** | **[+2.00%, +17.64%]** | **Statistically significant (> 0)** — CI does not cross zero |
| **Design & Accessibility (`0–5`)** | **+1.00 pt** ($n=7$ UI tasks) | **[+0.29, +1.71]** | **Statistically significant (> 0)** — consistent semantic/a11y superiority |
| **Process Discipline (`0–5`)** | **+0.73 pt** | **[+0.00, +1.64]** | **11 baseline tool errors vs. 1 ICM tool error** across live NDJSON logs |
| **Engineering Practices (`0–5`)** | **+0.64 pt** | **[−0.09, +1.55]** | Positive trend driven by fewer broken tool/edit invocations |
| **Correctness & Maintainability (`0–5`)** | **+0.00 pt** | **[0.00, 0.00]** | Final test pass rate and AST function length achieved parity once converged |
