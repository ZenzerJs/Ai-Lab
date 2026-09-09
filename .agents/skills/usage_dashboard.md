# Agent Skill: `usage_dashboard`

## Overview
The `usage_dashboard` skill exports token telemetry and cache-aware cost metrics from the SQLite usage ledger (`data/usage.db`) to static JSON (`dashboard/public/data.json`) and hosts the responsive Vite + React analytics web dashboard.

## Core Invariants
- **Data Integrity:** Only measured actuals are visualized; speculative or extrapolated projections are barred.
- **Sample Accountability:** Every chart and metric card displays explicit sample counts (`n=X`).
- **Cache Economics:** Accurately reflects discounted prompt cache read rates as defined in `config/PRICING.json`.

## Usage

### Refresh Dashboard Data
```bash
python dashboard/build_data.py
```

### Launch Development Server
```bash
cd dashboard && npm run dev
```

### Build Production Bundle
```bash
cd dashboard && npm run build
```

## When to Use
- Visualizing cost differentials between Baseline and ICM arms.
- Inspecting cache hit ratio distributions per task.
- Auditing raw execution records, turn counts, and token breakdowns.
