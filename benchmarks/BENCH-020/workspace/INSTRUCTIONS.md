# BENCH-020: Circuit Breaker, Bulkhead & Idempotent Retry Client

Repair only models.py, breaker.py, bulkhead.py, and client.py.
Python stdlib only; no network, sleeps, or paid services.

## API and invariants

- models.State enum: CLOSED / OPEN / HALF_OPEN with lowercase values.
- models.TransientError, CircuitOpen, BulkheadFull exceptions.
- models.RetryPolicy(max_attempts=3, base_delay=0.0, multiplier=1.0,
  retriable=(TransientError,)) is frozen and validated: max_attempts a
  positive int, base_delay >= 0, multiplier >= 1, retriable a nonempty
  tuple of exception classes — ValueError otherwise.
  policy.delay(i) = base_delay * multiplier**i (0-based).
- breaker.CircuitBreaker(failure_threshold=3, recovery_timeout=30.0,
  half_open_max_probes=1, clock=time.monotonic): validated; `clock` is an
  injected callable and ALL timing goes through it.
- Breaker semantics: `failure_threshold` consecutive failures open it
  (success resets the streak). While OPEN, allow() is False until clock
  time reaches recovery_timeout, then state becomes HALF_OPEN. Half-open
  admits at most half_open_max_probes probe calls (allow() consumes a
  probe slot); probe success closes and resets, probe failure RE-OPENS
  and restarts the recovery window.
- bulkhead.Bulkhead(limit): limit a positive int. acquire() takes a slot
  or returns False; release() pairs with acquire (ValueError at zero);
  in_flight counts live slots; run(fn) executes under a slot or raises
  BulkheadFull and ALWAYS releases.
- client.ResilientClient(breaker, bulkhead, policy=None,
  clock=time.monotonic): call(fn, idempotency_key=None) checks the
  breaker before every attempt (CircuitOpen when rejected) and stamps
  .attempted_at with the injected clock each attempt.
- Idempotent-only retry: retries happen only when idempotency_key is
  given; without a key exactly ONE attempt runs. Retries are limited to
  policy.retriable error classes and policy.max_attempts total tries;
  other errors propagate immediately. Each retry's delay is appended to
  .delays (computed, never slept). Successes and every failure are
  reported to the breaker via on_success/on_failure.

Visible tests are smoke coverage, not the complete specification.
