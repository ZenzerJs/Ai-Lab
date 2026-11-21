"""
tests/unit/test_bench_hardening.py - Deterministic hardening checks for the
BENCH-009..020 multi-file suites.

Two kinds of checks, all offline and deterministic:

- Barrier-based concurrency tests (BENCH-013 lock manager, BENCH-020
  bulkhead): several threads released simultaneously by threading.Barrier
  race the shared primitive; assertions cover contention-safety invariants
  (exactly one winner, slot ceilings, monotonic fencing tokens) that a
  single-threaded evaluator cannot exercise.
- Seeded property tests (BENCH-011 event store, BENCH-017 cron scheduler,
  BENCH-018 FX ledger, BENCH-019 WAL/KV): random.Random(seed)-driven
  workloads assert algebraic invariants over the reference
  implementations (replay equivalence, OR-semantics, half-even rounding,
  corrupt-tail truncation, compaction identity).

Each benchmark ships same-named modules (models.py, wal.py, ...) that are
imported relative to its own directory, so every suite is imported inside
_load_bench(), which prepends the reference dir to sys.path and purges the
suite's module names from sys.modules on exit — no cross-suite leakage.
"""
from contextlib import contextmanager
from pathlib import Path
import random
import sys
import threading

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BENCH_DIR = REPO_ROOT / "benchmarks"

_MODULE_NAMES = {
    "models", "clock", "lock_store", "coordinator",
    "breaker", "bulkhead", "client",
    "schema", "upcaster", "store", "projector",
    "parser", "matcher", "scheduler",
    "rates", "ledger", "reconciler",
    "wal", "compactor", "kv_store",
}


@contextmanager
def _load_bench(task_id):
    """Import `task_id`'s reference modules in isolation, then purge them."""
    ref_dir = str(BENCH_DIR / task_id / "reference")
    saved = {name: sys.modules.pop(name, None) for name in _MODULE_NAMES}
    sys.path.insert(0, ref_dir)
    try:
        yield
    finally:
        sys.path.remove(ref_dir)
        for name in _MODULE_NAMES:
            current = sys.modules.get(name)
            if current is not None and getattr(
                    current, "__file__", "").startswith(ref_dir):
                del sys.modules[name]
            if saved[name] is not None:
                sys.modules[name] = saved[name]


# ---------------------------------------------------------------------------
# Barrier-based deterministic concurrency tests
# ---------------------------------------------------------------------------

