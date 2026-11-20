# BENCH-008: Concurrent Worker Lease, Retry Jitter & SQLite Rollback

## Assignment
Fix the concurrent lease race, SQLite partial-commit leak, retry/DLQ lifecycle, and backoff jitter bugs across four modules:
- `models.py` (`Job`, `JobStatus`, `InvalidTransitionError`, `LeaseError`, `validate_transition`)
- `retry.py` (`compute_backoff`)
- `queue_store.py` (`QueueStore`)
- `worker.py` (`WorkerPool`)

## Public Contract & Invariants

### 1. `models.py`
- `JobStatus(str, Enum)`: `PENDING`, `RUNNING`, `COMPLETED`, `DLQ`.
- `InvalidTransitionError(ValueError)` and `LeaseError(RuntimeError)`.
- `validate_transition(from_status: JobStatus, to_status: JobStatus) -> None`:
  Allowed transitions:
  - `PENDING -> {RUNNING, DLQ}`
  - `RUNNING -> {COMPLETED, PENDING, DLQ, RUNNING}` (where `RUNNING -> RUNNING` only occurs on expired-lease reclaim/re-claim)
  - `COMPLETED -> set()` (terminal)
  - `DLQ -> set()` (terminal)
  Raises `InvalidTransitionError` for disallowed transitions.
- `Job` dataclass fields:
  `job_id: str`, `payload: dict`, `status: JobStatus = JobStatus.PENDING`, `attempts: int = 0`, `max_attempts: int = 3`, `lease_owner: Optional[str] = None`, `lease_expires_at: Optional[float] = None`, `available_at: float = 0.0`, `last_error: Optional[str] = None`, `created_at: float = 0.0`, `updated_at: float = 0.0`.
  Validation in `__post_init__`:
  - `attempts >= 0`, `max_attempts >= 1`, `attempts <= max_attempts` (raise `ValueError` otherwise).
  - If `status == JobStatus.RUNNING`, `lease_owner` must be a non-empty string and `lease_expires_at` must be not `None`.
  - If `status in (PENDING, COMPLETED, DLQ)`, `lease_owner` and `lease_expires_at` must both be `None`.

### 2. `retry.py`
- `compute_backoff(attempt: int, base: float = 0.1, cap: float = 5.0, rng: Optional[random.Random] = None) -> float`:
  - Raises `ValueError` if `attempt < 0` (or boolean), `base < 0`, or `cap < 0`.
  - Computes full-jitter exponential backoff: `upper = min(cap, base * (2 ** attempt))` (safely handling large `attempt` without `OverflowError`), and returns `rng.uniform(0.0, upper)` (using a fresh `random.Random()` if `rng is None`).
  - Always satisfies `0.0 <= delay <= cap`. Deterministic for a seeded `rng`.

### 3. `queue_store.py` (`QueueStore`)
SQLite-backed store with tables `jobs` and `job_audit_log`:
- `QueueStore(db_path: Union[str, Path])`
- `enqueue(job_id: str, payload: dict, max_attempts: int = 3, available_at: float = 0.0, now: Optional[float] = None) -> Job`
- `claim_next_job(worker_id: str, lease_ttl: float = 5.0, now: Optional[float] = None) -> Optional[Job]`:
  Uses a single `BEGIN IMMEDIATE` transaction to atomically reclaim expired leases and claim at most one ready `PENDING` job (`available_at <= now` and `attempts < max_attempts`), incrementing `attempts`, setting `status = 'RUNNING'`, `lease_owner = worker_id`, `lease_expires_at = now + lease_ttl`, and inserting a `"CLAIMED"` row into `job_audit_log`. Two concurrent threads must NEVER claim the same job.
- `complete_job(job_id: str, worker_id: str, now: Optional[float] = None, pre_status_hook: Optional[Callable[[], None]] = None) -> Job`:
  Inside a single `BEGIN IMMEDIATE` transaction: verifies `status == 'RUNNING'` and `lease_owner == worker_id` (else raises `LeaseError`), executes `pre_status_hook()` if provided, updates `jobs` to `COMPLETED` clearing lease fields, and inserts a `"COMPLETED"` row into `job_audit_log`. Any error MUST roll back the entire transaction leaving 0 partial/dirty audit rows.
- `fail_job(job_id: str, worker_id: str, error_msg: str, backoff_seconds: float = 0.0, now: Optional[float] = None) -> Job`:
  Inside a single `BEGIN IMMEDIATE` transaction: verifies `status == 'RUNNING'` and `lease_owner == worker_id` (else raises `LeaseError`). If `attempts >= max_attempts`, transitions to `DLQ` and inserts `"DEAD_LETTERED"` audit row; otherwise transitions to `PENDING` with `available_at = now + backoff_seconds` and inserts `"RETRY_SCHEDULED"` audit row. Clears `lease_owner` and `lease_expires_at`. Rolls back completely on error.
- `reclaim_expired_leases(now: Optional[float] = None) -> int`:
  Atomically transitions `RUNNING` jobs with `lease_expires_at <= now` back to `PENDING` (recording `"LEASE_EXPIRED"`) if `attempts < max_attempts`, or to `DLQ` (recording `"DEAD_LETTERED"`) if `attempts >= max_attempts`. Returns reclaimed count.
- `get_job(job_id: str) -> Optional[Job]`, `list_jobs(status: Optional[Union[JobStatus, str]] = None) -> List[Job]`, `get_audit_log(job_id: Optional[str] = None) -> List[dict]`, `next_available_at() -> Optional[float]`.

### 4. `worker.py` (`WorkerPool`)
- `WorkerPool(store, handler, num_workers=4, lease_ttl=5.0, backoff_base=0.05, backoff_cap=2.0, seed=0, now_fn=None)`
- `process_one(worker_id: str = "worker-0") -> Optional[Job]`:
  Reclaims expired leases, claims one job, executes `handler(job)`, commits completion on success, or computes backoff via `compute_backoff` and calls `store.fail_job(...)` on exception (releasing the lease back to `PENDING` or routing to `DLQ` after `max_attempts`), writing 0 `"COMPLETED"` audit rows on failure.
- `run_until_empty(wait_for_retry: bool = True) -> dict`:
  Runs `num_workers` worker threads concurrently until no claimable/running jobs remain, returning status counts `{"completed": int, "dlq": int, "pending": int, "running": int}`.
