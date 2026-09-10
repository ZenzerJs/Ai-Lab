# Experiment Protocol: EXP-005 (GLM 5.3 Flash via FreeBuff)

- **Date:** 2026-09-09
- **Provider / Agent:** FreeBuff coding agent (`glm-5.3-flash`, unmetered)
- **Target Model:** `glm-5.3-flash`
- **Target Tasks:** `experiments/tasks/EXP-005-G1.md` … `EXP-005-G4.md` (prompts reused verbatim from `EXP-001`–`EXP-004`)
- **Runs per Task:** 2 baseline + 2 ICM (Total runs: 16)

## Pricing Mode: Provider-Equivalent (Not Measured Cost)

FreeBuff provides `glm-5.3-flash` at **$0.00 direct user cost**. Therefore:

- **Actual user cost:** $0.00 — never mixed into the measured USD savings totals
  (`scripts/ledger.py cumulative` only aggregates recorded runs, and no GLM runs are recorded against the Gemini benchmark totals).
- **Provider-equivalent cost:** the identical token workload re-priced against public discounted
  API rates from `config/PRICING.json` (`glm-5.3-flash` entry, `pricing_mode: "provider-equivalent"`):

  | Rate | Value | Source |
  |---|---|---|
  | Input | $0.075 / MTok | [OpenRouter](https://openrouter.ai/z-ai/glm-5.3-flash) |
  | Cache read | $0.015 / MTok | OpenRouter |
  | Output | $0.25 / MTok | OpenRouter |

All GLM dollar figures in the dashboard are clearly labeled **simulated** and must not be
presented as FreeBuff charges or added to the Gemini measured-savings ledger.

## Hypothesis

Executing the same EXP-001–004 prompts through the ICM numbered stage pipeline
(`01_intake` -> `04_verify`) on `glm-5.3-flash` will achieve:
1. **>= 40% reduction** in provider-equivalent, cache-aware cost.
2. **Elevated cache-read ratio** on subsequent turns due to byte-stable prompt prefixes.
3. Reduced conversational turns and wall-clock latency versus the baseline arm.

## Fairness Invariants
- **Prompt Parity:** Exact task prompt bytes passed to both arms (inherited verbatim from EXP-001–004).
- **State Reset:** `git clean -fd && git checkout -- .` executed between every individual run.
- **Model Invariant:** Identical model ID (`glm-5.3-flash`) verified in `config/PRICING.json`.
- **Ledger Isolation:** Distinct `EXP-005-G*` task IDs keep GLM runs out of the `EXP-001`–`004` measured totals.

## Execution Commands

Dry-run harness verification (no model calls; requires a `glm-5.3-flash` fixture section in
`experiments/fixtures/mock_stream.ndjson` before this passes):

```bash
python scripts/run_experiment.py --task EXP-005-G1 --dry-run --runs 2
python scripts/ledger.py summary EXP-005-G1
```

Live benchmark (run inside the FreeBuff coding-agent session for each task):

```bash
python scripts/run_experiment.py --task EXP-005-G1 --runs 2
python scripts/run_experiment.py --task EXP-005-G2 --runs 2
python scripts/run_experiment.py --task EXP-005-G3 --runs 2
python scripts/run_experiment.py --task EXP-005-G4 --runs 2
python dashboard/build_data.py
```

## Telemetry Caveat

If the execution environment does not expose exact per-run token telemetry
(input / cache-read / output tokens), record an **operational benchmark** instead —
success/failure, turns, time-to-completion, and test pass rate — and do **not** invent
token counts or cache accounting. The project's credibility depends on keeping
measured facts separate from simulated values.
