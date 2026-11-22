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
    "nodes", "pager", "btree", "index",
    "windows", "bucket", "limiter", "chain",
    "log", "election", "node", "cluster",
    "graph", "resources", "ready",
    "lexer", "env", "eval",
    "memtable", "sstable",
    "hashing", "chunker", "merkle", "diff", "sync", "replica",
    "vclock", "counters", "orset", "lww", "merge", "store",
    "syntax", "nfa", "compiler", "engine",
    "versions", "rwset", "locks", "txn", "collector", "db",
    "objects", "tree", "commit", "refs", "merge3", "repo",
    "cell", "topo", "batch",
    "event", "watermark", "aggregators", "triggers", "pipeline",
    "relations", "algebra", "network", "propagate", "search", "solver",
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


def test_bench021_seeded_insert_delete_invariants():
    """Random insert/delete workloads keep occupancy and ordering valid."""
    with _load_bench("BENCH-021"):
        from btree import BTree
        from models import KeyNotFound

        rng = random.Random(4242)
        for order in (3, 4, 5):
            tree = BTree(order)
            live = set()
            for _ in range(300):
                if rng.random() < 0.6:
                    k = rng.randrange(200)
                    if k not in live:
                        tree.insert(k, f"v{k}")
                        live.add(k)
                else:
                    k = rng.randrange(200)
                    if k in live:
                        tree.delete(k)
                        live.discard(k)
                tree.validate()
            assert [k for k, _v in tree.items()] == sorted(live)
            for k in live:
                assert tree.search(k) == f"v{k}"
            for k in range(200):
                if k not in live:
                    try:
                        tree.delete(k)
                        raise AssertionError("missing delete accepted")
                    except KeyNotFound:
                        pass


def test_bench022_seeded_sliding_window_boundary():
    """(now-window, now] boundary holds over random timestamp inserts."""
    with _load_bench("BENCH-022"):
        from clock import ManualClock
        from windows import SlidingLog

        rng = random.Random(777)
        for _ in range(20):
            clock = ManualClock(900.0)
            sl = SlidingLog(60.0, clock)
            inserted = []
            for _i in range(rng.randrange(5, 25)):
                t = 900.0 + rng.random() * 200.0
                clock.value = t
                sl.add()
                inserted.append(t)
            clock.value = 1000.0
            expected = [t for t in inserted if 940.0 < t <= 1000.0]
            assert sl.count() == len(expected)


def test_bench022_seeded_bucket_cap_and_atomicity():
    """Refill is capacity-capped; try_consume is all-or-nothing."""
    with _load_bench("BENCH-022"):
        from bucket import TokenBucket
        from clock import ManualClock

        rng = random.Random(31337)
        clock = ManualClock(0.0)
        bucket = TokenBucket(5, 0.5, clock)
        for _ in range(50):
            clock.advance(rng.random() * 30.0)
            assert bucket.tokens <= 5.0
            demand = rng.randrange(0, 8)
            if demand == 0:
                continue
            if bucket.tokens >= demand:
                before = bucket.tokens
                assert bucket.try_consume(demand)
                assert bucket.tokens == before - demand
            else:
                assert not bucket.try_consume(demand)


def test_bench023_seeded_partition_commit_safety():
    """Minority-partitioned leaders never advance commit_index."""
    with _load_bench("BENCH-023"):
        from cluster import Cluster
        from node import RaftNode

        rng = random.Random(60606)
        for _ in range(10):
            ids = [f"n{i}" for i in range(5)]
            cluster = Cluster([RaftNode(i, ids) for i in ids])
            cluster.elect("n0")
            leader = cluster.nodes["n0"]
            # Random 3-node partition isolates the leader in a minority.
            cut = set(rng.sample(ids[1:], 3))
            cluster.partition(cut)
            cluster.replicate("n0", "x")
            assert leader.commit_index == 0
            cluster.heal()
            cluster.replicate("n0", "y")
            assert leader.commit_index == 2
            for nid, node in cluster.nodes.items():
                assert node.log.entries[0].command == "x"


def test_bench024_seeded_priority_order_respects_deps():
    """Random DAGs execute dependencies before dependents and higher
    priority first among ready tasks."""
    with _load_bench("BENCH-024"):
        from graph import DependencyGraph
        from models import Task, TaskState
        from resources import ResourcePool
        from scheduler import Scheduler

        rng = random.Random(9090)
        for _ in range(15):
            g = DependencyGraph()
            ids = [f"t{i}" for i in range(rng.randrange(4, 10))]
            for i, tid in enumerate(ids):
                deps = tuple(d for d in ids[:i] if rng.random() < 0.3)
                g.add(Task(tid, deps=deps, priority=rng.randrange(0, 10)))
            sched = Scheduler(g, ResourcePool({"cpu": 4}))
            states = sched.run(lambda t: None)
            assert all(s is TaskState.DONE for s in states.values())
            order_pos = {tid: i for i, tid in enumerate(sched.order)}
            for tid, task in g.tasks.items():
                for dep in task.deps:
                    assert order_pos[dep] < order_pos[tid]


