---
task_id: EXP-008
model: gemini-3.8-flash
model_baseline: gemini-3.8-flash
model_icm: gemini-3.8-flash
runs_per_arm: 1
target_repo: C:/Users/jayde/.gemini/config/projects/Resume-Forge
---
# EXP-008: ResumeForge Interview System (Multi-File Full-Stack Benchmark)

Implement an evidence-grounded, multi-turn interview intelligence system for ResumeForge:

1. **Schema & Persistence (prisma/schema.prisma):**
   - Add InterviewSession (id, userId, jobId, variantId, track, status, finalScore, evidenceUsed, turns, timestamps) with @default(uuid()).
   - Add InterviewTurn (id, sessionId, turnIndex, question, response, rubricScores, citations, createdAt).
   - Add reciprocal relations in User, Job, and ResumeVariant.

2. **Backend API Contracts:**
   - POST /api/interview/session: Initialize session from candidate evidence and target job requirements; generate opening question.
   - POST /api/interview/turn: Score response across 4-axis rubric (Technical, Depth, Conciseness, Grounding); record turn; generate follow-up question.
   - GET /api/interview/session/[id]: Retrieve full session state, transcript, evidence mappings, and composite scorecard.

3. **UI Workspace & Components:**
   - Split-console interview layout with ResizablePanelGroup (resizable.tsx).
   - Left pane: Question stream, candidate response textarea, turn progress bar, timer readout.
   - Right pane: Real-time evidence grounding inspector displaying targeted EvidenceItem card with matched keyword spans.
   - Scorecard modal: Accessible dialog.tsx displaying 4-axis rubric breakdown and composite score.

4. **Verification & Ground-Truth Test Harness:**
   - Playwright E2E spec (tests/e2e/interview.spec.ts) validating 3-turn grounded interview and scorecard modal.
   - Zero regressions across existing Vitest unit suite (npm test) and typecheck (npm run typecheck).
