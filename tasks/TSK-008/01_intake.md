# Task Stage Contract: 01_intake

## Task Metadata
- **Task ID:** TSK-008 (EXP-008)
- **Title:** ResumeForge Interview Intelligence System (Multi-File Full-Stack Benchmark)
- **Status:** APPROVED
- **Date Created:** 2026-09-15
- **Target Repository:** C:/Users/jayde/.gemini/config/projects/Resume-Forge
- **Task Contract Ref:** ICM Pipeline

---

## 1. Problem Statement & Objectives
Benchmark the architectural performance of a monolithic agent against a governed hierarchical multi-agent team (backend-core [Max], frontend-ui [Medium], qa-playwright [Low]) implementing an evidence-grounded interview system on active production repository Resume-Forge.

Objectives:
1. Schema extension in prisma/schema.prisma: InterviewSession and InterviewTurn with UUID primary keys and reciprocal relations.
2. Backend API endpoints: POST /api/interview/session, POST /api/interview/turn, GET /api/interview/session/[id].
3. Frontend UI components: Resizable split-console with question stream, response editor, evidence grounding inspector, and scorecard dialog.
4. Test harness: Playwright E2E spec (tests/e2e/interview.spec.ts) validating 3-turn grounded interview flow with zero regressions across existing 524 Vitest unit tests.

---

## 2. Scope Boundaries
Within boundary:
- Schema updates in prisma/schema.prisma
- API routes in src/app/api/interview/
- Domain utilities in src/lib/interview/
- UI components in src/components/interview/
- E2E tests in tests/e2e/ or e2e/

Out of scope:
- Remote third-party LLM billing during benchmark runs.
- Modifying unrelated existing tracker or tailor routes.
- Cloud deployment infrastructure.

---

## 3. Verified Baseline Invariants
- Vitest unit tests: 97 files passed (524 tests).
- TypeScript: tsc --noEmit exit code 0.
- Playwright E2E: smoke tests passing.
- Primary key format: UUID for candidate-facing records.
