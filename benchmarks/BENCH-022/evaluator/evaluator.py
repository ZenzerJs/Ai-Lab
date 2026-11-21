"""Protected deterministic checks for BENCH-022."""
import sys


def rejected(error, callback):
    try:
        callback()
    except error:
        return
    raise AssertionError(f"expected {error.__name__}")


def run_checks():
    try:
        from models import ConfigError, Decision, Quota, Rule
        from clock import ManualClock
        from windows import FixedWindow, SlidingLog
        from bucket import TokenBucket
        from limiter import RateLimiter
        from chain import RuleChain

        def model_checks():
            rejected(ConfigError, lambda: Quota("q", 0, 10.0))
            rejected(ConfigError, lambda: Quota("q", 1, 0.0))
            rejected(ConfigError, lambda: Quota("q", 1, 10.0, kind="bogus"))
            rejected(ConfigError, lambda: Quota("q", 1, 10.0, kind="bucket",
                                                refill_per_second=0))
            rejected(ConfigError, lambda: Rule("", "allow"))
            rejected(ConfigError, lambda: Rule("x", "bogus"))
            assert Quota("q", 2, 5.0).kind == "fixed"
            assert Decision("deny") is Decision.DENY
            assert Rule("*", "deny").matches("anything")
            assert Rule("api:*", "allow").matches("api:x")
            assert not Rule("api:*", "allow").matches("db:x")

        def window_checks():
            clock = ManualClock(0.0)
            fw = FixedWindow(10.0, clock)
            fw.add(); fw.add()
            assert fw.count() == 2
            clock.advance(9.999)
            assert fw.count() == 2            # still inside window
            clock.advance(0.001)
            assert fw.count() == 0            # boundary: new window
            fw.add()
            assert fw.count() == 1

            clock2 = ManualClock(100.0)
            sl = SlidingLog(10.0, clock2)
            for t in (90.0, 99.9, 100.0):
                sl._times.append(t)
            # (now-window, now]: 90.0 is exactly at the cutoff -> excluded.
            assert sl.count() == 2
            sl.add()
            assert sl.count() == 3
            clock2.advance(5.0)
            assert sl.count() == 3

        def bucket_checks():
            clock = ManualClock(0.0)
            bucket = TokenBucket(3, 1.0, clock)
            assert bucket.try_consume(2)
            assert bucket.try_consume(1)
            assert not bucket.try_consume(1)
            clock.advance(10.0)
            assert bucket.tokens == 3.0       # capped at capacity
            assert bucket.try_consume(3)
            rejected(ConfigError, lambda: bucket.try_consume(0))
            for args in ((0, 1.0), (-2, 1.0), (1.5, 1.0), (True, 1.0),
                         (3, 0.0), (3, -1.0)):
                rejected(ConfigError, lambda: TokenBucket(*args, clock))

        def limiter_checks():
            clock = ManualClock(0.0)
            quotas = [Quota("per-min", 2, 60.0, kind="fixed"),
                      Quota("burst", 4, 10.0, kind="sliding")]
            lim = RateLimiter(quotas, clock)
            assert lim.allow("alice") is Decision.ALLOW
            assert lim.allow("alice") is Decision.ALLOW
            assert lim.allow("alice") is Decision.DENY   # per-min exhausted
            assert lim.allow("bob") is Decision.ALLOW    # per-subject keying
            clock.advance(10.0)
            assert lim.allow("alice") is Decision.DENY   # still same fixed window
            clock.advance(50.0)
            assert lim.allow("alice") is Decision.ALLOW  # new fixed window
            assert lim.remaining("per-min", "alice") == 1
            rejected(KeyError, lambda: lim.remaining("nope", "alice"))
            # Denial is atomic: it consumes nothing on the other quota.
            clock2 = ManualClock(0.0)
            lim2 = RateLimiter(
                [Quota("tight", 1, 100.0, kind="fixed"),
                 Quota("loose", 5, 100.0, kind="fixed")], clock2)
            assert lim2.allow("s") is Decision.ALLOW
            assert lim2.allow("s") is Decision.DENY
            assert lim2.remaining("loose", "s") == 4     # nothing consumed
            rejected(ValueError, lambda: RateLimiter([], clock2))

        def chain_checks():
            chain = RuleChain([
                Rule("*", "allow"),
                Rule("api:*", "deny"),
            ])
            assert chain.decide("api:x") is Decision.DENY   # deny precedence
            assert chain.decide("web:y") is Decision.ALLOW
            chain2 = RuleChain([
                Rule("api:*", "deny"),
                Rule("api:health", "allow"),   # allow declared after deny still loses
                Rule("*", "allow"),
            ])
            assert chain2.decide("api:health") is Decision.DENY
            assert chain2.decide("db:z") is Decision.ALLOW
            default_deny = RuleChain([Rule("*", "allow")], default="deny")
            assert default_deny.decide("x") is Decision.ALLOW
            empty = RuleChain([], default=Decision.DENY)
            assert empty.decide("x") is Decision.DENY
            rejected(ValueError, lambda: RuleChain([], default="bogus"))
            decision, hits = chain.explain("api:x")
            assert decision is Decision.DENY and hits == ["*", "api:*"]

        for check in (model_checks, window_checks, bucket_checks,
                      limiter_checks, chain_checks):
            try:
                check()
            except Exception as exc:
                fail(f"{check.__name__}: {type(exc).__name__}: {exc}")
    except Exception as exc:
        fail(f"import_error: {exc}")
    print("ALL CHECKS PASSED")


def fail(detail):
    print("REASON: quota_invariant_violation", file=sys.stderr)
    print(detail, file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    run_checks()
