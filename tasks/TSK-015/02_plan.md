# Task Stage Contract: 02_plan

## Task Metadata
- **Task ID:** TSK-015
- **Experiment Ref:** EXP-006
- **Title:** Concurrency-Safe Transactional Ledger with Real-Time Dashboard & E2E Validation
- **Status:** APPROVED
- **Date Created:** 2026-10-03
- **Owner:** Full-Stack & Systems Engineering Agent
- **Task Contract Ref:** ICM Pipeline

---

## 1. Technical Architecture

### 1.1 Concurrency-Safe Transaction Engine (`server.js`)
- **State Model:**
  - Accounts: ID, Name, Type (`ASSET`, `LIABILITY`), Balance (represented as integer cents to avoid floating-point drift, e.g. `$100.00 = 10000`).
  - Transactions: ID, Timestamp, IdempotencyKey, SourceAccount, DestinationAccount, Amount, Status (`SETTLED`, `REJECTED`), BalanceSnapshot.
  - Idempotency Store: Map of `IdempotencyKey -> { status, statusCode, responseBody, timestamp }`.
- **Concurrency Serialization & Mutex Mechanism:**
  - Account-level lock coordinator. When a transfer between Account A and Account B is requested:
    - Sort lock keys `[A, B].sort()` to eliminate deadlocks.
    - Acquire exclusive asynchronous lock for the account pair.
    - Validate invariant: `sender.balance >= amount`.
    - Mutate state atomically: `sender.balance -= amount`, `receiver.balance += amount`.
    - Record double-entry transaction record.
    - Cache idempotency response.
    - Release lock.
- **Invariant Audit Engine:**
  - Dynamic verification: $\sum_{i} \text{balance}_i = \text{Initial Supply}$.
  - Non-negativity constraint: $\forall i, \text{balance}_i \ge 0$.
  - Returns `invariantValid: true/false`, `totalDrift: 0`, `accountCount: 4`.

### 1.2 Frontend Architecture (`public/index.html`)
- Modern dark-mode Tailwind CSS aesthetic (Deep slate background `#0b0f19`, Card borders `#1e293b`, Accents Emerald `#10b981`, Indigo `#6366f1`, Rose `#f43f5e`).
- Real-time polling / event ticker updating every 1000ms.
- **Top Metrics Bar:**
  - Total Liquidity (Sum of balances).
  - Invariant Verification Status (`100% BALANCED - ZERO DRIFT`).
  - Settled Transaction Count.
  - Idempotency Cache Hits counter.
- **Accounts Grid:**
  - Visual cards for `ACC-OPERATING` ($50,000), `ACC-TREASURY` ($30,000), `ACC-ESCROW` ($15,000), and `ACC-PAYROLL` ($5,000).
- **Transfer Interaction Form:**
  - Source selector, Destination selector, Amount input.
  - Idempotency Key with auto-generation and "New UUID" button.
  - Optimistic UI updates with loading state and rollbacks on failure.
  - Toast alert notifications for settled transactions, overdraft rejections, and idempotent replays.
- **Audit Ledger Table:**
  - Reverse-chronological ledger table showing Tx ID, Timestamp, Debit/Credit parties, Amount formatted, Idempotency Key, Status badge, Invariant check pill.

### 1.3 Playwright QA Suite (`tests/ledger.spec.js`)
- Test 1: Dashboard initialization and invariant check validation.
- Test 2: Standard atomic transfer verification with UI update & ledger entry.
- Test 3: Overdraft prevention test (insufficient funds generates explicit error banner, balances remain unchanged).
- Test 4: Idempotency enforcement (resending same idempotency key gives cached response and increments cache hit metric without duplicate debit).
- Test 5: High-concurrency race condition resistance test: sends 20 simultaneous concurrent requests against a balance of $1,000 in increments of $100. Exactly 10 succeed, 10 fail with insufficient funds, final balance is $0, and total system liquidity remains strictly conserved.

---

## 2. Impacted Files Manifest
| File Path | Purpose |
|---|---|
| `experiments/tasks/EXP-006/package.json` | Project manifest with scripts (`start`, `test:e2e`), dependencies (`express`, `@playwright/test`). |
| `experiments/tasks/EXP-006/server.js` | Concurrency-safe double-entry ledger backend engine. |
| `experiments/tasks/EXP-006/public/index.html` | Real-time Tailwind CSS dark-mode dashboard with optimistic updates. |
| `experiments/tasks/EXP-006/tests/ledger.spec.js` | Comprehensive Playwright E2E verification test suite. |
| `tasks/TSK-015/03_exec.md` | Execution ledger tracking changes and symbol definitions. |
| `tasks/TSK-015/04_verify.md` | Verification report with test execution results. |

---

## 3. OKR Acceptance Matrix
| Objective | Key Result | Machine-Verifiable Exit Criteria |
|---|---|---|
| **O1: Double-Entry & Balance Invariants** | KR1.1: Zero-sum conservation<br>KR1.2: No overdrafts | `verifySystemInvariants().valid === true` && `sender.balance >= 0` across all transactions. |
| **O2: Concurrency & Idempotency** | KR2.1: Parallel safety under 20 concurrent requests<br>KR2.2: Idempotent replay deduplication | Exactly $1,000 drained from $1,000 without overdrawing, and duplicate key returns `idempotentReplay: true`. |
| **O3: Real-Time UI & Micro-interactions** | KR3.1: Live metrics, accounts, ledger table<br>KR3.2: Explicit error states & optimistic UI | Playwright asserts presence of live accounts, transfer form, table updates, and error toast alerts. |
| **O4: Automated QA** | KR4.1: 100% pass on Playwright test suite | `npx playwright test` exits with code 0. |

---

## 4. Exit Criteria & Authorization
- [x] Architecture specifications and lock mechanisms defined.
- [x] OKR matrix with machine-verifiable criteria established.
- [x] All 4 deliverables planned.
- [x] Authorized to transition to `03_exec.md`.
