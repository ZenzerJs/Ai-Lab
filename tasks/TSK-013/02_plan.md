# Task Stage Contract: 02_plan

## Task Metadata
- **Task ID:** TSK-013
- **Title:** Resilient HTTP Retry Transport
- **Status:** APPROVED
- **Prerequisite:** `01_intake.md` exit criteria satisfied

---

## 1. Technical Approach & Architecture

We will implement a clean, robust, and extensible HTTP retry transport in `src/retry_transport.py` that operates via standard library primitives (`urllib.request`, `http.client`, `typing`, `dataclasses`, `random`, `time`).

### Public Architecture & Interfaces

1. **`JitterStrategy` (Enum):**
   - `NONE`: Deterministic backoff (`base_delay * (backoff_factor ** attempt)`).
   - `FULL`: Full jitter (`random.uniform(0, min(max_delay, base_delay * (backoff_factor ** attempt)))`).
   - `EQUAL`: Equal jitter (`half = delay / 2; half + random.uniform(0, half)`).
   - `DECORRELATED`: Decorrelated jitter (`min(max_delay, random.uniform(base_delay, sleep * 3))`).

2. **`RetryConfig` (Dataclass):**
   - `max_retries: int = 3` (Maximum number of retry attempts; total calls = 1 + max_retries).
   - `base_delay: float = 0.5` (Initial backoff in seconds).
   - `max_delay: float = 30.0` (Maximum ceiling for backoff delay).
   - `backoff_factor: float = 2.0` (Exponential multiplier).
   - `jitter: JitterStrategy = JitterStrategy.FULL` (Jitter calculation method).
   - `retry_status_codes: Set[int] = {429, 500, 502, 503, 504}` (Configurable HTTP status codes that trigger a retry).
   - `retry_exceptions: Tuple[Type[Exception], ...] = (URLError, TimeoutError, ConnectionError, http.client.RemoteDisconnected)`
   - `respect_retry_after: bool = True` (Support parsing HTTP `Retry-After` header as integer seconds or HTTP-date).

3. **`RetryMetrics` / `RetryState` (Dataclass):**
   - `attempt: int` (Current retry attempt count).
   - `total_delay: float` (Cumulative delay slept across retries).
   - `delays: List[float]` (Individual delay intervals).
   - `history: List[Tuple[int, Optional[int], Optional[str]]]` (Log of attempts with status codes or exception messages).

4. **`HTTPResponse` / `RetryTransport` (Class):**
   - `HTTPResponse`: Normalized response object containing `status_code`, `headers`, `body`, `url`.
   - `RetryTransport`:
     - Initialized with `config: RetryConfig` and optional custom `sleeper: Callable[[float], None]` (to inject instant virtual sleep in tests).
     - Method `compute_delay(attempt: int, retry_after: Optional[float] = None) -> float`: Calculates backoff with full jitter and clamps to `max_delay`.
     - Method `is_retryable_status(status_code: int) -> bool`: Checks if code is in `retry_status_codes`.
     - Method `is_retryable_exception(exc: Exception) -> bool`: Checks if exception matches `retry_exceptions`.
     - Method `execute(request_fn: Callable[[], HTTPResponse]) -> HTTPResponse`: Executes the request function with retry loop, exponential backoff, jitter, retry-after handling, and state recording.
     - Method `send(request: Union[urllib.request.Request, str], **urlopen_kwargs) -> HTTPResponse`: High-level wrapper executing `urllib.request.urlopen` with retry protection.
     - Custom callback support `on_retry: Optional[Callable[[int, Exception or HTTPResponse, float], None]]`.

5. **`MaxRetriesExceededError` (Exception):**
   - Raised when `max_retries` is exceeded and the final outcome is an exception or status failure (if configured to raise).

