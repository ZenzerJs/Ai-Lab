"""Protected deterministic checks for BENCH-009."""
from decimal import Decimal
import sys


class Clock:
    def __init__(self, value="0"):
        self.value = Decimal(value)
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
        from models import BucketState, as_decimal
        from bucket import TokenBucket
        from registry import BucketRegistry
        from middleware import RateLimiter
    except Exception as exc:
        fail("import_error", exc)

    def model_checks():
        assert as_decimal("0.1234567890123456789") == Decimal("0.1234567890123456789")
        assert as_decimal(0.1) == Decimal("0.1")
        state = BucketState(5, "0.1", 2, 0)
        assert all(isinstance(getattr(state, key), Decimal) for key in
                   ("capacity", "refill_rate", "tokens", "updated_at"))
        for value in (True, -1, "NaN", "Infinity", "bad"):
            rejected(ValueError, lambda: as_decimal(value))
        for values in ((0, 1, 0, 0), (2, 1, 3, 0), (2, -1, 1, 0), (2, 1, 1, -1)):
            rejected(ValueError, lambda: BucketState(*values))

    def clock_precision_checks():
        clock = Clock("10")
        bucket = TokenBucket(5, "0.1", clock)
        assert bucket.state.updated_at == Decimal(10)
        assert bucket.consume(5)
        clock.value = Decimal("11")
        bucket.refill()
        assert bucket.state.tokens == Decimal("0.1")
        assert bucket.state.updated_at == Decimal(11)
        clock.value = Decimal("9")
        bucket.refill()
        assert bucket.state.updated_at == Decimal(11)
        assert bucket.state.tokens == Decimal("0.1")
        assert not bucket.consume(1, now=11)
        for i in range(1, 10):
            bucket.refill(now=11 + i)
        assert bucket.state.tokens == Decimal(1)
        assert bucket.consume(1, now=20)
        assert bucket.state.tokens == 0
        bucket.refill(now=10000)
        assert bucket.state.tokens == 5
        before = (bucket.state.tokens, bucket.state.updated_at)
        for amount in (0, -1, True, "NaN", "Infinity"):
            rejected(ValueError, lambda: bucket.consume(amount, now=20000))
            assert (bucket.state.tokens, bucket.state.updated_at) == before
        precise = TokenBucket("1", "0.1", Clock())
        precise.consume(1, now=0)
        for i in range(1, 11):
            precise.refill(now=Decimal(i) / 10)
        assert isinstance(precise.state.tokens, Decimal)
        assert precise.state.tokens == Decimal("0.10")

    def isolation_checks():
        clock = Clock()
        registry = BucketRegistry(clock)
        a = registry.add("a", "api", 5, 0)
        b = registry.add("b", "api", 5, 0)
        other = registry.add("a", "other", 5, 0)
        assert a is not b and a is not other
        assert a.consume(5)
        assert b.state.tokens == other.state.tokens == 5
        rejected(ValueError, lambda: registry.add("a", "api", 100, 0))
        assert registry.get("a", "api") is a
        rejected(KeyError, lambda: registry.get("missing", "api"))
        fresh = BucketRegistry(clock)
        rejected(KeyError, lambda: fresh.get("a", "api"))
        assert fresh.add("a", "api", 2, 0).state.tokens == 2

    def atomic_checks():
        clock = Clock()
        registry = BucketRegistry(clock)
        a = registry.add("t", "a", 5, 1)
        b = registry.add("t", "b", 3, "0.1")
        alien = registry.add("other", "a", 5, 1)
        limiter = RateLimiter(registry)
        assert limiter.consume("t", [])
        assert limiter.consume("t", (pair for pair in [("a", 2), ("a", 3), ("b", 3)]))
        assert a.state.tokens == b.state.tokens == 0
        assert alien.state.tokens == 5
        clock.value = Decimal(1)
        before = [(x.state.tokens, x.state.updated_at) for x in (a, b)]
        assert not limiter.consume("t", [("a", 1), ("b", 1)])
        assert [(x.state.tokens, x.state.updated_at) for x in (a, b)] == before
        # A repeated-name overdraw must not be checked independently.
        assert not limiter.consume("t", [("a", "0.6"), ("a", "0.6")])
        assert [(x.state.tokens, x.state.updated_at) for x in (a, b)] == before
        for amount in (0, -1, True, "NaN", "Infinity"):
            rejected(ValueError, lambda: limiter.consume("t", [("a", 1), ("b", amount)]))
            assert [(x.state.tokens, x.state.updated_at) for x in (a, b)] == before
        rejected(KeyError, lambda: limiter.consume("t", [("a", 1), ("absent", 1)]))
        assert [(x.state.tokens, x.state.updated_at) for x in (a, b)] == before
        original = b.refill

        def broken_refill(now=None):
            original(now)
            raise RuntimeError("injected refill failure")

        b.refill = broken_refill
        rejected(RuntimeError, lambda: limiter.consume("t", [("a", 1), ("b", 1)]))
        assert [(x.state.tokens, x.state.updated_at) for x in (a, b)] == before
        b.refill = original
        clock.value = Decimal(10)
        calls = clock.calls
        assert limiter.consume("t", [("a", 2), ("b", 1)])
        assert clock.calls == calls + 1
        assert a.state.tokens == 3 and b.state.tokens == 0
        assert a.state.updated_at == b.state.updated_at == 10

    for check in (model_checks, clock_precision_checks, isolation_checks, atomic_checks):
        try:
            check()
        except Exception as exc:
            fail("token_bucket_invariant_violation", f"{check.__name__}: {type(exc).__name__}: {exc}")
    print("ALL CHECKS PASSED")


def fail(reason, detail):
    print(f"REASON: {reason}", file=sys.stderr)
    print(detail, file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    run_checks()
