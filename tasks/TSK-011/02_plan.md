# Task Stage Contract: 02_plan

## Task Metadata
- **Task ID:** TSK-011
- **Title:** Sliding Window Rate Limiter Module
- **Status:** APPROVED
- **Prerequisite:** `01_intake.md` exit criteria satisfied

---

## 1. Technical Approach & Architecture
We will provide an in-memory sliding window rate limiter in `src/rate_limiter.py` adhering to the following design:

### Class Interface
- `class SlidingWindowRateLimiter`:
  - `__init__(self, limit: int, window_seconds: float, burst_allowance: int = 0) -> None`:
    - `limit`: Maximum allowed sustained requests per window (positive int).
    - `window_seconds`: Length of the sliding window in seconds (positive float).
    - `burst_allowance`: Extra requests permitted beyond `limit` during short bursts (non-negative int). Effective max capacity in window is `limit + burst_allowance`.
  - `allow_request(self, key: str = "default", cost: int = 1, timestamp: Optional[float] = None) -> bool`:
    - Atomically evaluates if `cost` requests can be admitted for `key`.
    - Returns `True` and records request if allowed; returns `False` if limit would be exceeded.
  - `acquire(self, key: str = "default", cost: int = 1, timeout: Optional[float] = None) -> bool`:
    - (Optional blocking/backoff helper or helper method, if convenient, or simple timeout loop).
  - `reset(self, key: Optional[str] = None) -> None`:
    - Resets history for a specific key or all keys.
  - `get_remaining_tokens(self, key: str = "default", timestamp: Optional[float] = None) -> int`:
    - Queries the remaining available request allowance within the active sliding window for the given key.

### Thread Safety & Concurrency
- Internal `threading.Lock` protecting the internal state dict: `_locks: Dict[str, threading.Lock]` or single coarse-grained `_lock: threading.Lock` (or reentrant lock `threading.RLock`) to ensure all check-and-record operations are atomic. A single `threading.Lock` provides complete safety and avoids lock contention deadlocks for in-memory operations.
- Key-level granularity: maintain `collections.deque[Tuple[float, int]]` (storing `(timestamp, cost)`) per `key`.
- In `allow_request`:
  1. Acquire lock.
  2. Expire all log entries where `entry_timestamp <= now - window_seconds`.
  3. Calculate current total cost in window.
  4. If `current_cost + cost <= limit + burst_allowance`:
     - Append `(now, cost)` to deque.
     - Return `True`.
  5. Else:
     - Return `False`.

### Cognitive Reasoning Trace (Sequential Thinking)
1. **Step 1 (Decomposition):** Sliding window rate limiting requires tracking timestamped events within `now - window_seconds`. A deque of `(timestamp, cost)` provides O(1) amortized eviction from the left.
2. **Step 2 (Burst Allowance Integration):** Burst allowance extends the effective capacity to `limit + burst_allowance` within the sliding window, permitting sudden spikes while maintaining bounded throughput over the window duration.
3. **Step 3 (Thread Safety Invariant):** All reads and writes to the deque for any key must be synchronized under a lock to prevent race conditions during concurrent `allow_request` calls.
4. **Step 4 (Test Architecture):** Build comprehensive tests in `src/test_rate_limiter.py` using `unittest`:
   - Basic rate limiting (allow up to limit, reject subsequent).
   - Sliding window progression / timestamp expiration (using mock timestamp or short sleep).
   - Burst allowance functionality (allowing limit + burst_allowance, rejecting above).
   - Multi-key isolation (requests on key A don't affect key B).
   - Concurrent thread safety (`ThreadPoolExecutor` or `threading.Thread` with barrier/latch verifying exact accepted vs rejected count).
   - Validation & edge cases (invalid params, zero cost, reset behavior, get_remaining_tokens).

---

## 2. Impacted Files Manifest

| Target File Path | Action (`CREATE` / `MODIFY` / `DELETE`) | Description & Rationale | Diff Block Required (>50 lines) |
|---|---|---|---|
| `src/rate_limiter.py` | `CREATE` | Net-new SlidingWindowRateLimiter implementation | No (new file) |
| `src/test_rate_limiter.py` | `CREATE` | Comprehensive unit tests including concurrency testing | No (new file) |
| `tasks/TSK-011/03_exec.md` | `CREATE` | Stage 3 execution tracking contract | No (new file) |
| `tasks/TSK-011/04_verify.md` | `CREATE` | Stage 4 verification report | No (new file) |

---

## 3. OKR Acceptance Matrix (Machine-Verifiable Exit Criteria)

**Objective:** Implement and verify a thread-safe in-memory sliding window rate limiter with burst allowance and full type annotations.

| Key Result (KR) | Deterministic Success Metric | Automated Verification Command (via `filter_output.py`) | Status |
|---|---|---|---|
| **KR 1** | Module imports cleanly with no syntax/import errors | `python scripts/filter_output.py -- python -c "from src.rate_limiter import SlidingWindowRateLimiter; assert callable(SlidingWindowRateLimiter)"` | APPROVED |
| **KR 2** | Full unit test suite passes with 100% success and exit code 0 | `python scripts/filter_output.py -- python -m unittest src/test_rate_limiter.py` | APPROVED |
| **KR 3** | Pytest execution succeeds cleanly across the workspace test runner | `python scripts/filter_output.py -- python -m pytest src/test_rate_limiter.py` | APPROVED |

---

## 4. Stage Gate Transition Check
Per `.agents/rules/okr-gate.md`, implementation in `03_exec.md` must not commence until:
- [x] Technical architecture reviewed and validated.
- [x] Impacted files manifest completely populated.
- [x] OKR Acceptance Matrix defined with automated verification commands.
- [x] Sign-off approved to transition to `03_exec.md`.
