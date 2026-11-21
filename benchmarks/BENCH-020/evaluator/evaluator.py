"""Protected deterministic checks for BENCH-020."""
import sys


class FakeClock:
    def __init__(self, value=1000.0):
        self.value = value
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return self.value


def rejected(error, callback):
    try:
        callback()
    except error:
        return
    raise AssertionError(f"expected {error.__name__}")


def run_checks():
    try:
        from models import (BulkheadFull, CircuitOpen, RetryPolicy, State,
                            TransientError)
        from breaker import CircuitBreaker
        from bulkhead import Bulkhead
        from client import ResilientClient

        def model_checks():
            policy = RetryPolicy(max_attempts=4, base_delay=2.0, multiplier=3.0)
            assert [policy.delay(i) for i in range(3)] == [2.0, 6.0, 18.0]
            assert RetryPolicy().retriable == (TransientError,)
            for kwargs in ({"max_attempts": 0}, {"max_attempts": True},
                           {"max_attempts": 1.5}, {"base_delay": -1},
                           {"multiplier": 0.5}, {"retriable": ()},
                           {"retriable": (int,)}, {"retriable": [TransientError]}):
                rejected(ValueError, lambda: RetryPolicy(**kwargs))
            assert State.CLOSED.value == "closed"
            assert State("half_open") is State.HALF_OPEN

        def breaker_checks():
            clock = FakeClock()
            breaker = CircuitBreaker(2, 10.0, clock=clock)
            assert breaker.state is State.CLOSED
            assert breaker.allow()
            breaker.on_success()
            breaker.on_failure()
            assert breaker.state is State.CLOSED  # below threshold
            breaker.on_failure()
            assert breaker.state is State.OPEN
            assert not breaker.allow()
            clock.value += 9.9
            assert not breaker.allow()              # timeout not elapsed
            assert breaker.state is State.OPEN
            clock.value += 0.1
            assert breaker.state is State.HALF_OPEN
            assert breaker.allow()                  # probe slot 1
            assert not breaker.allow()              # probes exhausted
            breaker.on_failure()
            assert breaker.state is State.OPEN      # probe failure re-opens
            assert not breaker.allow()
            clock.value += 10.0
            assert breaker.allow()
            breaker.on_success()
            assert breaker.state is State.CLOSED
            assert breaker.allow()
            # Failure streak resets on success.
            breaker.on_failure()
            breaker.on_success()
            breaker.on_failure()
            assert breaker.state is State.CLOSED
            breaker.on_failure()
            assert breaker.state is State.OPEN
            multi = CircuitBreaker(1, 5.0, half_open_max_probes=2, clock=clock)
            multi.on_failure()
            clock.value += 5.0
            assert multi.allow() and multi.allow()
            assert not multi.allow()
            for kwargs in ((0, 1.0), (-1, 1.0), (1, -0.5), (1, 1.0, 0),
                           (1, 1.0, 1, None)):
                rejected(ValueError, lambda: CircuitBreaker(*kwargs))

        def bulkhead_checks():
            bulk = Bulkhead(2)
            assert bulk.in_flight == 0
            assert bulk.acquire() and bulk.acquire()
            assert not bulk.acquire()
            assert bulk.in_flight == 2
            bulk.release()
            assert bulk.in_flight == 1
            bulk.release()
            rejected(ValueError, lambda: bulk.release())
            assert bulk.run(lambda: "ok") == "ok"
            assert bulk.in_flight == 0
            calls = []

            def nested():
                calls.append("inner")
                return bulk2.run(lambda: "deep")

            bulk2 = Bulkhead(1)
            rejected(BulkheadFull, lambda: bulk2.run(nested))
            # inner call consumed the only slot, then released.
            assert calls == ["inner"]
            assert bulk2.in_flight == 0
            for limit in (0, -1, 1.5, True):
                rejected(ValueError, lambda: Bulkhead(limit))

        def client_checks():
            clock = FakeClock()
            breaker = CircuitBreaker(4, 30.0, clock=clock)
            bulk = Bulkhead(1)
            client = ResilientClient(breaker, bulk,
                                     RetryPolicy(3, 1.0, 2.0), clock=clock)
            calls = []

            def flaky():
                calls.append(1)
                raise TransientError("blip")

            # Non-idempotent: exactly one attempt, error propagates.
            rejected(TransientError, lambda: client.call(flaky))
            assert calls == [1]
            assert client.delays == []
            # Idempotent: retries with recorded backoff, then raises.
            rejected(TransientError, lambda: client.call(flaky, idempotency_key="k"))
            assert calls == [1, 1, 1, 1]  # 1 non-idempotent + 3 retried
            assert client.delays == [1.0, 2.0]
            assert breaker.state is State.OPEN
            # Breaker open: rejected before fn runs.
            rejected(CircuitOpen, lambda: client.call(lambda: 1, "k"))
            clock.value += 30.0
            assert breaker.state is State.HALF_OPEN
            # Probe fails -> breaker re-opens -> next attempt gated.
            rejected(CircuitOpen, lambda: client.call(flaky, "k"))
            assert breaker.state is State.OPEN  # probe failure re-opens
            clock.value += 30.0
            # Probe succeeds -> breaker closes.
            assert client.call(lambda: "done", "k") == "done"
            assert breaker.state is State.CLOSED
            # Closed again: idempotent retry recovers.
            attempts = []

            def recovers():
                attempts.append(1)
                if len(attempts) < 2:
                    raise TransientError("once")
                return "done2"

            assert client.call(recovers, "k") == "done2"
            # Permanent errors never retry even with a key.
            breaker2 = CircuitBreaker(5, 30.0, clock=clock)
            client2 = ResilientClient(breaker2, Bulkhead(2), clock=clock)
            permanent = []

            def fails_permanently():
                permanent.append(1)
                raise ValueError("perm")

            rejected(ValueError, lambda: client2.call(fails_permanently, "k"))
            assert permanent == [1]
            # Non-retriable error class: no retry.
            typed = []

            def fails_typed():
                typed.append(1)
                raise RuntimeError("perm")

            rejected(RuntimeError, lambda: client2.call(fails_typed, "k"))
            assert typed == [1]
            # Success path returns value, attempts stamped by injected clock.
            ok = ResilientClient(CircuitBreaker(1, 1.0, clock=clock),
                                 Bulkhead(1), clock=clock)
            assert ok.call(lambda: 7, "id") == 7
            assert ok.attempted_at == [clock.value]
            saturated = Bulkhead(1)
            assert saturated.acquire()
            rejected(BulkheadFull, lambda: saturated.run(lambda: None))

        for check in (model_checks, breaker_checks, bulkhead_checks, client_checks):
            try:
                check()
            except Exception as exc:
                fail(f"{check.__name__}: {type(exc).__name__}: {exc}")
    except Exception as exc:
        fail(f"import_error: {exc}")
    print("ALL CHECKS PASSED")


def fail(detail):
    print("REASON: resilience_invariant_violation", file=sys.stderr)
    print(detail, file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    run_checks()
