# Task Stage Contract: 01_intake

## Task Metadata
- **Task ID:** TSK-009
- **Title:** GitHub Pages Dashboard — Real Data, Few Impactful Statistics
- **Status:** DRAFT (blocked on Open Decisions §7)
- **Date Created:** 2026-10-03
- **Owner:** Lead Software Architect / Agent

---

## 1. Problem Statement & Objectives
The public dashboard (`dashboard/`, deployed via `.github/workflows/deploy-dashboard.yml`) reads as a pile of
panels and numbers. The user wants it to show **real data** through a **small set of high-impact statistics**.

### Intake Audit Findings (on-disk state, 2026-10-03)
| Finding | Evidence |
|---|---|
| **The published payload has zero eligible measured runs.** | `dashboard/public/data.json`: `has_data=false`, `is_demo_report=true`, `comparison_eligible_runs_count=0` |
| All 32 token-ledger runs are excluded. | Every run in `data/usage.db` gets flagged `legacy_unknown_provenance` + `cost_unavailable` |
| Token rows look hand-entered or synthetic. | Round, near-identical pairs (e.g. EXP-001 `45000/43800`, `9800/9500`); `MOCK-001` is a fixture; no `source_kind` column in `runs` |
| Only live-provenance dataset: EXP-005 operational (`data/ops_exp005.db`). | 16 runs, glm-5.3-flash, no token telemetry. ICM: **0/8 defect runs vs 2/8 baseline**, but **+65% duration** and **2× turns** |
| Headline claims in retros (for example TSK-008's "64.54% cost reduction") don't trace to an eligible ledger row. | `tasks/TSK-008/05_retro.md` vs `data.json` |
| UI surface is large. | 5 tabs, ~14 panel components, `ExecutiveShowcase.tsx` 32 KB, `RawLedgerTable.tsx` 26 KB, rate-card simulator, scale projections (10M/100M), 2 orphan `visual_showcase*.html` pages |

**Root cause:** the page has nothing real to say, so it fills the space with panels, simulations, and projections.
Fixing the layout alone won't solve this. The data has to be fixed first.

### Objective
1. Get a **provenance-clean** dataset that `build_data.py` marks as eligible (`is_demo_report=false`).
2. Replace the 5-tab dashboard with **one scrolling page**: a headline, 3 hero stats, 1 primary chart, 1 per-task table,
   and an expandable "Methodology & raw ledger" section.

---

## 2. Scope Boundaries
- Data provenance: a live re-run campaign and/or a provenance backfill for legacy runs (see §7).
- `dashboard/src/**`: new information architecture, plus removal/consolidation of panels.
- `dashboard/build_data.py`: emit a compact `headline` block (the 3 hero stats + CI/n) on top of the existing payload.
- `dashboard/public/`: remove orphan showcase HTML; keep sandbox outputs only if they're used as proof.
- Browser tests in `tests/browser/test_dashboard_production.py`, updated to the new layout.

## 3. Out-of-Scope Declarations
- Changes to the ICM methodology or the experiment runner semantics.
- New frontier-model paid runs beyond the campaign size approved in §7.
- Restyling `docs/viz.html` (the OKF knowledge graph).

## 4. Technical Constraints & Invariants
- **Honesty invariant:** no hero number may come from a simulation, a projection, or an ineligible run. Each hero stat shows `n` and a source tag.
- **Demo guard stays:** if `is_demo_report=true`, the hero area renders the demo banner and no numbers.
- **Platform Invariant:** Windows (PowerShell) and POSIX parity.
- **Tool Discipline:** no git writes during intake/plan.

## 5. Per-Stage Token Budget Allocation Table
| Slice Component | Allocated Token Budget | Target Description / Pruning Control |
|---|---|---|
| **System Persona & Rules** | 1,500 tokens | `AGENTS.md` + `.agents/rules/` |
| **Tool Definitions (MCP/CLI)** | 1,200 tokens | Compact tool definitions |
| **OKF Knowledge Base Slice** | 1,500 tokens | `docs/concepts/` provenance + eligibility concepts |
| **Repository Map (`repo_map.py`)** | 1,800 tokens | `dashboard/src` symbols only |
| **Stage Contract & History** | 1,200 tokens | This contract |
| **Volatile User Prompt & Headroom** | 800 tokens | User answers to §7 |
| **Total Active Turn Context** | **8,000 tokens** | **Hard Maximum Ceiling** |

---

## 6. Proposed Information Architecture (input to 02_plan)
1. **Headline sentence** generated from the data, e.g. *"Across N verified tasks, ICM cut cost per task by X% (95% CI a–b) with zero quality regressions."*
2. **Three hero stats only:** (a) Δ cost per *passing* task, (b) defect/pass rate baseline vs ICM, (c) cache-hit rate baseline vs ICM. Each shows `n`.
3. **One primary chart:** per-task paired bars or a dumbbell (baseline vs ICM cost), sorted by effect size.
4. **One table:** task × {pass rate, cost, tokens, turns, duration} with Δ columns.
5. **Honest trade-off callout:** latency and turn overhead (EXP-005 shows +65% duration).
6. **Collapsed `<details>`:** methodology, fairness invariants, exclusions, raw ledger, rate-card simulator.

**Cut or demote:** Scale selector and 10M/100M projections, rolling counters, multi-model simulator as a top-level tab,
`CumulativeSavings` timeline (needs a longitudinal series), `visual_showcase*.html`, separate Evidence tab.

---

## 7. Open Decisions (user input required before 02_plan)
1. **Legacy runs (EXP-001…008, MOCK-001):** were they measured from real CLI event logs (so provenance can be backfilled from the logs), or were they illustrative? If illustrative, they drop out of the public numbers.
2. **Live re-run campaign:** OK to run one? Proposed size: 4 tasks × 2 arms × n=3, on one model, with `source_kind=live` and computed cost.
3. **Primary story:** cost savings, quality/defects, or both? This decides which hero stat leads.
4. **Sandbox tab:** keep the side-by-side generated-app viewer as "see the output" proof, or cut it?

---

## 8. Exit Criteria & Stage Transition Checklist
- [x] Problem statement validated against user request
- [x] In-scope and out-of-scope boundaries defined
- [x] Open Decisions §7 answered (resolved in `02_plan.md` §0; legacy rows confirmed as `mock_stream.ndjson` fixtures)
- [x] Token budget verified and approved
- [x] Transition sign-off to `02_plan.md` granted
