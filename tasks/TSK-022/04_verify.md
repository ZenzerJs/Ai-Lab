# TSK-022 — Verification

Status: PASSED

## Automated verification
- Production build: `VITE_BASE_PATH=/Ai-Lab/` with `python scripts/filter_output.py -- npm --prefix dashboard run build` — exit 0. TypeScript passed; Vite emitted separate chunks for secondary destinations.
- Existing snapshot/reporting regressions: `python scripts/filter_output.py -- python -m pytest tests/browser/test_dashboard_production.py::TestSnapshotIntegrity tests/integration/test_reporting_export.py -q -p no:cacheprovider --basetemp=C:/Users/jayde/.gemini/AI-Lab/tasks/TSK-022/.pytest-tmp-02` — exit 0, 21 tests.
- Downloaded full report parsed and compared for exact object equality with committed `dashboard/public/data.json` — passed. Filtered evidence export retained generation/build metadata and the single selected EXP-006 governed verified record — passed.
- Semantic text/button color pairs meet 4.5:1; both chart bar colors meet 3:1 against white — passed via filtered Python luminance assertions.
- Final OKF frontmatter and whitespace checks: see completion record in `05_retro.md`.

The managed Windows sandbox blocked esbuild worker creation and pytest temporary-directory enumeration. Approved local escalations completed these checks. Initial failed attempts were environmental; no weakened verification or source-data changes were used.

## Browser verification
Production preview: `http://127.0.0.1:4173/Ai-Lab/`, including the actual Pages base path. All browser actions used CUA.

| Flow | Observed result |
|---|---|
| Overview | Real snapshot values: 1.9% reduction, separate 0.0% operational defect rate, 85.3% governed cache hit rate; uncertainty shown |
| Experiments | Search returns EXP-006; native details show both arms' usage; nonexistent search shows recovery action; savings filter returns two tasks |
| Simulator | GPT-4o at 10M tokens per arm: $90.58 baseline, $73.61 governed, $16.98 savings; explicitly simulated |
| Page state | Browser Back restores chosen model and scale; ledger task filter survives navigation |
| Evidence | Task, arm, source, evidence filters combine to one record; pagination shows final four of fourteen; sorting changes aria-sort; JSON downloads validated |
| Sandboxes | Governed API gateway content renders; baseline switch and interview selection change actual iframe URLs; inactive iframe count is zero |
| Keyboard | Focus ring visible; menu traps focus; Escape restores menu trigger after inert is removed; navigation moves focus to main, including same-route selection |
| Refresh | Completion announced with fourteen loaded records |
| Responsive | All five destinations have zero page-level horizontal overflow at 375x812, 768x1024, 1440x1100, and 812x375 |
| Runtime | No console errors; existing embedded artifact emits a Tailwind CDN advisory |

Screenshots are in `artifacts/TSK-022/`. Reduced motion is enforced by CSS; operating-system motion preference and 200% browser text scaling were not separately emulated. Browser viewport overrides were reset. Local preview remains available; remote publication was not performed.

## Token telemetry
Exact runtime token counts are not exposed. No synthetic token savings or usage figures are reported. Context was navigated through the repository map, symbol searches, and bounded source ranges.
