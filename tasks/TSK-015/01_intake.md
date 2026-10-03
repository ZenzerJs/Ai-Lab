# Task Stage Contract: 01_intake

## Task Metadata
- **Task ID:** TSK-015
- **Experiment Ref:** EXP-006
- **Title:** Concurrency-Safe Transactional Ledger with Real-Time Dashboard & E2E Validation
- **Status:** APPROVED
- **Date Created:** 2026-10-03
- **Owner:** Full-Stack & Systems Engineering Agent
- **Task Contract Ref:** ICM Pipeline

---

## 1. Problem Statement & Objectives
Financial ledger systems require extreme integrity: no money can be created or destroyed (zero-sum double-entry constraint), account balances must never drop below allowed limits (non-negative invariants or credit bounds), duplicate requests must be safely deduplicated via idempotency keys, and concurrent transfer requests targeting the same accounts must be serialized or atomically committed without race conditions or dirty reads.

In addition, modern financial platforms require a dark-mode real-time responsive dashboard providing visibility into account balances, ledger transaction logs, system invariants, optimistic UI state management, and clear failure/rejection handling. Finally, an automated Playwright end-to-end verification test suite must deterministically prove balance integrity, optimistic updates, and concurrency invariant safety.

Key Functional Requirements:
1. **Backend Concurrency-Safe Transaction Engine:**
   - Double-entry ledger architecture with entries (debit/credit pairs) where sum of debits == sum of credits.
   - Strict account balance invariants (prevent overdrafts/double spending).
   - Idempotency key registry preventing duplicate processing or replay attacks.
   - Concurrency control (in-memory or SQLite transactional locks with serializable/atomic guarantees) preventing race conditions under high concurrent load.
   - REST API endpoints:
     - `GET /api/accounts`: List accounts with current balances and cleared balances.
     - `GET /api/transactions`: List immutable ledger transaction records with entries and idempotency status.
     - `POST /api/transactions`: Execute atomic double-entry transfer with idempotency key, source account, destination account, and amount.
     - `POST /api/reset`: Reset ledger to clean deterministic seed state for testing.

2. **Frontend Interface:**
   - Modern Tailwind CSS dark-mode dashboard.
   - Live ledger balance cards, real-time transaction ledger table, transfer execution form.
   - Account metrics: Total Liquidity, Transaction Volume, Invariant Status (`BALANCED` / `CORRUPTED`), Idempotency Cache Hits.
   - Micro-interactions: optimistic balance updates, visual pending state, live balance flashing, and clear toast/alert error states for overdrafts or invalid transfers.
   - Accessible form controls with clear labels, ARIA attributes, and keyboard navigability.

3. **Automated QA & Verification Suite:**
   - Playwright end-to-end test suite (`tests/e2e/ledger.spec.ts` or standalone Playwright runner).
   - Test 1: Balance integrity & valid transfer execution.
   - Test 2: Idempotency enforcement (re-submitting identical idempotency key yields cached response without duplicate debit/credit).
   - Test 3: Insufficient funds & balance invariant enforcement (overdraft attempt rejected, UI displays explicit error state).
   - Test 4: Concurrency test firing concurrent transfers simultaneously ensuring zero race conditions, correct final balances, and intact ledger invariants.

---

## 2. Scope Boundaries
The following components are within boundary:
- `experiments/tasks/EXP-006/server.js`: Node.js Express/HTTP concurrency-safe transactional ledger server.
- `experiments/tasks/EXP-006/public/index.html`: Tailwind CSS dark-mode real-time ledger dashboard.
- `experiments/tasks/EXP-006/tests/ledger.spec.js`: Playwright E2E verification test suite.
- `experiments/tasks/EXP-006/package.json`: Project manifest with dependencies and test scripts.
- `tasks/TSK-015/`: ICM stage contracts (`01_intake.md`, `02_plan.md`, `03_exec.md`, `04_verify.md`, `05_retro.md`).

---

## 3. Out-of-Scope Declarations
- External cloud third-party banking APIs (Plaid, Stripe ACH).
- Distributed multi-datacenter consensus algorithms (Raft/Paxos); single-node atomic transactional lock is sufficient and optimal for this benchmark.
- Modifications to other benchmark tasks or directories.

---

## 4. Technical Constraints & Invariants
- **Double-Entry Invariant:** Every transaction $T$ consists of balanced legs where $\sum \text{debits} = \sum \text{credits}$. Total system money is strictly conserved.
- **Account Balance Invariant:** $\text{balance}(A) \ge 0$ at all times for standard asset accounts.
- **Idempotency Invariant:** Requests with identical `Idempotency-Key` headers or payload fields must return the exact prior response without modifying ledger state twice.
- **Concurrency Safety:** Parallel requests must be synchronized via mutex/queue/transaction lock so no balance check-then-act race occurs.
- **UI & Accessibility:** Dark mode theme with high contrast, accessible forms, keyboard controls, responsive down to mobile viewports.

---

## 5. Token Budget Allocation
- **System Persona & Rules:** 1,500 tokens
- **Active Task Contract:** 1,500 tokens
- **File Workspace & Diffs:** 4,000 tokens
- **Margin Headroom:** 1,000 tokens
- **Total Turn Budget:** 8,000 tokens

---

## 6. Exit Criteria & Stage Transition Checklist
- [x] Concurrency and double-entry invariants formulated.
- [x] API contract and UI requirements specified.
- [x] Playwright verification targets planned.
- [x] Transition to `02_plan.md` authorized.
