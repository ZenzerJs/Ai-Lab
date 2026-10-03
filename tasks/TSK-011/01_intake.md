# Task Stage Contract: 01_intake

## Task Metadata
- **Task ID:** TSK-011
- **Title:** Sliding Window Rate Limiter Module
- **Status:** APPROVED
- **Date Created:** 2026-10-03
- **Owner:** Lead Software Architect / Agent
- **Task Contract Ref:** ICM Pipeline

---

## 1. Problem Statement & Objectives
The workspace requires an in-memory sliding window rate limiter implementation in `src/rate_limiter.py` with corresponding unit tests in `src/test_rate_limiter.py`.

Key Requirements:
1. Pure Python implementation with zero external third-party dependencies (using standard library: `threading`, `time`, `collections`, `typing`).
2. Sliding window log or sliding window counter algorithm tracking request timestamps within a configured window (e.g. per second, minute, etc.).
3. Burst allowance capability (e.g. allowing up to `burst_limit` or `burst_capacity` requests beyond or as maximum ceiling above the sustained window limit).
4. Concurrent thread safety using mutual exclusion locks (`threading.Lock` or `threading.RLock`) ensuring data integrity under multithreaded access.
5. Unit test suite covering rate limiting behavior, sliding window expiration, burst allowance, concurrent access via multiple threads, and edge cases.
6. Comprehensive static type annotations across all classes, methods, and functions.

---

## 2. Scope Boundaries
The following components are within the boundary of this task:
- `src/rate_limiter.py`: In-memory sliding window rate limiter with burst allowance and thread safety.
- `src/test_rate_limiter.py`: Comprehensive test suite using `unittest` verifying functionality and thread concurrency.
- `tasks/TSK-011/`: ICM stage contracts (`01_intake.md`, `02_plan.md`, `03_exec.md`, `04_verify.md`).

---

## 3. Out-of-Scope Declarations
The following areas are explicitly excluded from this task:
- Introducing any third-party dependencies (e.g., redis, limits, flask-limiter).
- Distributed rate limiting across network sockets or external storage backends.
- Modifying workspace orchestration or experiment harness scripts (`scripts/run_experiment.py`, `dashboard/`).

---

## 4. Technical Constraints & Invariants
- **Platform Invariant:** Execution parity across Windows (PowerShell) and POSIX (bash/zsh).
- **Rule Adherence:** Compliance with all operational directives in `.agents/rules/`.
- **Tool Discipline:** Git write/commit tools are strictly barred during intake and planning stages.
- **Dependency Invariant:** Python Standard Library only (`time`, `threading`, `collections`, `typing`).
- **Log Sanitation:** All test and validation commands executed through `scripts/filter_output.py`.

---

## 5. Per-Stage Token Budget Allocation Table
To guarantee that active turn context remains strictly under the **8,000 token limit**, prompt slices adhere to the bounded budget:

| Slice Component | Allocated Token Budget | Target Description / Pruning Control |
|---|---|---|
| **System Persona & Rules** | 1,500 tokens | Fixed directives from `AGENTS.md` and `.agents/rules/` |
| **Tool Definitions (MCP/CLI)** | 1,200 tokens | Compact JSON-RPC tool definitions |
| **OKF Knowledge Base Slice** | 1,500 tokens | Excerpts from `docs/` |
| **Active Task Contract** | 2,000 tokens | Current stage contract markdown (`tasks/TSK-011/*.md`) |
| **Volatile User Prompt & Margin** | 1,800 tokens | Immediate user inputs, safety headroom |
| **Total Active Turn Context** | **8,000 tokens** | **Hard Maximum Ceiling** |

---

## 6. Exit Criteria & Stage Transition Checklist
- [x] Problem statement validated against user request
- [x] In-scope and out-of-scope boundaries unambiguously defined
- [x] Token budget verified and approved
- [x] Transition sign-off to `02_plan.md` granted
