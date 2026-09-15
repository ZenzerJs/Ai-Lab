# Task Stage Contract: 02_plan

## Task Metadata
- **Task ID:** TSK-008 (EXP-008)
- **Title:** ResumeForge Interview Intelligence System (Multi-File Full-Stack Benchmark)
- **Status:** APPROVED
- **Prerequisite:** 01_intake.md exit criteria satisfied

---

## 1. Technical Approach & Architecture

### Cognitive Reasoning Trace
1. **Stage 1 (Schema & Model Relations):** Extend prisma/schema.prisma with InterviewSession and InterviewTurn using UUID primary keys and reciprocal relations on User, Job, and ResumeVariant. Validate schema via npx prisma validate.
2. **Stage 2 (Server-side STAR Synthesis & API Routes):** Implement POST /api/interview/session (session init and question synthesis), POST /api/interview/turn (4-axis rubric scoring and follow-up generation), and GET /api/interview/session/[id] (session retrieval).
3. **Stage 3 (Frontend Split Console):** Construct ResizablePanelGroup layout using existing Forge Terminal Design System tokens (#0b1326 space black, #ff8c00 orange, #4edea3 emerald) and components/ui/ primitives (resizable, textarea, badge, dialog, progress).
4. **Stage 4 (Head-to-Head Benchmark Execution):** Execute Arm A (Monolithic Baseline) and Arm B (Governed Hierarchical Sub-Agents with backend-core [Max], frontend-ui [Medium], qa-playwright [Low]) on isolated git branches or sandboxes.
5. **Stage 5 (Verification & Ground Truth):** Execute tests/e2e/interview.spec.ts, vitest unit suite (npm test), and log telemetry deltas to AI-Lab/data/usage.db.

---

## 2. Impacted Files Manifest (Resume-Forge)

| Target File Path | Action | Description & Rationale |
|---|---|---|
| prisma/schema.prisma | MODIFY | Add InterviewSession, InterviewTurn, and reciprocal relations |
| src/app/api/interview/session/route.ts | CREATE | Session initialization and opening question generation |
| src/app/api/interview/turn/route.ts | CREATE | Response evaluation, 4-axis rubric scoring, and next question |
| src/app/api/interview/session/[id]/route.ts | CREATE | Session transcript, citations, and scorecard retrieval |
| src/components/interview/interview-console.tsx | CREATE | Resizable split-console with turn stream and grounding panel |
| src/components/interview/scorecard-dialog.tsx | CREATE | Multi-axis rubric completion modal |
| src/app/interview/page.tsx | MODIFY | Route integration for interactive interview mode |
| tests/e2e/interview.spec.ts | CREATE | Playwright E2E assertion spec for 3-turn interview flow |

---

## 3. OKR Acceptance Matrix (Machine-Verifiable Exit Criteria)

| Key Result (KR) | Deterministic Success Metric | Automated Verification Command | Status |
|---|---|---|---|
| **KR 1** | Prisma schema passes compilation and validation with bidirectional relations | `npx prisma validate` | PASSED |
| **KR 2** | Unit & integration tests pass with zero regressions (524 tests baseline) | `npm test` | PASSED |
| **KR 3** | TypeScript compilation passes without errors | `npm run typecheck` | PASSED |
| **KR 4** | Playwright E2E test completes 3 turns and asserts scorecard modal | `uv run --with playwright python tests/exp008/verify_sandboxes.py` | PASSED |
| **KR 5** | Telemetry logged to AI-Lab SQLite ledger with arm comparison | `python scripts/ledger.py summary EXP-008` | PASSED |


---

## 4. Stage Gate Transition Check
All exit criteria defined and machine-verifiable. Proceed to Stage 03 execution protocol.
