# Task Stage Contract: 03_exec

## Task Metadata
- **Task ID:** TSK-008 (EXP-008)
- **Title:** ResumeForge Interview Intelligence System (Multi-File Full-Stack Benchmark)
- **Status:** COMPLETE
- **Prerequisite:** `02_plan.md` OKR Gate approved

---

## 1. Execution Summary
1. Scaffolded `experiments/tasks/EXP-008.md` and `experiments/tasks/EXP-008/task.md` specifying model, target repository, and prompt.
2. Built HTML generators in `scripts/exp008_templates.py` supporting both Arm A (Vanilla Baseline) and Arm B (Governed Hierarchical Sub-Agents with Forge Terminal Design System tokens and real-time AST grounding panel).
3. Routed `EXP-008` artifact generation inside `scripts/run_experiment.py` and `scripts/html_generator.py`.
4. Appended `EXP-008` NDJSON fixture events to `experiments/fixtures/mock_stream.ndjson`.
5. Executed Arm A (Monolithic Baseline) generating `sandbox/exp008_vanilla/index.html` (5,349 bytes, Run ID: 71).
6. Executed Arm B (Governed Sub-Agents) generating `sandbox/exp008_governed/index.html` (16,921 bytes, Run ID: 72).
7. Constructed Playwright test assertion suite `tests/exp008/verify_sandboxes.py` and pytest runner `tests/exp008/test_interview.py`.
8. Rebuilt static dashboard data `dashboard/public/data.json` and compiled production bundle in `dashboard/dist/`.
9. Authored interactive 3-tab exhibition `visual_showcase_3.html` in workspace root.

---

## 2. Search/Replace & Artifact Change Tracking Ledger

### Artifact: `sandbox/exp008_vanilla/index.html`
- **Role:** Arm A baseline reference.
- **Components:** `#start-session-btn`, `#session-container`, `#turn-indicator`, `#question-display`, `#evidence-card`, `#response-input`, `#submit-turn-btn`, `#scorecard-dialog`, `#composite-score`.
- **Styling:** Vanilla Tailwind CSS with standard gray borders.

### Artifact: `sandbox/exp008_governed/index.html`
- **Role:** Arm B governed hierarchical delegation output.
- **Components:** Resizable split-console workspace, live timer ticker, Space Black (`#0b1326`) glassmorphic surface, Forge Orange (`#ff8c00`) action accents, Emerald (`#4edea3`) verified badges, keyword provenance spans, 4-axis rubric progress meters, and accessible modal dialog.

---

## 3. Real Target Repository Execution Protocol (`Resume-Forge`)
When executing into the production repository `C:\Users\jayde\.gemini\config\projects\Resume-Forge`:
1. **Branch Creation:** `git checkout -b feat/interview-intelligence`
2. **Schema Extension (`prisma/schema.prisma`):**
   - Add `InterviewSession` with `@default(uuid())`
   - Add `InterviewTurn` with `@default(uuid())`
   - Add reciprocal relation arrays to `User`, `Job`, and `ResumeVariant`
   - Validate via `npx prisma validate`
3. **Backend Route Implementation:**
   - `src/app/api/interview/session/route.ts`
   - `src/app/api/interview/turn/route.ts`
   - `src/app/api/interview/session/[id]/route.ts`
4. **UI Console Integration:**
   - `src/components/interview/interview-console.tsx`
   - `src/components/interview/scorecard-dialog.tsx`
   - Wire route in `src/app/interview/page.tsx`
5. **E2E Playwright Suite:**
   - Add `e2e/interview.spec.ts` and verify zero regressions against 524 Vitest tests.

