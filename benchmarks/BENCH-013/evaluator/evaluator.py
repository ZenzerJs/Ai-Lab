"""Protected deterministic checks for BENCH-013."""
import sys


class ManualClock:
    def __init__(self, value=0):
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
        from models import (LockConflictError, LockRecord, OwnershipError,
                            StaleTokenError)
        from clock import Clock
        from lock_store import LockStore
        from coordinator import LockCoordinator
    except Exception as exc:
        fail("import_error", exc)

    def model_checks():
        record = LockRecord("res", "alice", 1, 0, 5)
        assert (record.resource, record.owner, record.fencing_token,
                record.acquired_at, record.expires_at) == ("res", "alice", 1, 0, 5)
        bad = [("", "a", 1, 0, 5), ("r", "", 1, 0, 5), ("r", "a", 0, 0, 5),
               ("r", "a", -1, 0, 5), ("r", "a", True, 0, 5), ("r", "a", "1", 0, 5),
               ("r", "a", 1, -1, 5), ("r", "a", 1, 5, 5), ("r", "a", 1, 6, 5),
               ("r", "a", 1, 0.0, 5), ("r", "a", 1, 0, 5.0)]
        for values in bad:
            rejected(ValueError, lambda: LockRecord(*values))
        rejected(ValueError, lambda: LockRecord("r", "a", 1, 0, -1))
        assert issubclass(StaleTokenError, ValueError)
        assert issubclass(OwnershipError, PermissionError)

    def clock_checks():
        clock = Clock(lambda: 0)
        assert clock.now() == 0
        manual = ManualClock(7)
        clock = Clock(manual)
        assert clock.now() == 7
        manual.value = 8
        assert clock.now() == 8 and manual.calls == 2
        rejected(ValueError, lambda: Clock(lambda: 1.5).now())
        rejected(ValueError, lambda: Clock(lambda: True).now())

    def lifecycle_checks():
        manual = ManualClock(0)
        store = LockStore(Clock(manual))
        a = store.acquire("r", "alice", 10)
        assert (a.fencing_token, a.acquired_at, a.expires_at) == (1, 0, 10)
        assert store.owner("r") == "alice"
        rejected(LockConflictError, lambda: store.acquire("r", "alice", 10))
        rejected(LockConflictError, lambda: store.acquire("r", "bob", 10))
        for ttl in (0, -1, True, "10", 1.5):
            rejected(ValueError, lambda: store.acquire("x", "alice", ttl))
        manual.value = 10
        assert store.owner("r") is None
        rejected(KeyError, lambda: store.release("r", "alice", a.fencing_token))
        rejected(KeyError, lambda: store.renew("r", "alice", a.fencing_token, 5))
        b = store.acquire("r", "bob", 10)
        assert b.fencing_token == 2 and b.owner == "bob"
        rejected(KeyError, lambda: store.release("missing", "bob", 2))
        assert store.owner("missing") is None

    def fencing_checks():
        manual = ManualClock(0)
        store = LockStore(Clock(manual))
        a = store.acquire("a", "alice", 10)
        b = store.acquire("b", "alice", 10)
        assert (a.fencing_token, b.fencing_token) == (1, 2)
        store.release("a", "alice", 1)
        c = store.acquire("a", "alice", 10)
        assert c.fencing_token == 3
        rejected(OwnershipError, lambda: store.release("b", "mallory", 2))
        rejected(StaleTokenError, lambda: store.release("b", "alice", 1))
        rejected(StaleTokenError, lambda: store.release("b", "alice", 99))
        assert store.owner("b") == "alice"
        renewed = store.renew("b", "alice", 2, 40)
        assert renewed.fencing_token == 2 and renewed.expires_at == 40
        assert renewed.acquired_at == 0
        rejected(OwnershipError, lambda: store.renew("b", "mallory", 2, 40))
        rejected(StaleTokenError, lambda: store.renew("b", "alice", 1, 40))
        rejected(StaleTokenError, lambda: store.renew("b", "alice", 3, 40))
        manual.value = 41
        rejected(KeyError, lambda: store.renew("b", "alice", 2, 40))
        d = store.acquire("b", "carol", 5)
        assert d.fencing_token == 4
        rejected(StaleTokenError, lambda: store.release("b", "alice", 2))
        assert store.owner("b") == "carol"

    def coordinator_checks():
        manual = ManualClock(0)
        store = LockStore(Clock(manual))
        coordinator = LockCoordinator(store)
        with coordinator.hold("r", "alice", 10) as record:
            assert store.owner("r") == "alice"
            assert record.fencing_token == 1
        assert store.owner("r") is None
        with coordinator.hold("r", "alice", 10):
            try:
                with coordinator.hold("r", "bob", 10):
                    raise AssertionError("expected LockConflictError")
            except LockConflictError:
                pass
            assert store.owner("r") == "alice"
        def boom():
            with coordinator.hold("r", "alice", 10):
                raise RuntimeError("boom")
        rejected(RuntimeError, boom)
        assert store.owner("r") is None
        manual.value = 0
        coordinator2 = LockCoordinator(store)
        holder = coordinator2.hold("r", "alice", 5)
        record = holder.__enter__()
        manual.value = 6
        new_record = store.acquire("r", "bob", 10)
        try:
            holder.__exit__(None, None, None)
        except Exception as exc:
            raise AssertionError(f"stale hold raised {type(exc).__name__}")
        assert store.owner("r") == "bob"
        assert store._locks["r"].fencing_token == new_record.fencing_token
        store.release("r", "bob", new_record.fencing_token)

    for check in (model_checks, clock_checks, lifecycle_checks,
                  fencing_checks, coordinator_checks):
        try:
            check()
        except Exception as exc:
            fail("lease_invariant_violation",
                 f"{check.__name__}: {type(exc).__name__}: {exc}")
    print("ALL CHECKS PASSED")


def fail(reason, detail):
    print(f"REASON: {reason}", file=sys.stderr)
    print(detail, file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    run_checks()
