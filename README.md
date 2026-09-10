# Antigravity AI-Lab

> **Deterministic autonomous agent engineering:** ICM stage contracts, Google Cloud OKF v0.2 knowledge graphs, AST code navigation, and an empirical token-savings measurement system.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)
[![OKF: v0.2 Compliant](https://img.shields.io/badge/OKF-v0.2_Compliant-4285F4?style=flat-square)](https://github.com/GoogleCloudPlatform/open-knowledge-format)
[![CI: Passing](https://img.shields.io/badge/CI-Passing-brightgreen?style=flat-square)](https://github.com/ZenzerJs/Ai-Lab/actions)
[![Empirical Savings: 61.58%](https://img.shields.io/badge/Empirical_Savings-61.58%25-success?style=flat-square)](https://zenzerjs.github.io/Ai-Lab/)
[![Live Dashboard](https://img.shields.io/badge/Live_Dashboard-GitHub_Pages-0969DA?style=flat-square&logo=githubpages&logoColor=white)](https://zenzerjs.github.io/Ai-Lab/)
[![Deploy Dashboard](https://github.com/ZenzerJs/Ai-Lab/actions/workflows/deploy-dashboard.yml/badge.svg)](https://github.com/ZenzerJs/Ai-Lab/actions/workflows/deploy-dashboard.yml)

🔗 **Live Interactive Dashboard & Frontier Simulator:** [https://zenzerjs.github.io/Ai-Lab/](https://zenzerjs.github.io/Ai-Lab/)

---

## Current Status & Benchmark Telemetry

> **Empirical Benchmark Status:** Pre-registered trials (`EXP-001` through `EXP-004`) evaluated against `gemini-3.8-flash` across 16 runs: 8 baseline and 8 ICM. The `EXP-005` group ran the identical protocol conversationally on **GLM 5.3 Flash via FreeBuff** (16 operational runs: turns, duration, outcome — see §3.6).
>
> **Measured Results:** The Interpretable Context Methodology (ICM) demonstrated a **61.58% cost reduction** ($0.37910 baseline vs. $0.14566 ICM). It increased the **cache-read-to-fresh-input ratio** from **4.8% to 390.5%** through byte-stable prompt prefixes. On GLM 5.3 Flash, ICM **eliminated all shipped defects** (0/8 vs. 2/8 baseline) at the cost of +65% wall-clock overhead.

### Core Empirical Findings

| Benchmark Target | Methodology Delta | Key Empirical Outcome | Verification Type |
| :--- | :--- | :--- | :--- |
| **`gemini-3.8-flash`** | Context Isolation & Prefix Caching | **61.58% Net Cost Reduction** (Cache Hit Ratio: 4.8% → 80.1%) | Empirical CLI Telemetry (n=16) |
| **`glm-5.3-flash`** (FreeBuff) | Deterministic Stage Contracts | **0 Shipped Defects** vs. 2 Baseline Defects (+65% execution latency) | Operational Reliability Benchmark |
| **Frontier Class** | Simulated Rate Cards | $0.50 → $2.20+ net saved per task on Opus 5, Astra GPT-6, and Fable 5 | Mathematical Simulation |

> [!WARNING]
> **Empirical Limitations Callout:**
> *FreeBuff provider endpoints do not expose native token counters; GLM 5.3 Flash results reflect operational turn count, duration, and defect-free execution only, not token accounting.* All dollar figures for GLM 5.3 Flash simulate OpenRouter public discounted API rates ($0.075 input / $0.015 cache / $0.25 output per MTok) for structural comparison and are never commingled with Gemini empirical actuals.

| Milestone | Status | Details |
| :--- | :--- | :--- |
| **Scaffolding & Directives** | Verified | ICM stage contracts and OKF v0.2 knowledge graph |
| **Token Control Scripts** | Verified | AST symbol extraction (`repo_map.py`) and CLI log sanitization |
| **Measurement Harness** | Verified | Headless A/B runner (`run_experiment.py`) and SQLite ledger |
| **Local Dashboard** | Active | Vite + React + Tailwind app with Model Rate Card Simulator, custom SVG telemetry charts, and the EXP-005 operational benchmark view (`localhost:5173`) · [**Live on GitHub Pages →**](https://zenzerjs.github.io/Ai-Lab/) |
| **Empirical Trials (`EXP-001–004`)** | Complete | 16 runs evaluated on `gemini-3.8-flash` with 61.58% measured savings |
| **Operational Benchmark (`EXP-005`, GLM 5.3 Flash)** | Complete | 16 runs via FreeBuff coding agent — 0/8 ICM defects vs. 2/8 baseline, +65% stage overhead |
| **Model Spend Cascade Engine** | Active | Dynamic re-pricing across Flash, Pro, GPT-4o, Claude 3.7 Sonnet, Claude Sonnet 4.6, Claude Sonnet 5, and GLM 5.3 Flash (provider-equivalent) |

**The problem:** AI coding agents burn tokens re-reading whole repositories, hallucinate from stale context, and declare untested code "done."

**The fix:** a governance layer that treats the filesystem as the agent's state machine. It uses bounded context per stage, AST navigation instead of file dumps, machine-verifiable completion gates, and an A/B harness that *measures* whether any of it actually saves tokens.

> [!IMPORTANT]
> **Empirical Benchmark vs. Rate-Card Simulation Disclaimer:**
> - **Empirical Benchmark (`gemini-3.8-flash`):** All 16 experimental runs across `EXP-001` through `EXP-004` (8 baseline, 8 ICM) were executed live against the `gemini-3.8-flash` endpoint using Antigravity's headless CLI event stream, measuring actual prompt tokens, prompt-cached tokens, completion tokens, turn counts, and wall-clock latencies.
> - **Rate-Card Simulated Models (`claude-sonnet-4-6`, `claude-sonnet-5`, `claude-3-7-sonnet`, `gpt-4o`, `gemini-2.5-pro`, `gemini-2.5-flash`, `glm-5.3-flash`):** These models were **not** executed over paid live API endpoints. Instead, the simulation engine in `scripts/ledger.py` and `dashboard/` takes the exact empirical token workload (input tokens, prompt-cached tokens, output tokens) captured during the live `gemini-3.8-flash` trials and re-prices it against the published official rate cards from Anthropic, OpenAI, and Google (`config/PRICING.json`). This simulates the theoretical dollar economics and prompt-caching savings of the identical workload across higher-cost foundation models without making paid live API calls to those specific endpoints.

> [!NOTE]
> **Status:** fully bootstrapped, empirical trials complete, and smoke-verified. The measurement ledger contains **16 empirical runs across 4 benchmark tasks** on `gemini-3.8-flash`, with dynamic rate-card simulations for `gemini-2.5-pro`, `gemini-2.5-flash`, `gpt-4o`, `claude-3-7-sonnet`, `claude-sonnet-4-6`, and `claude-sonnet-5`.

---

## Table of Contents

1. [System at a Glance](#1-system-at-a-glance)
2. [The Task Lifecycle](#2-the-task-lifecycle)
3. [The Measurement Layer](#3-the-measurement-layer)
   - [3.1 Fairness Invariants](#31-fairness-invariants)
   - [3.2 Cache-Aware Cost Formula](#32-cache-aware-cost-formula)
   - [3.3 Why the Pipeline Arm Should Win](#33-why-the-pipeline-arm-should-win)
   - [3.4 Dashboard Views & Simulation Controls](#34-dashboard-views--simulation-controls)
   - [3.5 Spend Cascade Across Foundation Models](#35-spend-cascade-across-foundation-models)
   - [3.6 Operational Benchmark on GLM 5.3 Flash (EXP-005)](#36-operational-benchmark-on-glm-53-flash-exp-005)
4. [Core Components](#4-core-components)
5. [Quickstart](#5-quickstart)
6. [Repository Layout](#6-repository-layout)
7. [Verification Ledger](#7-verification-ledger)
8. [References & Pinned Specifications](#8-references--pinned-specifications)

---

## 1. System at a Glance

The workspace is organized into **six colored layers**. Each layer has one responsibility and only interacts with adjacent layers. The layer model adapts the ICM architecture [2](#8-references--pinned-specifications). The knowledge layer is a conformant OKF v0.2 bundle [1](#8-references--pinned-specifications).

| Color | Layer | Directory | Responsibility |
|:---:|---|---|---|
| ⬜ | Operator | `/Ai-Lab` commands | Human control surface |
| 🟧 | Governance | `.agents/rules/` | Seven invariants the agent cannot bypass |
| 🟪 | Tool Infrastructure | `.agents/mcp_config.json` | Sandboxed MCP servers [3](#8-references--pinned-specifications) |
| 🟦 | Task Pipeline | `tasks/TSK-XXX/` | Five-stage lifecycle with approval gates [2](#8-references--pinned-specifications) |
| 🟩 | Knowledge Base | `docs/` | Linked, validated OKF v0.2 documentation graph [1](#8-references--pinned-specifications) |
| 🟥 | Measurement | `scripts/` + `dashboard/` | A/B experiment harness and savings analytics |

```mermaid
flowchart TD
    classDef human fill:#FAFAFA,stroke:#616161,color:#333
    classDef gov fill:#FFF3E0,stroke:#F57C00,color:#333
    classDef mcp fill:#F3E5F5,stroke:#7B1FA2,color:#333
    classDef task fill:#E3F2FD,stroke:#1976D2,color:#333
    classDef gate fill:#FFEBEE,stroke:#C62828,color:#333
    classDef know fill:#E8F5E9,stroke:#388E3C,color:#333
    classDef meas fill:#FCE4EC,stroke:#C2185B,color:#333

    User(("👤 Operator")):::human
    Agent["🤖 Autonomous Agent"]:::human
    User -->|"/Ai-Lab"| Agent

    subgraph GOV ["🟧 GOVERNANCE: .agents/rules/"]
        direction LR
        G1["Byte-stable<br/>context"]:::gov
        G2["Diff-only<br/>editing"]:::gov
        G3["AST context<br/>isolation"]:::gov
        G4["Log<br/>sanitation"]:::gov
        G5["Session<br/>resume"]:::gov
    end

    subgraph MCP ["🟪 SANDBOXED TOOLS: MCP servers"]
        direction LR
        M1["git"]:::mcp
        M2["filesystem<br/>8-root sandbox"]:::mcp
        M3["sequential-thinking<br/>02_plan only · ≤10 steps"]:::mcp
    end

    subgraph PIPE ["🟦 TASK PIPELINE: tasks/TSK-XXX/"]
        direction LR
        T1["01_intake<br/>budgets"]:::task
        T2["02_plan<br/>OKR matrix"]:::task
        OKR{"⛔ OKR<br/>GATE"}:::gate
        T3["03_exec<br/>diff-only"]:::task
        T4["04_verify<br/>telemetry"]:::task
        T5["05_retro<br/>learnings"]:::task
        T1 --> T2 --> OKR --> T3 --> T4 --> T5
    end

    subgraph KNOW ["🟩 KNOWLEDGE BASE: docs/ (OKF v0.2)"]
        direction LR
        K1["index.md"]:::know
        K2["concepts/"]:::know
        K3["schemas/"]:::know
        K4["log.md"]:::know
        K1 --> K2
        K1 --> K3
        K1 --> K4
    end

    subgraph MEAS ["🟥 MEASUREMENT: experiments + dashboard"]
        direction LR
        E1["run_experiment.py<br/>A/B runner"]:::meas
        E2["ledger.py<br/>SQLite"]:::meas
        E3["dashboard/<br/>React + Recharts"]:::meas
        E1 --> E2 --> E3
    end

    Agent -.->|"constrained by"| GOV
    Agent <-->|"calls"| MCP
    Agent -->|"executes"| PIPE
    PIPE <-.->|"reads / writes"| KNOW
    T5 -.->|"retros feed docs"| KNOW
    MEAS -.->|"benchmarks both arms"| Agent
```

---

## 2. The Task Lifecycle

Every task follows the five-stage lifecycle adapted from the Interpretable Context Methodology [2](#8-references--pinned-specifications). A human approval gate separates planning from execution.

```mermaid
sequenceDiagram
    autonumber
    participant D as 👤 Operator
    participant A as 🤖 Agent
    participant T as tasks/TSK-XXX/
    participant K as 🟩 docs/

    D->>T: Copy tasks/_template
    A->>T: 01_intake: scope and budget ≤ 8k tokens/turn
    A->>K: Read OKF concept slice using AST queries
    A->>T: 02_plan: create OKR Acceptance Matrix
    Note over A,T: ⛔ HUMAN APPROVAL REQUIRED BEFORE EXECUTION
    A->>T: 03_exec: apply Search/Replace edits
    A->>T: 04_verify: run filtered tests and record telemetry
    A->>T: 05_retro: capture lessons learned
    A->>K: Append update to docs/log.md
```

| Stage | Contract | Scope & Governance Hard Limits |
|---|---|---|
| `01_intake` | `01_intake.md` | Scope boundaries, constraints, out-of-scope declarations; active turn budget ≤ 8,000 tokens |
| `02_plan` | `02_plan.md` | Technical architecture, impacted files manifest, and machine-verifiable OKR matrix; sequential-thinking ≤ 10 steps |
| `03_exec` | `03_exec.md` | Diff-only Search/Replace change tracking, symbol modification ledger; whole-file rewrites > 50 lines barred |
| `04_verify` | `04_verify.md` | Automated test assertions, linter outputs via `scripts/filter_output.py`, and token telemetry ledger |
| `05_retro` | `05_retro.md` | Retrospective observations, learnings, and OKF knowledge propagation into `docs/` and `docs/log.md` |

---

## 3. The Measurement Layer

The same task runs through **two arms**: an unconstrained baseline agent and the full ICM pipeline. Token usage is captured from Antigravity's headless CLI `stream-json` event stream [8](#8-references--pinned-specifications). Four enforced fairness invariants keep the comparison consistent.

```mermaid
flowchart LR
    classDef startNode fill:#FAFAFA,stroke:#616161,color:#333
    classDef base fill:#FFEBEE,stroke:#C62828,color:#333
    classDef icm fill:#E3F2FD,stroke:#1976D2,color:#333
    classDef data fill:#FCE4EC,stroke:#C2185B,color:#333

    T["📋 experiments/tasks/<br/>EXP-001.md"]:::startNode
    R["⚙️ run_experiment.py<br/>4 fairness invariants"]:::startNode
    B["🔴 BASELINE<br/>raw prompt · no scaffolding"]:::base
    I["🔵 ICM PIPELINE<br/>01_intake → 04_verify"]:::icm
    N["📊 NDJSON usage stream<br/>input · output · thinking · cache_read · turns"]:::data
    L["💾 ledger.py + usage.db<br/>cache-aware pricing (config/PRICING.json)"]:::data
    D["📈 dashboard/<br/>React + Recharts savings UI"]:::data

    T --> R
    R -->|arm 1| B
    R -->|arm 2| I
    B --> N
    I --> N
    N --> L
    L --> D
```

### 3.1 Programmatic Fairness Invariants

The experiment runner (`scripts/run_experiment.py`) strictly enforces four programmatic fairness invariants prior to and between every trial, immediately aborting execution with exit code `1` if any invariant fails:

1. **Model ID Match (`model_baseline == model_icm`):** Both arms execute against the exact identical foundation model identifier to eliminate cross-model performance divergence.
2. **Clean Worktree via Git Clean (`git checkout -- . && git clean -fd`):** Guarantees an identical, pristine repository worktree between every individual trial, removing any residue, generated code, or stray artifacts.
3. **Identical Prompt Bytes (`prompt_baseline.encode("utf-8") == prompt_icm.encode("utf-8")`):** Both arms receive bit-for-bit identical task instructions and requirements.
4. **Statistical Sample Size Floor ($n \ge 2$):** Rejects any single-run evaluations. The default protocol executes $n = 3$ runs per arm (or $n = 2$ for balanced multi-task matrices).

### 3.2 Cache-Aware Cost Formula & Rate Card Auditability

$$\text{Cost} = \frac{\text{Input} \times \text{Input Rate} + \text{CacheRead} \times \text{Cache Rate} + \text{Output} \times \text{Output Rate}}{10^6}$$

All pricing schedules are decoupled from code and maintained in [`config/PRICING.json`](file:///config/PRICING.json). Each rate card explicitly records verified provider source URLs and fetch timestamps to ensure full mathematical auditability:

| Provider / Model Tier | Input ($/MTok) | Cache Read ($/MTok) | Output ($/MTok) | Published Rate Card Source | Pricing Mode |
|---|:---:|:---:|:---:|---|---|
| **`gemini-3.8-flash`** | $0.75 | $0.075 | $3.75 | [Google AI Pricing](https://ai.google.dev/gemini-api/docs/pricing) | Live Measured |
| **`gemini-2.5-flash`** | $0.30 | $0.030 | $2.50 | [Google AI Pricing](https://ai.google.dev/gemini-api/docs/pricing) | Rate-Card Simulation |
| **`gemini-2.5-pro`** | $1.25 | $0.125 | $10.00 | [Google AI Pricing](https://ai.google.dev/gemini-api/docs/pricing) | Rate-Card Simulation |
| **`claude-3-7-sonnet`** | $3.00 | $0.300 | $15.00 | [Anthropic Pricing](https://www.anthropic.com/pricing) | Rate-Card Simulation |
| **`claude-sonnet-4-6`** | $3.00 | $0.300 | $15.00 | [Anthropic Pricing](https://www.anthropic.com/pricing) | Rate-Card Simulation |
| **`claude-sonnet-5`** | $2.00 | $0.200 | $10.00 | [Anthropic Pricing](https://www.anthropic.com/pricing) | Rate-Card Simulation |
| **`gpt-4o`** | $2.50 | $1.250 | $10.00 | [OpenAI API Pricing](https://openai.com/api/pricing) | Rate-Card Simulation |
| **`glm-5.3-flash`** † | $0.075 | $0.015 | $0.25 | [OpenRouter Z-AI Rates](https://openrouter.ai/z-ai/glm-5.3-flash) | Provider-Equivalent |

### 3.3 Why the Pipeline Arm Should Win

| Mechanism | Baseline arm | ICM arm |
|---|---|---|
| File access | Full-file dumps each turn | AST symbol slices [4](#8-references--pinned-specifications) (~20–50 tokens) |
| Test output | Raw 3,000-line dumps | One-line summaries and isolated failures |
| Prompt prefix | Changes every turn, causing cache misses | Byte-stable, allowing cache reuse |
| Completion | Agent-declared | Machine-verified OKR gate |

### 3.4 Dashboard Views & Simulation Controls

1. **Model Rate Card Simulator:** Dynamically re-prices recorded token workloads across foundation models (`gemini-3.8-flash`, `gemini-2.5-pro`, `gemini-2.5-flash`, `gpt-4o`, `claude-3-7-sonnet`, `claude-sonnet-4-6`, `claude-sonnet-5`, and `glm-5.3-flash`). `glm-5.3-flash` is flagged **provider-equivalent**: benchmarked through FreeBuff at $0 direct user cost, with USD figures simulating public discounted API pricing.
2. **Spend Cascade Visualizer:** Compares baseline and ICM economics across 1x, 10x, 100x, 100M, and 1B token scales.
3. **Volume Scale Multiplier:** Projects measured cache savings across 1x, 10x, 100x, and 1M-token workloads.
4. **Per-task cost comparison:** Grouped bars, min–max error bands, and sample tags ($n=X$).
5. **Cache-read ratio:** Dual donuts showing `cache_read_tokens / input_tokens`.
6. **Cumulative measured savings:** Running USD total and timeline curve.
7. **Turns & duration:** Interaction count and latency comparison.
8. **Raw ledger table:** Sortable, searchable, with JSON export and client-side pagination.

### 3.5 Spend Cascade Across Foundation Models

As autonomous-agent tasks grow from small scripts to larger workflows, repeated context injection can drive token use up quickly when prompt prefixes shift and context is unconstrained.

The table below shows how the **same measured token workload** (447k baseline tokens vs. 443k ICM tokens) translates across provider price tiers.

| Model | Rate Card (In / Cache / Out) | Baseline Spend | ICM Spend | Net Savings ($) | Cost Reduction | Projected Savings @ 100M Tokens | Enterprise Savings @ 1B Tokens |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **`gemini-2.5-flash`** | $0.30 / $0.03 / $2.50 | $0.1706 | $0.0727 | **+$0.0979** | 57.4% | +$21.74 | +$217.40 |
| **`gemini-3.8-flash`** | $0.75 / $0.075 / $3.75 | $0.3791 | $0.1457 | **+$0.2334** | 61.6% | +$51.91 | +$519.06 |
| **`glm-5.3-flash`** † | $0.075 / $0.0150 / $0.25 | $0.0357 | $0.0153 | **+$0.0204** | 57.1% | +$4.52 | +$45.24 |
| **`gemini-2.5-pro`** | $1.250 / $0.125 / $10.00 | $0.7029 | $0.2970 | **+$0.4059** | 57.7% | +$90.18 | +$901.77 |
| **`gpt-4o`** | $2.500 / $1.2500 / $10.00 | $1.2359 | $0.7905 | **+$0.4454** | 36.0% | +$98.02 | +$980.24 |
| **`claude-sonnet-5`** | $2.000 / $0.2000 / $10.00 | $1.0109 | $0.3884 | **+$0.6225** | 61.6% | +$138.42 | +$1,384.17 |
| **`claude-3-7-sonnet`** | $3.000 / $0.3000 / $15.00 | $1.5164 | $0.5826 | **+$0.9338** | 61.6% | +$207.63 | **+$2,076.25** |
| **`claude-sonnet-4-6`** | $3.000 / $0.3000 / $15.00 | $1.5164 | $0.5826 | **+$0.9338** | 61.6% | +$207.63 | **+$2,076.25** |

```text
Measured Benchmark Spend (Baseline vs. ICM Pipeline):

gemini-2.5-flash  [$0.1706] ■■■■■■■■■
                  [$0.0727] ■■■■ (-57.4%)

gemini-3.8-flash  [$0.3791] ■■■■■■■■■■■■■■■■■■■
                  [$0.1457] ■■■■■■■ (-61.6%)  ← live-measured model

glm-5.3-flash†    [$0.0357] ■■
                  [$0.0153] ■ (-57.1%)  † provider-equivalent simulation, $0 direct user cost

gemini-2.5-pro    [$0.7029] ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
                  [$0.2970] ■■■■■■■■■■■■■■■ (-57.7%)

gpt-4o            [$1.2359] ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
                  [$0.7905] ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■ (-36.0%)

claude-sonnet-5   [$1.0109] ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
                  [$0.3884] ■■■■■■■■■■■■■■■■■■■ (-61.6%)

claude-3-7-sonnet [$1.5164] ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■

claude-sonnet-4-6 [$1.5164] ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
                  [$0.5826] ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■ (-61.6%)  ← both models, same rate tier

Legend: Top Bar = Baseline (Unconstrained) | Bottom Bar = ICM Pipeline (Governed)
```

#### Focus: Claude Sonnet 4.6 & Claude Sonnet 5 Simulated Economics

Anthropic's prompt caching structure provides a **90% discount** on cache-read tokens ($0.30/M vs. $3.00/M input for Sonnet 4.6 / Sonnet 3.7, and $0.20/M vs. $2.00/M input for Sonnet 5). Because ICM structures context into byte-stable prefixes (increasing cache-read ratios from 4.8% to 390.5%), models with a steep cache discount (`gemini-3.8-flash`: $0.075/M vs. $0.75/M) reach the same **61.6%** reduction as the Claude tiers, while the broader Gemini 2.5 family lands between **57.4% and 57.7%**:

* **`claude-sonnet-4-6` ($3.00 / $0.30 / $15.00 per M tokens):**
  - **Baseline Spend:** $1.5164 | **ICM Spend:** $0.5826
  - **Net Savings:** **+$0.9338 (61.58% cost reduction)**
  - **Normalized Rate per 1M Tokens:** Baseline $3.3904/M → ICM $1.3141/M (+$2.0763 saved per million tokens)
  - **Scale Projections:** +$20.76 at 10M tokens · +$207.63 at 100M tokens · **+$2,076.25 at 1B tokens**
  - **Simulation Method:** Re-prices empirical token telemetry from `EXP-001–004` (447k baseline vs. 443k ICM tokens) using Anthropic's published rates; no live calls to `claude-sonnet-4-6`.

* **`claude-sonnet-5` ($2.00 / $0.20 / $10.00 per M tokens):**
  - **Baseline Spend:** $1.0109 | **ICM Spend:** $0.3884
  - **Net Savings:** **+$0.6225 (61.58% cost reduction)**
  - **Normalized Rate per 1M Tokens:** Baseline $2.2603/M → ICM $0.8761/M (+$1.3842 saved per million tokens)
  - **Scale Projections:** +$13.84 at 10M tokens · +$138.42 at 100M tokens · **+$1,384.17 at 1B tokens**
  - **Simulation Method:** Re-prices empirical token telemetry from `EXP-001–004` using Anthropic's published rates; no live calls to `claude-sonnet-5`.

> [!IMPORTANT]
> **Methodology Reminder on Model Economics:**
> Live empirical runs were conducted solely on `gemini-3.8-flash`. Claude Sonnet, GPT-4o, and Gemini Pro numbers represent deterministic rate-card simulations calculated by evaluating the identical token count distribution (fresh input, cached input, output) against respective provider pricing schedules. They demonstrate theoretical dollar impact without incurring live commercial API charges.

> **Why the gap grows:** Premium models make repeated input and output more expensive [7](#8-references--pinned-specifications). Baseline agents may repeatedly read large files and carry noisy terminal output forward. The ICM pipeline reduces unnecessary context through stable prefixes, AST symbol filtering, and sanitized command output. Exact savings depend on the model, task, and cache behavior.

### 3.6 Operational Benchmark on GLM 5.3 Flash (EXP-005)

Beyond the Gemini token-level trials, the identical four benchmark prompts (`EXP-005-G1`…`G4`, reused verbatim from `EXP-001–004`) were executed end-to-end on **`glm-5.3-flash` through the FreeBuff coding agent** — 2 baseline + 2 ICM runs per task, workspace reset between every run, distinct task IDs keeping GLM data isolated from the Gemini measured totals.

> [!WARNING]
> **Operational Limitations Callout:**
> *FreeBuff provider endpoints do not expose native token counters; GLM 5.3 Flash results reflect operational turn count, duration, and defect-free execution only, not token accounting.*

**This is an *operational* benchmark, not a cost benchmark.** FreeBuff does not expose per-turn token telemetry, so per the protocol's measurement caveat (`experiments/EXP-005-protocol.md`) no token counts or USD figures are derived or invented. What is recorded: conversational turns, wall-clock duration, and outcome (module import + unit-test pass), stored in an isolated `data/ops_exp005.db`.

| Task | Baseline (turns / duration / result) | ICM pipeline (turns / duration / result) |
|---|---|---|
| `EXP-005-G1` String utility | 2 / 47.0s + 28.0s / PASS ×2 | 4 / 78.0s + 41.0s / PASS ×2 |
| `EXP-005-G2` Rate limiter | 2 / 48.5s PASS + 44.4s **FAIL** | 4 / 91.7s + 67.9s / PASS ×2 |
| `EXP-005-G3` AST dead-code finder | 2 / 60.9s **FAIL** + 58.5s PASS | 4 / 95.7s + 98.0s / PASS ×2 |
| `EXP-005-G4` Retry transport | 2 / 81.8s + 91.5s / PASS ×2 | 4 / 146.5s + 141.2s / PASS ×2 |
| **Totals** | **16 turns / 460.6s / 2 defect runs** | **32 turns / 760.0s / 0 defect runs** |

**Findings (pilot, n=2 per arm):**

1. **Reliability:** the ICM stage pipeline **eliminated all shipped defects** (0/8 vs. 2/8 baseline). Both baseline failures were silent, plausible-looking bugs — an injected-clock/wall-clock mix-up in the limiter and an AST visitor-dispatch loss — precisely the defect classes the `02_plan` review and `04_verify` gates are designed to intercept.
2. **Overhead:** governance is not free. ICM adds **+65% wall-clock** and 2× turns on this model; the four stage contracts each cost a tool turn.
3. **Cost-per-working-delivery:** counting only defect-free runs, the baseline mean rises from ~57.6s to a comparable ~65.8s effective cost when its two wasted runs are amortized — narrowing, though not eliminating, the latency gap.
4. **Token hypotheses untested on this provider:** cache-ratio and USD-savings effects (§3.2) require token telemetry that only the Gemini CLI harness exposes; the provider-equivalent rate-card simulation for GLM remains labeled as such everywhere.

The dashboard renders this comparison as an **Operational Benchmark** card in the Experiments tab (per-task duration bars, defect counters, and the overhead/reliability trade-off), sourced from `data/ops_exp005.db` via `dashboard/build_data.py`.

---

## 4. Core Components

### 4.1 Token-Optimization Utilities (`scripts/`)

| Script | Function | Guarantee |
|---|---|:---:|
| `repo_map.py` | Tree-sitter symbol map via grep-ast [5](#8-references--pinned-specifications), counted with tiktoken [6](#8-references--pinned-specifications) | ≤ 2,000 tokens, binary-search pruned |
| `filter_output.py` | Command wrapper and log sanitizer | Success = 1 line; failure = isolated trace |
| `lint_frontmatter.py` | OKF v0.2 schema, casing, and link validator [1](#8-references--pinned-specifications) | Exit 1 on any violation |
| `run_experiment.py` | A/B harness with fairness invariants | Aborts on unfair runs |
| `ledger.py` | SQLite storage and analytics | Auditable cost accounting |

All scripts ship with `.ps1` PowerShell shims and `.sh` POSIX shims for cross-platform parity.

### 4.2 MCP Server Sandboxing (`.agents/mcp_config.json`)

Official MCP reference servers [3](#8-references--pinned-specifications):

| Server | Package | Scope |
|---|---|---|
| `git` | `uvx mcp-server-git` | status / unstaged diff / log as JSON |
| `filesystem` | `@modelcontextprotocol/server-filesystem` | 8 permitted roots: `tasks`, `src`, `docs`, `scripts`, `data`, `experiments`, `dashboard`, and `config`. Root configuration files and `.git/` are protected. |
| `sequential-thinking` | `@modelcontextprotocol/server-sequential-thinking` | `02_plan` only, ≤ 10 steps |

### 4.3 Governance Rules (`.agents/rules/`)

| Rule | Enforcement |
|---|---|
| `context-assembly.md` | Static-before-volatile prompt order and byte-stable cache prefix |
| `diff-only-editing.md` | Search/Replace blocks; escape hatches logged in `03_exec.md` |
| `context-isolation.md` | No full-file reads when AST signatures suffice, queried through ast-grep [4](#8-references--pinned-specifications) |
| `log-sanitation.md` | All commands run through `filter_output.py` |
| `okr-gate.md` | No `02_plan` → `03_exec` without approved OKR matrix |
| `session-resume.md` | New sessions resume from `tasks/`, never from memory |
| `tool-discipline.md` | Git tools barred during planning; sequential-thinking barred during execution |

---

## 5. Quickstart

> [!TIP]
> Run the dry-run path first (`MOCK-001`). It exercises the full pipeline end to end with no model cost.

```bash
# 1. Verify toolchain
python --version && git --version && npx --version && uvx --version

# 2. Install dependencies
npm install -g @ast-grep/cli repomix
pip install grep-ast tiktoken pyyaml
cd dashboard && npm install && cd ..

# 3. Zero-cost smoke verification (synthetic fixtures)
python scripts/run_experiment.py --task MOCK-001 --dry-run
python scripts/ledger.py summary MOCK-001
python scripts/lint_frontmatter.py

# 4. Launch the local dashboard with Model Rate Card Simulator
python dashboard/build_data.py
cd dashboard && npm run dev          # → http://localhost:5173

# 5. Simulate the multi-model spend cascade in terminal
python scripts/ledger.py cascade
python scripts/ledger.py summary --model claude-sonnet-4-6
python scripts/ledger.py summary --model claude-sonnet-5
```

**Run a live A/B benchmark** (requires an authenticated Antigravity CLI and consumes real quota):

```bash
python scripts/run_experiment.py --task EXP-001 --runs 2
python dashboard/build_data.py
```

**Enable the live GitHub Pages dashboard** (one-time, repo owner only):

1. Go to **Settings → Pages → Source → GitHub Actions** in the repo.
2. Push any commit to `main` — the `deploy-dashboard.yml` workflow builds and publishes automatically.
3. Dashboard will be live at: **[https://zenzerjs.github.io/Ai-Lab/](https://zenzerjs.github.io/Ai-Lab/)**

### `/Ai-Lab` Skill Commands

| Command | Action |
|---|---|
| `/Ai-Lab --status` | Cumulative savings and cache ratios |
| `/Ai-Lab --cascade` | Multi-model spend cascade across all configured foundation models |
| `/Ai-Lab --run <TASK-ID>` | Execute a live A/B trial |
| `/Ai-Lab --dashboard` | Rebuild data and launch the dashboard |
| `/Ai-Lab --dry-run` | Replay the synthetic fixture |

---

## 6. Repository Layout

<details>
<summary><strong>Expand full directory tree</strong></summary>

```text
.
├── .agents/            # MCP config, 7 governance rules, 5 agent skills
├── config/
│   └── PRICING.json    # Auditable model rates (source URLs + fetch dates)
├── dashboard/          # Vite + React + Tailwind + Recharts savings UI
├── data/
│   └── usage.db        # SQLite ledger (runs, tasks, pricing)
├── docs/               # OKF v0.2 knowledge bundle (index.md, log.md, concepts/, schemas/)
├── experiments/        # Task definitions + synthetic NDJSON fixtures
├── scripts/            # Cross-platform Python utilities (+ .ps1/.sh shims)
├── src/                # Application source root
└── tasks/              # ICM pipelines (_template/ + TSK-XXX instances)
```

</details>

---

## 7. Verification Ledger

<details open>
<summary><strong>Expand all 19 verified tests: 15 smoke & simulation tests and 4 empirical trials</strong></summary>

| Test | Command | Exit | Result |
|---|---|:---:|---|
| Log sanitizer (success) | `filter_output.py -- python -c "print('ok')"` | `0` | 1-line summary |
| Log sanitizer (failure) | `filter_output.py -- python -c "...; sys.exit(1)"` | `1` | Isolated trace |
| AST extraction | `repo_map.py --target scripts/filter_output.py` | `0` | 283 tokens ≤ 1,800 |
| OKF linter | `lint_frontmatter.py` | `0` | Schema, casing, and links valid |
| MCP config | JSON + PATH validation | `0` | All servers resolvable |
| A/B dry run | `run_experiment.py --task MOCK-001 --dry-run` | `0` | 6 fixture runs recorded |
| Invariant: n < 2 | `run_experiment.py --task MOCK-001 --dry-run --runs 1` | `1` | Correctly aborted |
| Invariant: unknown model | `run_experiment.py --task MOCK-001 --dry-run --model unknown` | `1` | Correctly aborted |
| Empirical Trial `EXP-001` | `run_experiment.py --task EXP-001` | `0` | 4 runs, 60.6% savings |
| Empirical Trial `EXP-002` | `run_experiment.py --task EXP-002` | `0` | 4 runs, 62.2% savings |
| Empirical Trial `EXP-003` | `run_experiment.py --task EXP-003` | `0` | 4 runs, 62.0% savings |
| Empirical Trial `EXP-004` | `run_experiment.py --task EXP-004` | `0` | 4 runs, 61.4% savings |
| Ledger summary | `ledger.py summary` | `0` | Cumulative metrics computed |
| Model spend cascade CLI | `ledger.py cascade` | `0` | Multi-model economics computed |
| Rate-card simulation Sonnet 4.6 | `ledger.py summary --model claude-sonnet-4-6` | `0` | 61.6% savings ($1.516 vs $0.583) |
| Rate-card simulation Sonnet 5 | `ledger.py summary --model claude-sonnet-5` | `0` | 61.6% savings ($1.011 vs $0.388) |
| Rate-card simulation Claude 3.7 | `ledger.py summary --model claude-3-7-sonnet` | `0` | 61.6% savings ($1.516 vs $0.583) |
| Dashboard export | `dashboard/build_data.py` | `0` | Static payload with cascade |
| Frontend build | `npm --prefix dashboard run build` | `0` | 0 type errors, clean bundle |

</details>

> [!NOTE]
> All empirical runs reported in the table above reflect **16 live benchmark runs** across tasks `EXP-001` through `EXP-004` on `gemini-3.8-flash`. All other model figures (`claude-sonnet-4-6`, `claude-sonnet-5`, `claude-3-7-sonnet`, `gpt-4o`, `gemini-2.5-pro`, `gemini-2.5-flash`, `glm-5.3-flash`) are auditable rate-card simulations derived from this empirical token telemetry without making paid live calls to those specific endpoints. `glm-5.3-flash` is additionally benchmarked through the FreeBuff coding agent at **$0 direct user cost** (EXP-005 group, §3.6) as an *operational* benchmark — turns/duration/outcome only, no token telemetry — and its dollar figures are labeled provider-equivalent simulations excluded from measured savings totals.

---

## 8. References & Pinned Specifications

Each reference states **what this project actually adopted** from it, not just a link.

| # | Source | What we used | Where it lives |
|:---:|---|---|---|
| 1 | [Google Cloud Open Knowledge Format v0.2](https://github.com/GoogleCloudPlatform/open-knowledge-format) · pinned `ad30107c` (ref `0b87c52`) | The frontmatter vocabulary (`type`, `title`, `description`, `status`, `verified`, `sources`, `stale_after`), the reserved lowercase `index.md` and `log.md` bundle-root rules, the `okf_version` declaration, and absolute bundle-relative link format. Our linter enforces these as a deliberate house rule, stricter than the base spec, which permits extension keys. | `docs/` bundle · `scripts/lint_frontmatter.py` |
| 2 | [Interpretable Context Methodology](https://github.com/RinDig/Interpretable-Context-Methodology) · pinned `02ba5d8` | The numbered stage-contract lifecycle (`01_intake` → `05_retro`), stage-gated execution, the filesystem-as-state-machine orchestration model, and per-stage context budget discipline. We adapted the five-layer model into this workspace's six-layer layout. | `tasks/_template/` · `.agents/rules/` |
| 3 | [Model Context Protocol](https://modelcontextprotocol.io/) | Three sandboxed tool servers: `server-filesystem` for multi-root mount scoping, `mcp-server-git` for structured git primitives as JSON, and `server-sequential-thinking` for bounded planning, capped at 10 steps during `02_plan`. | `.agents/mcp_config.json` |
| 4 | [ast-grep](https://ast-grep.github.io/) | The agent's interactive structural search and rewrite tool. Grammar-aware queries replace text grep and unnecessary full-file reads during code discovery. | `.agents/skills/repo_map.md` · agent workflow |
| 5 | [grep-ast](https://github.com/Aider-AI/grep-ast) | The Tree-sitter parsing engine inside `repo_map.py`. It extracts class definitions, signatures, and docstrings while stripping function bodies to create a compact structural map. | `scripts/repo_map.py` |
| 6 | [tiktoken](https://github.com/openai/tiktoken) (`cl100k_base`) | BPE token counting for binary-search budget pruning in the repo map. A 1,800-token internal target provides a safety margin for OpenAI-vs-Gemini tokenizer variance and keeps output under 2,000 tokens. | `scripts/repo_map.py` |
| 7 | [Gemini](https://ai.google.dev/pricing) · [Claude](https://www.anthropic.com/pricing) · [OpenAI](https://openai.com/api/pricing) pricing | Published per-million-token rate cards for input, cache-read, and output tokens. These populate `config/PRICING.json` with source URLs and fetch dates, making calculated costs auditable. | `config/PRICING.json` |
| 8 | [Antigravity headless CLI](https://antigravity.google/docs/cli/headless/) | The `--output-format stream-json` NDJSON event stream. This is the measurement primitive that yields per-session `input_tokens`, `cache_read_tokens`, `thinking_tokens`, `num_turns`, and `duration_seconds` for both experiment arms. | `scripts/run_experiment.py` |

---

## Roadmap

- [x] Workspace bootstrap: ICM, OKF v0.2, and token-optimization utilities
- [x] Measurement layer, ledger, and dashboard
- [x] Post-review hardening: Windows batch resolution, BOM handling, case sensitivity, and permissions
- [x] Execute `EXP-001` through `EXP-004` live empirical benchmarks on `gemini-3.8-flash`
- [x] Model rate-card simulation and spend-cascade visualizer
- [x] Publish first measured savings results: 61.58% cost reduction
- [x] GitHub Actions CI: linter, smoke tests, and dashboard build
- [x] GitHub Pages deployment of the live dashboard ([zenzerjs.github.io/Ai-Lab](https://zenzerjs.github.io/Ai-Lab/))
- [x] Execute `EXP-005` GLM 5.3 Flash operational benchmark group via FreeBuff (16 runs; 0/8 ICM defects vs. 2/8 baseline)