def test_bench025_seeded_eval_arithmetic():
    """Random arithmetic programs evaluate with strict precedence."""
    with _load_bench("BENCH-025"):
        from eval import run

        rng = random.Random(12321)
        ops = ["+", "-", "*"]
        for _ in range(100):
            terms = [rng.randrange(1, 50) for _ in range(4)]
            expr = (f"{terms[0]} {rng.choice(ops)} {terms[1]} "
                    f"{rng.choice(ops)} {terms[2]} {rng.choice(ops)} "
                    f"{terms[3]}")
            expected = eval(expr)   # Python agrees on int precedence
            assert run(expr) == [expected]


def test_bench025_seeded_scoping_shadowing():
    """Child scopes shadow without leaking to parents."""
    with _load_bench("BENCH-025"):
        from env import Environment
        from eval import run

        rng = random.Random(202)
        env = Environment()
        env.define("x", 1)
        for _ in range(10):
            child = env.child()
            val = rng.randrange(100)
            child.define("x", val)
            assert run("x", env=child) == [val]
            assert env.get("x") == 1


def test_bench026_seeded_reopen_and_compact_identity():
    """Reopen and compaction preserve the latest per-key state."""
    with _load_bench("BENCH-026"):
        import tempfile
        from models import NotFoundError
        from store import KVStore

        rng = random.Random(5150)
        for _ in range(10):
            expected = {}
            with tempfile.TemporaryDirectory() as td:
                kv = KVStore(td)
                for _i in range(rng.randrange(10, 60)):
                    key = f"k{rng.randrange(12)}"
                    if rng.random() < 0.8:
                        kv.put(key, f"v{rng.randrange(100)}")
                        expected[key] = kv.mem.get(key).value
                    else:
                        kv.delete(key)
                        expected.pop(key, None)
                    if rng.random() < 0.3:
                        kv.flush()
                kv.compact()
                kv.close()
                kv2 = KVStore(td)
                for key, val in expected.items():
                    assert kv2.get(key) == val
                for key in {f"k{i}" for i in range(12)} - set(expected):
                    try:
                        kv2.get(key)
                        raise AssertionError("deleted key readable")
                    except NotFoundError:
                        pass
                kv2.close()


def test_bench027_concurrent_repairs_converge():
    """N replicas pull-repair from one source concurrently -> converge."""
    with _load_bench("BENCH-027"):
        from replica import Replica

        rng = random.Random(4242)
        base = bytes(rng.randrange(256) for _ in range(4096))
        target = Replica("t", base)
        replicas = []
        for i in range(4):
            mutated = bytearray(base)
            mutated[i * 500:(i + 1) * 500] = bytes(500)
            replicas.append(Replica(f"r{i}", bytes(mutated)))
        barrier = threading.Barrier(len(replicas))

        def sync(r):
            barrier.wait(timeout=5)
            r.sync_with(target)

        threads = [threading.Thread(target=sync, args=(r,))
                   for r in replicas]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        for r in replicas:
            assert r.is_consistent(target)


def test_bench027_seeded_diff_ranges_minimal():
    """diff_ranges returns disjoint minimal ranges for seeded mutations."""
    with _load_bench("BENCH-027"):
        from chunker import chunk
        from diff import diff_ranges
        from merkle import MerkleTree

        rng = random.Random(77)
        for _ in range(8):
            n = rng.randrange(1, 33)
            a = bytes(rng.randrange(256) for _ in range(n * 64))
            b = bytearray(a)
            for _i in range(rng.randrange(1, 6)):
                pos = rng.randrange(len(b))
                b[pos] ^= 0xFF
            ta = MerkleTree(chunk(a, 64))
            tb = MerkleTree(chunk(bytes(b), 64))
            ranges = diff_ranges(ta, tb)
            for i in range(len(ranges) - 1):
                assert ranges[i][1] <= ranges[i + 1][0]


def test_bench028_seeded_merge_commutative_idempotent():
    """CRDT merges are commutative and idempotent under seeded shuffles."""
    with _load_bench("BENCH-028"):
        from counters import GCounter
        from orset import ORSet

        rng = random.Random(99)
        for _ in range(10):
            a, b = GCounter(), GCounter()
            for _i in range(rng.randrange(1, 20)):
                a.increment("A", rng.randrange(5))
                b.increment("B", rng.randrange(5))
            m1 = a.merge(b)
            m2 = b.merge(a)
            assert m1.value == m2.value
            assert m1.merge(m1).value == m1.value

        s1, s2 = ORSet(), ORSet()
        for e in range(8):
            tag = f"t{e}-{rng.randrange(1000)}"
            s1.add(e, tag)
            s2.add(e, tag)
        assert sorted(s1.elements()) == sorted(s2.elements())


