# TSK-023 — Plan

Status: APPROVED

## Design
Keep the existing light studio. Dark uses the user's Obsidian Violet palette: warm charcoal canvas, neutral graphite cards, plum hero, and amethyst interaction colors. Add a compact Sun/Moon control beside refresh. Keep native model selection; show provider icons next to the selected model and in comparison/evidence rows.

Revised direction approved under user's explicit follow-up: replace the navy experiment with the exact Obsidian Violet palette supplied by the user. Provider plates use the canvas color in dark mode; use official monochrome artwork for legibility. Keep mint for verified states, replace arbitrary category colors and decorative dots with angular audit labels and meaningful icons. In Evidence, use a consistent icon + stacked experiment/model cell and right-aligned numeric columns. Preserve the rest of the layout.

Motion: 220ms ease-out page entrance; 30ms bounded row stagger; 0.97 button press; 200ms drawer entrance; 180ms details fade; short success pulse. Animate transform and opacity only. Reduced motion removes all added transforms, transitions, and stagger delays. No bounce, ambient animation, or new motion dependency.

## File manifest
- Add `dashboard/src/components/workspace/{ThemeToggle,ProviderIcon}.tsx`.
- Add `dashboard/src/workspace-enhancements.css`.
- Add four official assets and source attribution under `dashboard/public/providers/`.
- Patch `dashboard/index.html`, `dashboard/src/main.tsx`, `dashboard/src/App.tsx`, and workspace Shell, Simulator, Evidence components.
- Patch workspace Overview and Experiments for semantic status shapes; add the supplied screenshot's ledger alignment fix. Replace the temporary OpenAI docs favicon with the official monochrome logomark.
- Update `dashboard/design-system/MASTER.md`, `docs/concepts/frontend-workspace.md`, and `docs/log.md`.
- Add task contracts and proof screenshots under `artifacts/TSK-023/`.

## OKR acceptance matrix
| Objective | Deterministic result | Command/check |
|---|---|---|
| Build | TypeScript and Pages production build exit 0 | `python scripts/filter_output.py -- npm --prefix dashboard run build` with `VITE_BASE_PATH=/Ai-Lab/` |
| Theme | Toggle changes root theme; reload retains choice; all five destinations fit 375px and desktop in both modes | CUA assertions, persisted in verification contract |
| Provider marks | All four local images load; Google, OpenAI, Anthropic, GLM labels appear with correct model families | CUA image natural-size assertions and source-asset checks |
| Motion | Entrance/stagger/press styles exist; reduced-motion rule disables them | CUA computed styles and filtered CSS assertions |
| Evidence integrity | Snapshot/types/pricing math unchanged | `python scripts/filter_output.py -- git diff --exit-code -- dashboard/public/data.json dashboard/src/types.ts dashboard/src/lib/recalculate.ts` |
| Accessibility | Dark text/control/chart pairs meet contrast targets | Filtered Python luminance assertions; CUA keyboard/focus checks |
| Knowledge | OKF and whitespace exit 0 | `python scripts/filter_output.py -- python scripts/lint_frontmatter.py`; filtered `git diff --check` |

Gate reviewed and approved by implementing agent under user's explicit feature request. All additions are reversible frontend changes; no separate approval required.
