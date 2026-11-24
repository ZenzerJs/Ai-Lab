# OpenAI/Codex cohort

The matched manifest is `openai_codex_cohort_manifest.json`. It schedules
BENCH-007, BENCH-008, BENCH-014, BENCH-018, BENCH-021, and BENCH-024 across
`baseline`, `icm_v3`, and `icm_staged`, with two repetitions per task-arm pair.
All arms use the priced model ID `gpt-6.2-astra` from `config/PRICING.json`.

From the workspace root, execute the cohort with:

```powershell
python scripts/campaign.py execute-batch --manifest experiments/evidence/openai_codex_cohort_manifest.json --db data/usage.db --cli codex --timeout 600
```

After a live execution, verify the campaign rows in `data/usage.db` and export
the dashboard snapshot with:

```powershell
python dashboard/build_data.py dashboard/public/data.json
```

The runner preserves raw Codex JSONL in each run's evidence file and maps
`turn.completed.usage` counters to the ledger schema for accounting.
