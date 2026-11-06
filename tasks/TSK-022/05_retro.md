# TSK-022 — Retrospective

Status: CLOSED

## Result
Replaced the cramped dashboard composition with a distinct research workspace. Separate destinations make experiment inspection, pricing projections, generated artifacts, and raw evidence easier to use. Retained the original data contracts and pricing calculations, including missing-value semantics.

## Lessons
- Font size and spacing both matter: the first visual pass exposed supporting labels that were too small. Enlarged them before delivery.
- Focus restoration must happen after React removes inert from the background; immediate focus inside a close handler fails.
- Preserve page state across navigation, but unmount hidden iframes to stop background artifact work.
- A non-measured snapshot is not necessarily a fixture. Demo, simulation, and unverified states need distinct language.
- Canva worked as an editable art-direction reference with placeholder data. Its geometry and palette were independently adapted to the real React application.

## Knowledge propagation
- Design source of truth: `dashboard/design-system/MASTER.md`.
- Architecture concept: `docs/concepts/frontend-workspace.md`.
- Knowledge catalog and chronological log updated.
- Final production build, OKF validation, and whitespace checks pass. Snapshot and original calculation files have no diff.

## Handoff
Preview the production build at `http://127.0.0.1:4173/Ai-Lab/`. Rebuild with `VITE_BASE_PATH=/Ai-Lab/` before Pages publication. The existing GitHub Pages workflow remains the deployment path. No commit, push, or remote deployment was requested or performed.