def test_bench013_contended_acquire_single_winner():
    """N threads race one resource; exactly one acquires, others conflict."""
    with _load_bench("BENCH-013"):
        from clock import Clock
        from lock_store import LockStore
        from models import LockConflictError

        store = LockStore(Clock(lambda: 0))
        barrier = threading.Barrier(8)
        winners, conflicts = [], []

        def contend(owner):
            barrier.wait(timeout=5)
            try:
                winners.append(store.acquire("res", owner, 10))
            except LockConflictError:
                conflicts.append(owner)

        threads = [threading.Thread(target=contend, args=(f"w{i}",))
                   for i in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert len(winners) == 1
        assert len(conflicts) == 7
        assert store.owner("res") == winners[0].owner


def test_bench013_fencing_tokens_monotonic_under_race():
    """Sequential acquire/release cycles yield strictly increasing tokens."""
    with _load_bench("BENCH-013"):
        from clock import Clock
        from lock_store import LockStore

        store = LockStore(Clock(lambda: 0))
        barrier = threading.Barrier(4)
        tokens = []

        def grab(owner):
            barrier.wait(timeout=5)
            record = store.acquire(f"r-{owner}", owner, 10)
            tokens.append(record.fencing_token)

        threads = [threading.Thread(target=grab, args=(f"o{i}",))
                   for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert sorted(tokens) == [1, 2, 3, 4]


def test_bench020_bulkhead_never_exceeds_limit():
    """Racing acquires saturate at `limit`; losers get False, never more."""
    with _load_bench("BENCH-020"):
        from bulkhead import Bulkhead

        bulk = Bulkhead(3)
        barrier = threading.Barrier(8)
        acquired = []

        def contend():
            barrier.wait(timeout=5)
            if bulk.acquire():
                acquired.append(1)

        threads = [threading.Thread(target=contend) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert len(acquired) == 3
        assert bulk.in_flight == 3


def test_bench020_half_open_probe_gating_under_race():
    """At most half_open_max_probes threads pass allow() while half-open."""
    with _load_bench("BENCH-020"):
        from breaker import CircuitBreaker

        clock_value = [1000.0]

        def clock():
            return clock_value[0]

        breaker = CircuitBreaker(1, 30.0, half_open_max_probes=2,
                                 clock=clock)
        breaker.on_failure()          # -> OPEN
        clock_value[0] += 30.0        # recovery timeout elapsed -> HALF_OPEN

        barrier = threading.Barrier(6)
        allowed = []

        def probe():
            barrier.wait(timeout=5)
            if breaker.allow():
                allowed.append(1)

        threads = [threading.Thread(target=probe) for _ in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert len(allowed) == 2


# ---------------------------------------------------------------------------
# Seeded property tests
# ---------------------------------------------------------------------------

def test_bench011_seeded_replay_equivalence():
    """Snapshot+tail replay equals full replay over random event streams."""
    with _load_bench("BENCH-011"):
        from schema import Event
        from store import EventStore
        from projector import replay

        rng = random.Random(20261121)
        for _ in range(20):
            store = EventStore()
            stream = f"s{rng.randrange(4)}"
            version = 0
            batches = rng.randrange(1, 6)
            for _b in range(batches):
                n = rng.randrange(1, 5)
                events = [Event("increment",
                                {"delta": rng.randrange(1, 10),
                                 "metadata": {}},
                                schema_version=3)
                          for _e in range(n)]
                store.append(stream, events, expected_version=version)
                version += n
                if rng.random() < 0.5:
                    store.save_snapshot(stream, version,
                                        replay(store, stream,
                                               use_snapshot=False))
            assert replay(store, stream) == replay(
                store, stream, use_snapshot=False)


def test_bench011_seeded_chained_upcast():
    """Chained upcasting of random v1/v2 events lands at schema v3."""
    with _load_bench("BENCH-011"):
        from schema import Event
        from upcaster import upcast

        rng = random.Random(7)
        for _ in range(30):
            delta = rng.randrange(-100, 100)
            if rng.random() < 0.5:
                event = Event("increment", {"amount": delta},
                              schema_version=1)
            else:
                event = Event("increment", {"delta": delta},
                              schema_version=2)
            migrated = upcast(event)
            assert migrated.schema_version == 3
            assert migrated.payload["delta"] == delta
            assert isinstance(migrated.payload["metadata"], dict)


def test_bench017_seeded_cron_or_semantics():
    """Restricted dom+dow use OR; matches() agrees with parsed schedule."""
    with _load_bench("BENCH-017"):
        from datetime import datetime
        from matcher import cron_weekday, matches
        from parser import parse

        rng = random.Random(99)
        for _ in range(50):
            dom = rng.randrange(1, 29)
            dow = rng.randrange(0, 7)
            sched = parse(f"0 12 {dom} * {dow}")
            dt = datetime(2026, rng.randrange(1, 13),
                          rng.randrange(1, 29), 12, 0)
            expected = (dt.day == dom) or (cron_weekday(dt) == dow)
            assert matches(sched, dt) == expected


def test_bench017_seeded_next_runs_monotonic():
    """next_runs output is strictly increasing and each instant matches."""
    with _load_bench("BENCH-017"):
        from datetime import datetime, timezone
        from matcher import matches
        from parser import parse
        from scheduler import next_runs

        rng = random.Random(42)
        sched = parse("*/15 * * * *")
        after = datetime(2026, rng.randrange(1, 6),
                         rng.randrange(1, 28), 0, 0,
                         tzinfo=timezone.utc)
        runs = next_runs(sched, after, "UTC", 5)
        assert len(runs) == 5
        assert all(matches(sched, r.replace(tzinfo=None)) for r in runs)
        assert all(a < b for a, b in zip(runs, runs[1:]))
        assert all(r > after for r in runs)


def test_bench018_seeded_journal_balance():
    """Balanced random journals post; unbalanced are rejected."""
    with _load_bench("BENCH-018"):
        from decimal import Decimal
        from ledger import Ledger
        from models import Leg, Money

        rng = random.Random(31415)
        ledger = Ledger()
        for i in range(30):
            ccy = rng.choice(["USD", "EUR", "JPY"])
            amount = Decimal(rng.randrange(1, 10000)) / 100
            legs = (Leg("cash", Money(amount, ccy)),
                    Leg("rev", Money(-amount, ccy)))
            ledger.post(f"e{i}", legs)
        assert len(ledger.entries()) == 30

        bad = Ledger()
        for i in range(10):
            amount = Decimal(rng.randrange(1, 100))
            try:
                bad.post(f"x{i}", (Leg("a", Money(amount, "USD")),
                                   Leg("b", Money(0, "USD"))))
                raise AssertionError("unbalanced entry posted")
            except ValueError:
                pass


def test_bench018_seeded_half_even_quantize():
    """quantize() rounds half-even, including the float-trap case 2.675."""
    with _load_bench("BENCH-018"):
        from decimal import ROUND_HALF_EVEN, Decimal
        from models import quantize

        rng = random.Random(2718)
        for _ in range(200):
            cents = rng.randrange(0, 100000)
            half = rng.choice([0, 5])
            value = Decimal(cents) / 1000 + Decimal(half) / 1000
            rounded = quantize(str(value))
            # half-even: ties resolve to the even cent
            assert rounded == value.quantize(
                Decimal("0.01"), rounding=ROUND_HALF_EVEN)
        assert quantize("0.125") == Decimal("0.12")
        assert quantize("0.135") == Decimal("0.14")
        assert quantize("2.675") == Decimal("2.68")
        assert quantize("0.115") == Decimal("0.12")
        assert quantize("0.105") == Decimal("0.10")


def test_bench019_seeded_wal_roundtrip_and_truncate():
    """encode/scan round-trips random records; corrupt tails truncate."""
    with _load_bench("BENCH-019"):
        import tempfile
        from models import Record, encode, scan
        import wal

        rng = random.Random(1337)
        for _ in range(15):
            n = rng.randrange(1, 12)
            records = [Record("put", f"k{rng.randrange(50)}",
                              bytes([rng.randrange(256)])
                              * rng.randrange(0, 8))
                       for _i in range(n)]
            data = b"".join(encode(r) for r in records)
            assert [r for r, _e in scan(data)] == records
            # Corrupt the tail at a random cut; replay keeps the prefix.
            cut = rng.randrange(1, len(data))
            truncated = data[:cut]
            kept = [r for r, _e in scan(truncated)]
            assert kept == records[:len(kept)]

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "log.wal"
            for r in records:
                wal.append(path, r)
            path.write_bytes(path.read_bytes() + b"\xffbroken")
            assert wal.replay(path) == records


def test_bench019_seeded_compaction_identity():
    """compact(compact_log(x)) == compact(x) over random op streams."""
    with _load_bench("BENCH-019"):
        from compactor import compact, compact_log
        from models import Record

        rng = random.Random(555)
        for _ in range(25):
            records = []
            for _i in range(rng.randrange(1, 20)):
                if rng.random() < 0.7:
                    records.append(Record(
                        "put", f"k{rng.randrange(10)}",
                        bytes([rng.randrange(256)])
                        * rng.randrange(1, 8)))
                else:
                    records.append(Record("delete", f"k{rng.randrange(10)}"))
            assert compact(compact_log(records)) == compact(records)
            assert [r.key for r in compact_log(records)] == sorted(
                {r.key for r in records})
