<div align="center">

# 🧪 Ai-Lab

**Context, considered.**

[![CI](https://github.com/ZenzerJs/Ai-Lab/actions/workflows/ci.yml/badge.svg)](https://github.com/ZenzerJs/Ai-Lab/actions/workflows/ci.yml)
[![Dashboard](https://img.shields.io/badge/Dashboard-Live_on_GitHub_Pages-8B73E6?logo=githubpages&logoColor=white)](https://zenzerjs.github.io/Ai-Lab/)
[![Python](https://img.shields.io/badge/Python-Research_Tooling-3776AB?logo=python&logoColor=white)](requirements.txt)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](dashboard/package.json)
[![OKF](https://img.shields.io/badge/Knowledge-OKF_v0.2-8672DA)](docs/SPEC-VERSIONS.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-5470A6)](LICENSE)

**[Open live project](https://zenzerjs.github.io/Ai-Lab/)**

<img src="docs/images/screenshot.jpg" alt="Ai-Lab interface" width="900" />

<sub>Live dashboard showing the published research snapshot.</sub>

</div>

---

## 📋 Contents

- [Overview](#-overview)
- [What the Evidence Says](#-what-the-evidence-says)
- [Key Capabilities](#-key-capabilities)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Getting Started](#-getting-started)
- [Repository Layout](#-repository-layout)
- [How Experiments Are Evaluated](#-how-experiments-are-evaluated)
- [Claims, Limits & Next Steps](#-claims-limits--next-steps)

---

## 💡 Overview

More context does not automatically mean better agent performance. Structure can reduce mistakes, but planning, re-reading, verification, and tool overhead all cost time and tokens.

Ai-Lab studies that tradeoff. It brings together **Interpretable Context Methodology (ICM)** stage contracts, **Open Knowledge Format (OKF)** documentation, AST-based repository navigation, an A/B experiment harness, and a dashboard that separates measured outcomes from simulated pricing.

| Common agent-workflow assumption | What Ai-Lab makes measurable |
|---|---|
| ❌ “More structure always saves tokens” | ✅ Compare **unconstrained baseline** and **governed** runs on cost, runtime, and quality |
| ❌ “A passing agent response means the task is finished” | ✅ Use verification gates, task artifacts, and task-specific assertions |
| ❌ “Every run is comparable” | ✅ Record prompt/model identity, run evidence, source type, and exclusions |
| ❌ “Projected savings are real API spend” | ✅ Label **live token-based estimates** separately from **rate-card simulations** |
| ❌ “A dashboard headline tells the whole story” | ✅ Inspect per-task deltas, confidence intervals, ledger entries, and failure cases |

---

## 📊 What the Evidence Says

> [!IMPORTANT]
> **Current published snapshot:** The checked-in `dashboard/public/data.json` combines **722 tracked runs across 41 tasks (100 model-stratified series)** across six models (`60` `gemini-3.8-flash-low` [50 measured live + 10 archived `imported`], `50` `gemini-4-hydrogen-low` [24 baseline, 24 `icm`, 2 `icm_lite`], `54` `gemini-4-argon-low` [26 baseline, 26 `icm`, 2 `icm_lite`], `18` `claude-sonnet-5-5-low`, `350` `swe-2-max-lightning` [158 baseline, 158 `icm`, 34 `icm_lite`], and `190` `gemini-4-neon-devin` [74 baseline, 74 `icm`, 30 `icm_v2`, 12 `icm_lite`]), alongside `16` separate operational GLM runs (`ops_exp005.db`), `34` deterministic `BENCH-*` regression suites (`BENCH-001`..`BENCH-034`), and our local unit/integration/browser verification suites:
> 1. **Priced live CLI cost snapshot (`gemini-3.8-flash-low`, `gemini-4-argon-low`, `gemini-4-hydrogen-low`, `claude-sonnet-5-5-low`, 172 measured runs):** Effort-suffix pricing (`scripts/ledger.py`) re-priced the 122 Argon/Hydrogen/Claude real-telemetry runs to `cost_status=usage_estimate`, bringing the priced measured pool to **156/172 passing (90.7%)** with **$8.1634 baseline vs. $8.0391 governed (+$0.1243 / +1.5% net USD savings across paired passing runs; macro-average across 41 tasks: +14.2% cost)** and **140 governed (`97` `icm` + `18` `icm_lite` + `25` `icm_v2`) vs. 116 baseline live tool execution errors (`−20.7%` reduction / `+20.7%` more errors in `quality_rubric.tool_errors`)** across all active DB-linked runs. Earlier `EXP-001`..`007` runs established the **~150 LOC / 2+ file break-even threshold** (**+28.1% to +64.3% savings** on multi-file architectures vs. **−200.8%** overhead on micro-tasks).
> 2. **Cross-model multi-file + Adaptive `ICM-Lite` & `ICM v2` regression suites (`BENCH-001`..`034`):** Per-model breakdown: `gemini-4-argon-low` (`54` measured runs, `48/54` passed: `$3.6888` baseline vs. `$3.4563` governed), `gemini-4-hydrogen-low` (`50` measured runs, `49/50` passed: `$2.8255` baseline vs. `$2.7304` governed), `claude-sonnet-5-5-low` (`18` measured runs, `17/18` passed: `$0.3742` baseline vs. `$0.3411` governed), `swe-2-max-lightning` (`350` live isolated Devin trials across `BENCH-001`..`026`, `cost_status=unavailable`, graded by `ProtectedEvaluator`: `242/350` passed — `103/158` baseline, `105/158` `icm`, `34/34` `icm_lite`), and `gemini-4-neon-devin` (`190` live isolated Devin trials across `BENCH-001/004/005/006` + `BENCH-013`..`034`, `cost_status=unavailable`, graded by `ProtectedEvaluator`: `128/190` passed — `48/74` baseline, `49/74` `icm`, `19/30` `icm_v2`, `12/12` `icm_lite` — tool counts, errors, streaks, duration, and pre/post/restored hashes recomputed directly from committed `experiments/evidence/live_BENCH-*_gemini-4-neon-devin_*.ndjson`). In the 90-trial **Batch 5 ICM v2 Showdown** (`BENCH-013`..`034`, 30 matched triplets across `baseline` / `icm` / `icm_v2`), all three arms matched at **19/30 passed (63.3%)**, while `icm_v2`'s pre-injected AST repo-map + Zero-Ceremony Repro-First contract cut mean runtime by **−15.6% vs. ICM v1** (`72.2 s` vs. `85.5 s`, and `−4.2%` vs. baseline's `75.4 s`), mean turns by **−28.1% vs. ICM v1** (`5.03` vs. `7.00`), and logged NDJSON tool steps by **−23.0% vs. ICM v1** (`208` vs. `270`, and `−6.7%` vs. baseline's `223`).
> 3. **5-dimension quality rubric (`EXP-001`..`EXP-011`, 10 evaluated tasks):** Governed execution achieves a **+6.6% mean quality gain (95% CI: +1.6% to +13.0%)**, **+0.83 / 5.00 Design & Accessibility gain (95% CI: +0.17 to +1.50)**, while active DB-linked live tool execution errors across all 722 runs stand at **140 governed (`icm`/`icm_lite`/`icm_v2`) vs. 116 baseline** (`reduction_percent: −20.7%` in `quality_rubric.tool_errors`, driven by 25 sandbox `filter_output.py` errors in `icm_v2`).

### Live-token comparison: seven tasks

| Measure | Unconstrained baseline | Governed / ICM |
|---|---:|---:|
| Estimated total task cost | **$1.3858** | **$1.3592** |
| Prompt cache-hit ratio | **87.8%** | **85.3%** |
| Paired tasks represented | 7 | 7 |
| Live-verified runs | 7 | 7 |

**Net observed difference:** roughly **$0.0266 saved (1.9%)** across this specific seven-task snapshot. USD values are estimates calculated from recorded token usage and rate cards, not a statement of the user's billed API charges.

### Why the per-task results matter

| Task | Baseline cost | Governed cost | Result |
|---|---:|---:|---|
| `EXP-001` — text normalization | $0.0747 | $0.2247 | **Governed cost ~3× as much** |
| `EXP-003` — code analysis | $0.1783 | $0.1283 | **28.1% lower estimated cost** |
| `EXP-006` — transactional ledger | $0.5215 | $0.1861 | **64.3% lower estimated cost** |
| `EXP-007` — API gateway topology | $0.2507 | $0.3381 | **34.8% higher estimated cost** |

The honest finding is **conditional value**: workflow governance helped on some more involved tasks but added overhead to others. With only one run per arm for each task in this published snapshot, these are **descriptive comparisons**, not a robust estimate of average savings.

### Separate operational benchmark: reliability vs. latency

A different **GLM 5.3 Flash / FreeBuff** operational evaluation reported:

| Measure | Baseline | Governed |
|---|---:|---:|
| Runs with observed defects | **2 of 8** | **0 of 8** |
| Total duration | **460.6 s** | **760.0 s** |

That sample shows a possible quality/reliability tradeoff alongside approximately **65% higher total duration**. The FreeBuff endpoint did **not** expose native token counters; these results are **not** combined with the live token-cost comparison above.

### Multi-File Repository Outlines (`EXP-009`..`EXP-011`) & 5-Dimension Quality Rubric

To test the **~150 LOC / 2+ file break-even threshold** (`docs/concepts/icm-breakeven-analysis.md`) and evaluate work quality beyond token cost, we added three 6–8 file starter repository outlines (`EXP-009` event-driven job queue, `EXP-010` knowledge graph & BM25 search, `EXP-011` policy API gateway) and a pre-registered **5-dimension quality scorer** (`Correctness`, `Engineering Practices`, `Maintainability`, `Process Discipline`, `Design & UX`; 0–5 each in `scripts/campaign.py`).

#### 1. Multi-File Outline Token & Pricing Results (`EXP-009`..`EXP-011`, `gemini-3.8-flash`)

| Task (6–8 Files) | Baseline Turns & Cost | ICM Turns & Cost (Raw) | ICM Cost (Cold-Start Normalized) | Net Savings (Raw / Normalized) |
|---|---|---:|---:|---:|
| `EXP-009` — 7-file job queue & DAG | 37 turns · **$0.2769** | 28 turns · **$0.3580** | **$0.1585** | −29.3% / **+42.8%** |
| `EXP-010` — 8-file knowledge graph & BM25 | 15 turns · **$0.1840** | 9 turns · **$0.1222** | **$0.0580** | **+33.6% / +68.5%** |
| `EXP-011` — 6-file policy API gateway | 20 turns · **$0.2206** | 12 turns · **$0.1670** | **$0.0815** | **+24.3% / +63.0%** |
| **3-Task Multi-File Total** | **72 turns · $0.6814** | **49 turns · $0.6472** | **$0.2981** | **+5.0% / +56.3%** |

*Note:* Across `EXP-009`..`EXP-011`, governed execution used **32% fewer turns** (49 vs. 72), **45% fewer uncached input tokens** (`126.3k` vs. `229.5k`), and **58% fewer output tokens** (`14.7k` vs. `34.8k`). Raw ICM cost includes a ~95k prior-session cached prefix; cold-start normalized cost subtracts that shared prefix so both arms start at equal zero context.

#### 2. 5-Dimension Quality Sweep (`EXP-001`..`EXP-011`, $n = 10$ Evaluated Tasks)

While pooled cost across the original 7 tasks had a wide confidence interval crossing zero (−68.3% to +41.1%), the **5-dimension quality delta stays strictly positive**:

| Dimension | Mean Delta ($\text{ICM} - \text{Baseline}$) | 95% Bootstrap CI | Finding |
|---|---:|---:|---|
| **Overall Quality (`normalized_pct`)** | **+4.1%** | **[+1.2%, +8.1%]** | Statistically significant (> 0); peak gain on `EXP-003` (+20%) and `EXP-007` (+8%) |
| **Design & Accessibility (`0–5`, $n=6$ UI)** | **+0.83 pt** | **[+0.17, +1.50]** | Governed UIs consistently include semantic `<main>`, ARIA attributes, and richer state coverage |
| **Live Tool Execution Errors** | **81 vs. 103** | **−21.4%** | Active DB-linked live `EXP` + `BENCH` NDJSON logs record 81 governed vs. 103 baseline tool errors |

**Explore the evidence:** [Dashboard](https://zenzerjs.github.io/Ai-Lab/) · [Published data snapshot](dashboard/public/data.json) · [Quality findings](docs/concepts/quality-benchmark-findings.md) · [Break-even analysis](docs/concepts/icm-breakeven-analysis.md) · [Measurement design](docs/concepts/measurement-layer.md)

---

## ✨ Key Capabilities

| Component | What it provides |
|---|---|
| 🧭 **ICM task lifecycle** | Structured intake → plan → execute → verify → retrospective, with an explicit human approval gate between planning and execution. |
| 🗂️ **OKF knowledge graph** | Versioned documentation, concepts, schemas, and knowledge links to retrieve relevant context without reading the entire repository. |
| 🌳 **AST-aware navigation** | Structural repository maps that prioritize symbols and signatures over large undirected file dumps. |
| 🔬 **A/B experiment runner & outlines** | Repeatable task definitions (`EXP-001`..`EXP-011`), 6–8 file starter repository outlines (`scripts/scaffold_outlines.py`), and telemetry extraction. |
| ⚖️ **5-dimension quality judge & blind A/B** | Pre-registered 0–25 workspace scorer (`score_workspace`), diff blinding (`prepare_blind_ab_packet`), and 95% bootstrap CIs (`compute_quality_ci`). |
| 🧾 **Evidence & cost ledger** | SQLite-backed run records with source classification, SHA-256 hashes, token usage, cache readings, and estimated cost. |
| 📊 **Interactive workspace dashboard** | Obsidian Violet light/dark research workspace with task comparisons, 5-dimension quality CIs, rate-card simulator, live sandboxes, and provenance ledger. |
| 🛡️ **Automated quality checks** | Python unit/integration/browser suites, OKF v0.2 frontmatter linter, and filtered verification runner (`scripts/filter_output.py`). |

### What Ai-Lab refuses to conflate

- **Actual model runs vs. hypothetical repricing.** Model comparisons in the spend simulator are **rate-card projections**, not evidence that those other models executed the same task.
- **Cost vs. quality.** A cheaper run can fail; a more reliable run can take longer.
- **A published snapshot vs. real-time telemetry.** The dashboard reads exported JSON. Refreshing the page does **not** execute agents or query the private SQLite ledger.
- **Individual wins vs. general improvement.** A large saving in one benchmark does not establish a universal benefit.

---

## 🏗️ Architecture

```mermaid
flowchart TD
    O["Operator & task definition"] --> R["A/B experiment runner"]
    R --> B["Baseline arm<br/>unconstrained workflow"]
    R --> G["Governed arm<br/>ICM stage contracts"]
    K["OKF knowledge + AST tools"] --> G
    B --> L["Verified telemetry & SQLite ledger"]
    G --> L
    L --> Q["5-dimension quality scorer & blind A/B judge"]
    L --> D["Static workspace export<br/>React 18 · TypeScript · Custom SVG"]
    Q --> D
```

The governed arm uses a documented task lifecycle:

| Stage | Contract |
|---|---|
| `01_intake` | Bound scope, context, and budget |
| `02_plan` | Define changes, tests, and approval criteria |
| `03_exec` | Apply constrained edits and record changes |
| `04_verify` | Run checks and capture evidence |
| `05_retro` | Record findings for later tasks |

See [architecture overview](docs/concepts/architecture-overview.md), [knowledge index](docs/index.md), and [task definitions](experiments/tasks/).

---

## 🧱 Tech Stack

| Layer | Technology |
|---|---|
| Agent methods | ICM 5-stage contracts, OKF v0.2 knowledge graph, break-even complexity law |
| Research & grading scripts | Python 3.11+, AST (`ast` / Tree-sitter), `tiktoken`, 5-dimension rubric & blind A/B judge |
| Experiment evidence | JSON/NDJSON streams, SQLite ledger, SHA-256 provenance, 95% bootstrap CIs |
| Dashboard workspace | Vite, React 18, TypeScript, custom CSS token system (Obsidian Violet light/dark), bespoke SVG charts |
| Testing | pytest (unit, integration, snapshot, rubric), Playwright browser suites, GitHub Actions |
| Publication | Static GitHub Pages snapshot (`dashboard/public/data.json`) |

---

## 🚀 Getting Started

### 1. Explore the dashboard

```bash
git clone https://github.com/ZenzerJs/Ai-Lab.git
cd Ai-Lab/dashboard
npm ci
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). This serves the checked-in public data snapshot; **no paid model calls or live database are needed**.

### 2. Run the offline verification suite

From the repository root:

```bash
python -m pip install -r requirements.txt
python -m pytest tests/unit/ -v --tb=short
python scripts/lint_frontmatter.py
```

The CI workflow additionally verifies selected production-dashboard behavior, runs a dry-run fixture, and compiles the Vite app.

### 3. Work with the experiment runner (optional)

Only in a **disposable checkout**:

```bash
python scripts/run_experiment.py --task MOCK-001 --dry-run
```

This checks mechanics using a synthetic fixture without invoking a paid model. The runner's isolation workflow can modify or clean its target worktree; inspect the task definition and target path first.

### 4. Regenerate the dashboard data (optional)

```bash
python dashboard/build_data.py
```

**Warning:** The exporter **overwrites** `dashboard/public/data.json`. With no local `data/usage.db`, it can generate a demo/fixture report instead of the published empirical snapshot. Use a disposable clone or back up that file first.

---

## 📁 Repository Layout

```text
Ai-Lab/
├── .agents/
│   ├── rules/                  # Modular ICM governance constraints
│   └── skills/                 # Navigation and run helpers
├── docs/                       # OKF v0.2 knowledge graph, break-even & quality findings
├── experiments/
│   ├── tasks/                  # Benchmark task specs (EXP-001..EXP-011)
│   └── evidence/               # SHA-256 verified live CLI event streams (.ndjson)
├── sandbox/                    # Interactive UI artifacts & multi-file outline runs
├── scripts/                    # Runner, repo_map, ledger, campaign, quality rubric, outlines
├── tasks/                      # ICM 5-stage task contracts (TSK-001..TSK-027)
├── dashboard/
│   ├── src/                    # Obsidian Violet React workspace (Overview, Experiments, Simulator, Sandboxes, Audit)
│   ├── public/data.json        # Published empirical + quality rubric snapshot
│   └── build_data.py           # SQLite & quality rubric → static JSON exporter
├── tests/                      # Unit, integration, rubric, and Playwright browser suites
├── config/PRICING.json         # Audited model rate cards with provenance
└── .github/workflows/          # CI and GitHub Pages deployment
```

---

## 🔒 How Experiments Are Evaluated

The framework is designed around **same-task, same-model, same-prompt** comparisons, with run provenance and explicit exclusions:

1. **Prompt/model parity:** both arms should receive the same task instructions and model.
2. **Worktree isolation:** each trial starts from a known repository state.
3. **Outcome evidence:** usage, duration, completion, and evaluator results are stored with source classification.
4. **Separate accounting:** recorded token counts determine measured-workload estimates; alternate model pricing is an explicitly labelled simulation.
5. **Transparent uncertainty:** task-level variation and limited sample sizes remain visible.

> [!WARNING]
> **Replication matters.** The experiment protocol documents a minimum of two runs per arm; the `EXP-001`..`EXP-007` live cost snapshot represents **one run per arm across seven tasks**, whereas `BENCH-002`/`003`/`007`/`008` run $n=3$ per arm on `gemini-4-hydrogen-low`. Do not describe the 7-task `EXP` slice as a replicated multi-run A/B campaign.

> [!CAUTION]
> Some experiment runners restore and clean target Git worktrees as part of isolation. **Run trials only in disposable clones or dedicated worktrees with no uncommitted work you need to keep.** Never point the runner at your primary development checkout without inspecting its target and cleanup behavior.

---

## 🎓 Claims, Limits & Next Steps

> **The product is the measurement discipline, not an attractive savings percentage.**

- **Two-regime cost & token behavior (`EXP-001`..`EXP-011`, `BENCH-002`/`003`/`007`/`008`):** Pooled across the initial 7-task snapshot (`EXP-001`..`EXP-007`), estimated cost reduction is **1.9% (95% CI: −68.3% to +41.1%)** because fixed 5-stage contract overhead on single-file micro-tasks (`<100 LOC`) offsets savings on larger tasks. Above the **~150 LOC / 2+ file break-even threshold** (`EXP-003`, `EXP-006`, and multi-file `BENCH-*` regression suites on `gemini-4-hydrogen-low`), governed runs cut active live cost (`EXP-003`: −28.1%, `EXP-006`: −64.3%) and multi-file tokens/passing patch (**46,663 vs. 49,861**, −6.4%).
- **Statistically significant quality & hygiene gains (`TSK-025`..`TSK-027`):** Evaluated across 10 paired tasks (`EXP-001`..`EXP-011`, excl. `EXP-006`) on the pre-registered 5-dimension rubric (0–25 scale), governed execution achieves a **+4.1% mean quality improvement (95% CI: +1.2% to +8.1%)**, **+0.83 / 5.00 Design & Accessibility gain (95% CI: +0.17 to +1.50)**, and **21.4% fewer active live tool execution errors** (`81` vs. `103`).
- **Historical single-run claims (`EXP-008`):** Earlier references to `EXP-008` (64.54% cost reduction on ResumeForge) represent a single multi-file pair and are audited separately in the quality sweep rather than pooled into the 7-task `usage.db` cost aggregate.
- **Rate-card simulations:** Token workloads from one source model are repriced against other providers' schedules in the simulator. Repricing does not establish that other models have identical tokenization, caching behavior, or task performance.
- **Operational quality (`EXP-005` FreeBuff):** The 8-vs-8 GLM 5.3 Flash benchmark (`0/8` governed defect runs vs. `2/8` baseline defect runs, +65% duration) has no provider-native token counters and is kept separate from USD token-cost totals.
- **Forward direction:** Expand multi-repetition campaigns ($k \ge 3$ per task) across 20+ multi-file tasks and introduce **ICM-Lite** (single-file contract) for micro-tasks below the 150 LOC break-even threshold.

The most interesting question is not whether governance can make an agent look efficient once. It's **which tasks justify the extra structure, and how confidently we can tell**.

<div align="center">

*Built by [@ZenzerJs](https://github.com/ZenzerJs) · [MIT License](LICENSE)*

</div>
