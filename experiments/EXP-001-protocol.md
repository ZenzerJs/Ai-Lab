# Experiment Protocol: EXP-001 (Rate-Limiting Middleware)

- **Date:** 2026-09-09
- **Evaluator:** Jayden Saha
- **Target Model:** `gemini-3.8-flash`
- **Target Task:** `experiments/tasks/EXP-001.md`
- **Runs per Arm:** 2 (Total runs: 4)

## Hypothesis
Executing the task through the ICM numbered stage pipeline (`01_intake` -> `04_verify`) with AST symbol maps and prompt prefix caching will achieve:
1. **>= 40% reduction** in total cost-weighted USD.
2. **>= 60% cache hit ratio** on subsequent turns due to byte-stable prompt prefixes.
3. Zero untracked terminal log pollution in agent context.

## Fairness Invariants
- **Prompt Parity:** Exact task prompt bytes passed to both arms.
- **State Reset:** `git clean -fd && git checkout -- .` executed between every individual run.
- **Model Invariant:** Identical model ID (`gemini-3.8-flash`) verified in `config/PRICING.json`.

## Execution Command
```bash
python scripts/run_experiment.py --task EXP-001 --runs 2
```