### Cognitive Reasoning Trace (Sequential Thinking)
1. **Step 1 (Backoff & Full Jitter):**
   - For attempt $i \in [0, \text{max\_retries}-1]$:
     - Pure exponential delay: $D = \min(\text{max\_delay}, \text{base\_delay} \times \text{backoff\_factor}^i)$.
     - Full Jitter: sample uniformly from $[0, D]$.
   - If `Retry-After` is present in response headers (e.g. status 429 or 503), parse integer seconds or IMF-fixdate format, taking $\max(\text{retry\_after}, \text{jittered\_delay})$ up to `max_delay`.
2. **Step 2 (Transport Execution Flow):**
   - Loop `attempt` from 0 to `max_retries`:
     - Call `request_fn()`.
     - If response returned:
       - Check `is_retryable_status(response.status_code)`.
       - If not retryable or `attempt == max_retries`, return `response`.
       - Calculate delay (taking into account `Retry-After` header if enabled).
       - Record metrics and invoke `on_retry` callback if registered.
       - Sleep for calculated duration.
     - If exception raised:
       - Check `is_retryable_exception(exc)`.
       - If not retryable or `attempt == max_retries`, re-raise `exc` (or wrap in `MaxRetriesExceededError`).
       - Calculate delay, invoke callback, sleep, and continue.
3. **Step 3 (Mock Unit Tests Design):**
   - `MockSleeper`: Collects sleep durations without real-time wall-clock delays.
   - Test cases:
     - Immediate success on attempt 0 (no retries, no delay).
     - Transient failure then success (e.g., 503 -> 503 -> 200).
     - Full retry exhaustion for retryable HTTP status (e.g., 500 x 4 -> returns final 500 response or raises depending on config).
     - Non-retryable status code returns immediately without retrying (e.g., 400, 401, 404).
     - Retryable exceptions (e.g., `TimeoutError`, `URLError`, `ConnectionResetError`) retried up to limit.
     - Non-retryable exceptions (e.g., `ValueError`) raise immediately on first attempt.
     - Verification of exponential backoff bounds and full jitter uniform distribution properties.
     - Verification of `Retry-After` header parsing (both seconds and date format).
     - Custom status codes configuration (e.g., allow 418 or exclude 500).
     - Metrics tracking and `on_retry` observer callback verification.

---

## 2. Impacted Files Manifest

| Target File Path | Action (`CREATE` / `MODIFY` / `DELETE`) | Description & Rationale | Diff Block Required (>50 lines) |
|---|---|---|---|
| `src/retry_transport.py` | `CREATE` | Resilient HTTP retry transport implementation | No (Initial Creation) |
| `src/test_retry_transport.py` | `CREATE` | Comprehensive mock unit tests | No (Initial Creation) |
| `tasks/TSK-013/03_exec.md` | `CREATE` | Execution tracking ledger | No (Stage Contract) |
| `tasks/TSK-013/04_verify.md` | `CREATE` | Verification assertions and test results | No (Stage Contract) |

---

## 3. OKR Acceptance Matrix

| Objective ID | Key Result (KR) Description | Target Metric / Exit Criteria | Verification Method |
|---|---|---|---|
| **OKR-1** | Exponential Backoff & Full Jitter | Delays strictly obey $[0, \min(\text{max}, \text{base} \times \text{factor}^i)]$ bounds | `unittest` / `pytest` test suite |
| **OKR-2** | Status Code & Exception Filters | Configurable retry filters accurately differentiate retryable vs non-retryable | `unittest` / `pytest` test suite |
| **OKR-3** | Exhaustion & Header Handling | Correct retry termination, metrics ledger, and `Retry-After` parsing | `unittest` / `pytest` test suite |
| **OKR-4** | 100% Mock Testing Parity | Zero live network requests, sub-second test execution via virtual sleeper | `python scripts/filter_output.py` |
| **OKR-5** | Log Sanitation & Standards | Standard library only; filtered execution exit code 0 | `python scripts/filter_output.py` |

---

## 4. Exit Criteria & Transition Checklist
- [x] Technical design reviewed and verified against user requirements.
- [x] Impacted files manifest finalized.
- [x] OKR acceptance matrix established with deterministic criteria.
- [x] Transition to `03_exec.md` approved.