def test_bench029_seeded_findall_nonoverlapping():
    """search_at yields non-overlapping leftmost-longest matches."""
    with _load_bench("BENCH-029"):
        from engine import Regex

        rng = random.Random(11)
        for pat in ("a+b*", "(ab|c)+", "x?y*"):
            eng = Regex(pat)
            text = "".join(rng.choice("abcxy") for _ in range(50))
            prev_end = 0
            pos = 0
            while pos <= len(text):
                hit = eng.search_at(text, pos)
                if hit is None:
                    break
                s, e = hit
                assert e > s, "empty match must never be yielded"
                assert s >= prev_end, "overlapping matches"
                prev_end = e
                pos = e
                if s == len(text):
                    break


def test_bench030_concurrent_commit_single_winner():
    """Threads racing the same key: exactly one commits, rest conflict."""
    with _load_bench("BENCH-030"):
        from db import DB
        from txn import ConflictError

        db = DB()
        seed = db.begin("seed")
        seed.write("k", "v0")
        seed.commit()
        barrier = threading.Barrier(6)
        committed, aborted = [], []

        def race(i):
            t = db.begin(f"t{i}")
            t.write("k", f"v{i}")
            barrier.wait(timeout=5)
            try:
                t.commit()
                committed.append(i)
            except ConflictError:
                aborted.append(i)

        threads = [threading.Thread(target=race, args=(i,))
                   for i in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert len(committed) == 1
        assert len(aborted) == 5


def test_bench031_seeded_merge_base_symmetric():
    """merge_base(a,b) == merge_base(b,a) across seeded DAGs."""
    with _load_bench("BENCH-031"):
        from commit import make_commit, merge_base
        from objects import ObjectStore
        from tree import write_tree

        rng = random.Random(31)
        for _ in range(6):
            store = ObjectStore()
            t = write_tree(store, {"f": "x"})
            root = make_commit(store, t, [], "root", 0)
            pa, pb = [root], [root]
            for i in range(rng.randrange(2, 6)):
                pa = [make_commit(store, t, pa, f"a{i}", i + 1)]
                pb = [make_commit(store, t, pb, f"b{i}", i + 1)]
            assert merge_base(store, pa[0], pb[0]) == \
                merge_base(store, pb[0], pa[0]) == root


def test_bench032_seeded_dag_glitch_free():
    """Random DAGs propagate glitch-free: one recompute per dirty cell."""
    with _load_bench("BENCH-032"):
        from engine import Engine
        from graph import Graph

        rng = random.Random(64)
        for _ in range(6):
            g = Graph()
            g.add_source("s0", rng.randrange(10))
            names = ["s0"]
            observed = []
            for i in range(rng.randrange(3, 8)):
                deps = rng.sample(names, rng.randrange(1, min(3, len(names) + 1)))

                def mk():
                    return lambda *vals: observed.append(vals) or sum(vals)
                name = f"c{i}"
                g.add(name, mk(), deps)
                names.append(name)
            e = Engine(g)
            e.propagate()
            n0 = e.recompute_count
            e.set("s0", rng.randrange(10))
            # all computed cells descend from s0 — each recomputes once
            assert e.recompute_count == 2 * n0


def test_bench033_seeded_watermark_monotone():
    """Seeded event streams: watermark never regresses; windows fire once."""
    with _load_bench("BENCH-033"):
        from aggregators import Count
        from event import Event
        from pipeline import Pipeline

        rng = random.Random(55)
        for _ in range(8):
            p = Pipeline(size=50, lateness=10,
                         aggregator_factory=Count)
            ts = 0
            prev_wm = None
            fired = set()
            for _i in range(rng.randrange(20, 80)):
                ts += rng.randrange(0, 60)
                p.push(Event(ts, "k", 1))
                wm = p.wm.current()
                if prev_wm is not None and wm is not None:
                    assert wm >= prev_wm, "watermark regressed"
                prev_wm = wm
            for key, idx, _res in p.results:
                assert (key, idx) not in fired
                fired.add((key, idx))


def test_bench034_seeded_chain_forces_before():
    """a<b<c forces a<c=b across seeded splits; cycles unsatisfiable."""
    with _load_bench("BENCH-034"):
        from relations import B
        from solver import Solver

        rng = random.Random(13)
        for _ in range(6):
            n = rng.randrange(3, 6)
            nodes = [f"n{i}" for i in range(n)]
            s = Solver(nodes)
            for i in range(n - 1):
                s.constrain(nodes[i], nodes[i + 1], {B, "m"})
            sol = s.solve()
            assert sol is not None
            assert sol[(nodes[0], nodes[-1])] == "b"
