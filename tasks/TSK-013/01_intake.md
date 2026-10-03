# Task Stage Contract: 01_intake

## Task Metadata
- **Task ID:** TSK-013
- **Title:** Resilient HTTP Retry Transport
- **Status:** APPROVED
- **Date Created:** 2026-10-03
- **Owner:** Lead Software Architect / Agent
- **Task Contract Ref:** ICM Pipeline

---

## 1. Problem Statement & Objectives
The workspace requires a resilient HTTP retry transport implementation in `src/retry_transport.py` and comprehensive unit test coverage in `src/test_retry_transport.py`.

Key Requirements:
1. **Exponential Backoff:** Configurable base backoff delay and multiplier/exponent, with configurable max backoff delay ceiling.
2. **Full Jitter:** Support AWS/Decorrelated full jitter algorithm (`uniform(0, min(max_delay, base_delay * (multiplier ** attempt)))`) to prevent thundering herd problems.
3. **Configurable Status Code Filters:** Configurable set/list of retryable HTTP status codes (defaults to transient errors: 429, 500, 502, 503, 504) and retryable exceptions (e.g. connection error, timeout).
4. **Resilient HTTP Retry Transport:** Clean, modular transport architecture supporting requests/urllib/callable abstractions, maximum retry attempts, backoff calculation, retry metrics/state tracking, and retry decision callbacks.
5. **Mock Unit Tests:** Comprehensive mock test suite in `src/test_retry_transport.py` validating backoff formula, jitter distribution boundaries, retry exhaustion, status code filtering, exception handling, custom retry conditions, and telemetry with 100% mock execution (zero live network requests).

---

## 2. Scope Boundaries
The following components are within the boundary of this task:
- `src/retry_transport.py`: Core retry policy, jitter calculations, backoff strategies, and retry transport handler/wrapper.
- `src/test_retry_transport.py`: Mock unit test suite exercising all retry scenarios and edge cases.
- `tasks/TSK-013/`: ICM stage contracts (`01_intake.md`, `02_plan.md`, `03_exec.md`, `04_verify.md`).

---

## 3. Out-of-Scope Declarations
The following areas are explicitly excluded from this task:
- External network requests or live third-party API dependencies during test runs.
- Heavy external dependencies beyond Python standard library (urllib, http.client, dataclasses, typing, random, time).
- Modifications to existing unrelated workspace modules (`rate_limiter.py`, `dead_code_finder.py`, `slugify.py`).

---

## 4. Technical Constraints & Invariants
- **Platform Invariant:** Cross-platform execution parity across Windows (PowerShell) and POSIX (bash/zsh).
- **Rule Adherence:** Compliance with all operational directives in `.agents/rules/`.
- **Tool Discipline:** Git write/commit tools are strictly barred during intake and planning stages.
- **Dependency Invariant:** Python Standard Library (`urllib`, `dataclasses`, `typing`, `random`, `time`, `unittest`).
- **Log Sanitation:** All test and validation commands executed through `scripts/filter_output.py`.

---

## 5. Per-Stage Token Budget Allocation Table

| Slice Component | Allocated Token Budget | Target Description / Pruning Control |
|---|---|---|
| **System Persona & Rules** | 1,500 tokens | Fixed directives from `AGENTS.md` and `.agents/rules/` |
| **Tool Definitions (MCP/CLI)** | 1,200 tokens | Compact JSON-RPC tool definitions |
| **OKF Knowledge Base Slice** | 1,500 tokens | Excerpts from `docs/` |
| **Active Task Contract** | 2,000 tokens | Current stage contract markdown (`tasks/TSK-013/*.md`) |
| **Volatile User Prompt & Margin** | 1,800 tokens | Immediate user inputs, safety headroom |
| **Total Active Turn Context** | **8,000 tokens** | **Hard Maximum Ceiling** |

---

## 6. Exit Criteria & Stage Transition Checklist
- [x] Problem statement validated against user request.
- [x] In-scope and out-of-scope boundaries unambiguously defined.
- [x] Token budget verified and approved.
- [x] Transition sign-off to `02_plan.md` granted.
