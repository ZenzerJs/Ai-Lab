# TSK-022 — Design and implementation plan

Status: APPROVED

## Design direction
Subject: an independent laboratory for agent context economics. Audience: engineers and technical decision makers. Single job: inspect what context governance changes, supported by evidence.

Palette: Canvas #F5F6FA, Paper #FFFFFF, Ink #192238, Night #182137, Iris #6955D8, Sea #167A68. Supporting amber and rust are reserved for qualifications and cost increases. Display: Bricolage Grotesque; body: Manrope; utility: IBM Plex Mono, with system fallbacks.

Layout: persistent ink sidebar, restrained top bar, generous page heading, lavender thesis panel, metric cards, cost comparison with a reading guide, experiment previews. Mobile uses an accessible menu and single-column content. Signature: a context orbit with five actual ICM stages. Quiet surfaces surround it.

```
| AI-Lab  | Workspace / Overview                 Export |
| nav     | Your lab, at a glance.                      |
|         | Context thesis                 stage orbit |
|         | cost       quality       cache              |
|         | comparison chart       reading the results  |
| source  | experiment rows              explore models |
```

Critique: a neon control room would repeat the current cramped aesthetic. Replaced generic glowing metrics with light surfaces, explicit evidence types, and a subject-specific stage orbit. Avoid duplicating the full simulation table on overview. Keep every destination functional and independently addressable through URL hashes.

## Architecture and impacted files
- Replace `dashboard/src/App.tsx`: fetching, hash navigation, async states, page composition, export.
- Replace `dashboard/src/index.css`: semantic tokens, complete responsive workspace design, focus/reduced-motion support.
- Add `dashboard/src/components/workspace/{Shell,Overview,Experiments,Simulator,Evidence,Workbench}.tsx` and `dashboard/src/lib/workspace.ts`.
- Update `dashboard/index.html`: title, description, favicon, font hints.
- Add `dashboard/design-system/MASTER.md`.
- Add five task contracts in `tasks/TSK-022/`.
- Add `docs/concepts/frontend-workspace.md`; update `docs/index.md` and `docs/log.md`.
- Keep old components intact for rollback; new workspace components replace their composition.

## OKR acceptance matrix
| Objective | Deterministic exit criterion | Verification |
|---|---|---|
| Build | TypeScript and production bundle exit 0, including `/Ai-Lab/` assets | `python scripts/filter_output.py -- npm --prefix dashboard run build` with `VITE_BASE_PATH=/Ai-Lab/` |
| Data integrity | Committed snapshot invariants pass | `python scripts/filter_output.py -- python -m pytest tests/browser/test_dashboard_production.py::TestSnapshotIntegrity -q -p no:cacheprovider` |
| Reporting | Existing reporting/export regression suite passes | `python scripts/filter_output.py -- python -m pytest tests/integration/test_reporting_export.py -q -p no:cacheprovider` |
| Knowledge | OKF linter exits 0 | `python scripts/filter_output.py -- python scripts/lint_frontmatter.py` |
| UX | Five hash destinations, model + scale, task search, ledger filter/export, sandbox arm switch; zero horizontal page overflow at 375/768/1440 px; visible keyboard focus | CUA browser assertions against served production build, recorded in `04_verify.md` |

## Gate review
Reviewed and signed off by implementing agent within user's explicit redesign authorization. Criteria are deterministic; source data and calculation functions remain unchanged. No separate user approval is mandated by the local gate. Ready for execution.
