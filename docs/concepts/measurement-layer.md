---
type: concept
title: Usage Harness & Savings Measurement Layer
description: Architecture, fairness invariants, and cache-aware pricing formulas for A/B benchmarking between baseline and ICM pipeline arms.
status: active
verified: human-reviewed
sources:
  - /concepts/architecture-overview.md
---

# Usage Harness & Savings Measurement Layer

The **Measurement Layer** provides empirical token telemetry, cost calculations, and comparative analytics to quantify the economic efficiency of the Interpretable Context Methodology (ICM) against an unconstrained baseline agent arm.

---

## 1. System Architecture

The measurement subsystem consists of four coupled components:

```
+---------------------------+       +---------------------------+
|  Task Definition Markdown | ----> |   scripts/run_experiment  |
|  (experiments/tasks/*.md) |       |   (A/B CLI Orchestrator)  |
+---------------------------+       +-------------+-------------+
                                                  |
                     +----------------------------+
                     |
                     v
       +----------------------------+       +---------------------------+
       |   Headless CLI Execution   | ----> |  NDJSON Stream Parser     |
       |  (antigravity / --dry-run) |       |  (Token & Turn Collector) |
       +----------------------------+       +-------------+-------------+
                                                          |
                                                          v
+---------------------------+               +---------------------------+
|    config/PRICING.json    | ------------> |    scripts/ledger.py      |
|    (Auditable Rates)      |               |     (data/usage.db)       |
+---------------------------+               +-------------+-------------+
                                                          |
                                                          v
+---------------------------+               +---------------------------+
|     Vite / React UI       | <------------ |  dashboard/build_data.py  |
|     (Local Dashboard)     |               | (dashboard/public/data.json)
+---------------------------+               +---------------------------+
```

1. **Task Definitions (`experiments/tasks/<TASK-ID>.md`):** Declarative benchmarks defining identical task prompts, target worktrees, and required run counts.
2. **A/B Experiment Runner (`scripts/run_experiment.py`):** Standalone CLI executing baseline and ICM arms with fairness constraints and `--dry-run` fixture playback.
3. **Usage Ledger (`scripts/ledger.py` + `data/usage.db`):** SQLite persistence engine recording granular runs, turn counts, latencies, and cache-aware costs.
4. **Savings Dashboard (`dashboard/`):** Local Vite + React + TypeScript visualizer computing per-task error bands, cache hit ratios, cumulative savings curves, and execution telemetry.

---

## 2. Fairness Invariants

To eliminate evaluation bias, the runner strictly validates four fairness invariants prior to execution. Any violation triggers immediate process abort with exit code `1`:

1. **Model ID Parity:** Both arms must execute against the identical upstream model identifier (e.g., `gemini-2.5-pro`). Cross-model comparisons are prohibited.
2. **Exact Prompt Bytes Parity:** The raw task prompt passed to both arms must be identical down to the exact byte sequence.
3. **Starting Workspace Cleanliness:** In live execution mode, the target git repository must be reset to a pristine baseline between consecutive runs using:
   ```bash
   git checkout -- . && git clean -fd
   ```
4. **Statistical Sample Lower Bound:** Every benchmark requires a minimum of 2 runs per arm ($n \ge 2$, default 3) to capture variance across stochastic agent turns.

---

## 3. Cache-Aware Pricing Model

Modern foundation models provide multi-tier token pricing where cached prefix tokens cost significantly less than newly processed prompt tokens. The measurement engine calculates costs using cache-aware accounting:

$$\text{Cost}_{\text{USD}} = \frac{(\text{Input Tokens} \times R_{\text{input}}) + (\text{Cache Read Tokens} \times R_{\text{cache\_read}}) + (\text{Output Tokens} \times R_{\text{output}})}{1,000,000}$$

Where:
- $R_{\text{input}}$: USD rate per million fresh input tokens.
- $R_{\text{cache\_read}}$: USD rate per million prompt cache read tokens (typically 75% to 90% cheaper than fresh input).
- $R_{\text{output}}$: USD rate per million generated output tokens.

### Externalized Rate Seeding
Token rates are never hardcoded in application logic. All rates are dynamically seeded into SQLite from `config/PRICING.json` with verifiable upstream source URLs and fetch timestamps.

---

## 4. Empirical Efficiency Drivers in ICM

The measurement layer captures two fundamental architectural advantages delivered by ICM:

1. **Cache Hit Ratio Escalation:** By structuring tasks into deterministic stage contracts (`01_intake` through `04_verify`) and enforcing context assembly ordering, system prompts and knowledge slices hit prompt prefix caches on repeated stages.
2. **Conversational Turn & Latency Reduction:** Structured OKR exit gates and diff-only editing eliminate exploratory wandering, reducing both turn counts and total wall-clock duration.

---

## 5. Verifiable Telemetry Protocol

In accordance with workspace directives, all local testing and CI verification must use synthetic NDJSON fixtures from `experiments/fixtures/mock_stream.ndjson`. Paid model calls are restricted to explicit terminal invocation by human operators.
