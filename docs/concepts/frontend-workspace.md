---
type: concept
title: AI-Lab Research Workspace
description: Frontend structure, evidence semantics, design tokens, and verification for the AI-Lab dashboard.
status: active
verified: agent-reviewed
sources:
  - /concepts/architecture-overview.md
  - /concepts/measurement-layer.md
---

# AI-Lab Research Workspace

The React application in `dashboard/` presents recorded agent experiments in a spacious research workspace. Its visual system lives in `dashboard/design-system/MASTER.md`; semantic CSS tokens live in `dashboard/src/index.css`.

## Frontend boundaries

`App.tsx` owns abortable snapshot fetching and hash navigation. `Shell.tsx` provides persistent desktop navigation, an accessible mobile drawer, refresh, and the full JSON report export. Secondary pages load lazily and retain state after their first visit.

| Destination | Responsibility |
|---|---|
| `#overview` | Recorded headline statistics, per-task cost comparison, and reading guide |
| `#tasks` | Searchable experiment comparisons and separate operational quality results |
| `#simulator` | Source-workload repricing and normalized per-arm volume projections |
| `#sandboxes` | Selection and isolated preview of generated standalone artifacts |
| `#audit` | Source/evidence filters, sorting, pagination, record details, and filtered JSON export |

The original types, `deriveDataForModel`, and recorded snapshot remain independent of presentation. Internal links and assets respect the Vite base path so the workspace runs under GitHub Pages at `/Ai-Lab/`.

## Evidence semantics

Measured headlines require measured data and exclude demo or simulation snapshots. Demo fixtures, simulation snapshots, and unavailable measurements have distinct labels. Missing costs remain dashes. Operational defect results are explicitly separate from token-cost benchmarks. Simulator values are saved rate-card projections rather than live executions of target models; normalized volumes apply independently to each arm.

Full report export preserves the source payload. Filtered export preserves generation/build metadata, selected filters, and matching records. Evidence verification and comparison eligibility are distinct fields.

## Interaction and accessibility

The mobile drawer traps focus, makes background content inert, and restores focus after dismissal. Hash navigation supports browser history and returns focus to the main landmark. Native details controls expose experiment comparisons and evidence references. Dense tables scroll inside labeled regions rather than widening the page.

Secondary pages preserve filters and selections across navigation. Sandbox iframes unmount when inactive; generated artifacts remain isolated with script-only sandbox permissions. Motion preferences disable workspace animation and transitions. Font loading uses swap with system fallbacks.

## Themes, provider marks, and evidence geometry

`ThemeToggle.tsx` handles explicit light/dark choice, system preference changes when no choice exists, and cross-tab synchronization. An inline head bootstrap applies the initial preference before styles load. The locally saved choice uses `ai-lab.theme.v1`.

`workspace-enhancements.css` pairs the light studio with the Obsidian Violet dark palette defined in the design system. Canvas, chrome, cards, and hero are separate semantic surfaces. Buttons and selected states use violet; verified evidence uses restrained mint. Category labels are angular outlines, and decorative status dots are replaced with meaningful icons.

`ProviderIcon.tsx` maps model families to local Google, OpenAI, Anthropic, and Z.ai / GLM assets. Official asset URLs and ownership attribution live in `dashboard/public/providers/README.md`. Dark provider backgrounds match the canvas. Monochrome marks display white for contrast; Google retains its brand colors.

Ledger identity cells place one icon beside a stacked experiment/model label. Input-token and cost headers align right with their values. Verified records use a shield and text rather than a filled chip.

Page entrances, bounded row stagger, press feedback, drawer/detail reveals, and confirmation pulses use transform/opacity. Optional native theme crossfade does not block pointer input. Reduced-motion rules disable the additions, including active transforms. See `TSK-023` for verification and proof.

## Verification and publication

Use the output filter for builds and regression suites. Production checks set `VITE_BASE_PATH=/Ai-Lab/`. Browser verification covers all destinations at phone, tablet, desktop, and landscape dimensions, export content, model projections, keyboard focus, and artifact switching. See task `TSK-022` for observed results and screenshot locations.

The existing GitHub Pages workflow publishes the dashboard. Local source work does not itself update the public deployment.
