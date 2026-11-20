"""
evaluator.py - Protected evaluator for BENCH-008.
Verifies multi-threaded atomic SQLite job claiming, single-transaction audit
commit/rollback, DLQ routing, expired lease reclamation, model invariants,
and seeded full-jitter backoff bounds.
"""
from pathlib import Path
import random
import sqlite3
import sys
import tempfile
import threading


def _fail(reason: str, detail: str) -> None:
    print(f"REASON: {reason}", file=sys.stderr)
    print(detail, file=sys.stderr)
    sys.exit(1)


def run_checks() -> None:
    try:
        from models import (
            InvalidTransitionError,
            Job,
            JobStatus,
            LeaseError,
            validate_transition,
        )
        from queue_store import QueueStore
        from retry import compute_backoff
        from worker import WorkerPool
    except Exception as exc:
        _fail("import_error", f"Failed to import BENCH-008 modules: {exc}")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # Check 1A: Deterministic 8-thread claim race over 10 jobs
        race_db = tmp / "race.db"
        store_race = QueueStore(race_db)
        expected_ids = {f"race-{i}" for i in range(10)}
        for i in range(10):
            store_race.enqueue(f"race-{i}", {"idx": i}, now=1000.0)

        barrier = threading.Barrier(8)
        claimed_ids = []
        claim_lock = threading.Lock()
        claim_errors = []

        def _racer(worker_idx: int) -> None:
            wid = f"racer-{worker_idx}"
            try:
                barrier.wait(timeout=5.0)
                while True:
                    job = store_race.claim_next_job(wid, lease_ttl=10.0, now=1000.0)
                    if job is None:
                        break
                    with claim_lock:
                        claimed_ids.append(job.job_id)
                    store_race.complete_job(job.job_id, wid, now=1001.0)
            except Exception as exc:
                with claim_lock:
                    claim_errors.append(exc)

        racers = [threading.Thread(target=_racer, args=(i,)) for i in range(8)]
        for t in racers:
            t.start()
        for t in racers:
            t.join(timeout=15.0)

        if claim_errors:
            _fail(
                "lease_race_or_partial_commit_leak",
                f"Concurrent claim race raised exception: {claim_errors[0]}",
            )
        if len(claimed_ids) != 10 or set(claimed_ids) != expected_ids:
            _fail(
                "lease_race_or_partial_commit_leak",
                f"Claim race detected! Expected 10 unique claims, got total={len(claimed_ids)}, unique={len(set(claimed_ids))}, claims={claimed_ids}",
            )

        # Check 1B: 8-thread WorkerPool over 10 jobs processes each strictly once
        pool_db = tmp / "pool_race.db"
        store_pool = QueueStore(pool_db)
        for i in range(10):
            store_pool.enqueue(f"pool-{i}", {"idx": i}, now=1000.0)

        exec_counts = {}
        exec_lock = threading.Lock()

        def _counting_handler(job: Job) -> None:
            with exec_lock:
                exec_counts[job.job_id] = exec_counts.get(job.job_id, 0) + 1

        pool_race = WorkerPool(
            store_pool,
            _counting_handler,
            num_workers=8,
            lease_ttl=10.0,
            backoff_base=0.0,
            backoff_cap=0.0,
            seed=7,
            now_fn=lambda: 1000.0,
        )
        summary = pool_race.run_until_empty()
        if (
            len(exec_counts) != 10
            or any(v != 1 for v in exec_counts.values())
            or summary["completed"] != 10
        ):
            _fail(
                "lease_race_or_partial_commit_leak",
                f"WorkerPool concurrency violation: counts={exec_counts}, summary={summary}",
            )

        # Check 2A: Store-level injected crash rolls back atomically (0 dirty audit rows)
        tx_db = tmp / "tx.db"
        store_tx = QueueStore(tx_db)
        store_tx.enqueue("tx-1", {"k": "v"}, max_attempts=3, now=100.0)
        claimed_tx = store_tx.claim_next_job("w1", lease_ttl=10.0, now=100.0)
        if claimed_tx is None:
            _fail("lease_race_or_partial_commit_leak", "Failed to claim tx-1")

        def _boom_hook() -> None:
            raise RuntimeError("injected_storage_crash")

        try:
            store_tx.complete_job("tx-1", "w1", now=101.0, pre_status_hook=_boom_hook)
            _fail(
                "lease_race_or_partial_commit_leak",
                "complete_job did not propagate pre_status_hook exception",
            )
        except RuntimeError:
            pass

        conn = sqlite3.connect(str(tx_db))
        try:
            dirty_completed = conn.execute(
                "SELECT COUNT(*) FROM job_audit_log WHERE job_id = 'tx-1' AND event_type = 'COMPLETED'"
            ).fetchone()[0]
            status_row = conn.execute(
                "SELECT status FROM jobs WHERE job_id = 'tx-1'"
            ).fetchone()
        finally:
            conn.close()

        if dirty_completed != 0 or not status_row or status_row[0] != "RUNNING":
            _fail(
                "lease_race_or_partial_commit_leak",
                f"Partial-commit leak after crash: dirty_completed={dirty_completed}, status={status_row}",
            )

        # Wrong lease owner must also reject and leave 0 COMPLETED rows
        try:
            store_tx.complete_job("tx-1", "impostor", now=101.0)
            _fail(
                "lease_race_or_partial_commit_leak",
                "complete_job allowed non-owner worker to complete job",
            )
        except LeaseError:
            pass
        except Exception:
            pass

        conn = sqlite3.connect(str(tx_db))
        try:
            dirty_impostor = conn.execute(
                "SELECT COUNT(*) FROM job_audit_log WHERE job_id = 'tx-1' AND event_type = 'COMPLETED'"
            ).fetchone()[0]
        finally:
            conn.close()
        if dirty_impostor != 0:
            _fail(
                "lease_race_or_partial_commit_leak",
                f"Partial-commit leak on wrong lease owner: dirty_completed={dirty_impostor}",
            )

        store_tx.complete_job("tx-1", "w1", now=102.0)

        # Check 2B: WorkerPool handler crash releases lease to PENDING, 0 dirty COMPLETED rows, then retries
        store_tx.enqueue("crash-retry", {"step": 1}, max_attempts=3, now=200.0)
        attempt_calls = {"n": 0}

        def _flaky_handler(job: Job) -> None:
            attempt_calls["n"] += 1
            if attempt_calls["n"] == 1:
                raise RuntimeError("transient_boom")

        flaky_pool = WorkerPool(
            store_tx,
            _flaky_handler,
            num_workers=1,
            lease_ttl=5.0,
            backoff_base=0.0,
            backoff_cap=0.0,
            seed=11,
            now_fn=lambda: 200.0,
        )
        flaky_pool.process_one("w-flaky")

        mid_job = store_tx.get_job("crash-retry")
        mid_logs = [e["event_type"] for e in store_tx.get_audit_log("crash-retry")]
        if (
            mid_job is None
            or mid_job.status != JobStatus.PENDING
            or mid_job.attempts != 1
            or getattr(mid_job, "lease_owner", "MISSING") is not None
            or getattr(mid_job, "lease_expires_at", "MISSING") is not None
            or "COMPLETED" in mid_logs
            or "RETRY_SCHEDULED" not in mid_logs
        ):
            _fail(
                "lease_race_or_partial_commit_leak",
                f"Handler crash did not cleanly roll back/release lease to PENDING: job={mid_job}, logs={mid_logs}",
            )

        flaky_pool.process_one("w-flaky")
        done_job = store_tx.get_job("crash-retry")
        if done_job is None or done_job.status != JobStatus.COMPLETED or done_job.attempts != 2:
            _fail(
                "lease_race_or_partial_commit_leak",
                f"Retried job did not complete on attempt 2: {done_job}",
            )

        # Check 2C: Exhausting max_attempts routes to DLQ with 0 COMPLETED audit rows
        store_tx.enqueue("crash-dlq", {"step": "fatal"}, max_attempts=2, now=300.0)

        def _always_fail(job: Job) -> None:
            raise RuntimeError("permanent_failure")

        dlq_pool = WorkerPool(
            store_tx,
            _always_fail,
            num_workers=2,
            lease_ttl=5.0,
            backoff_base=0.0,
            backoff_cap=0.0,
            seed=3,
            now_fn=lambda: 300.0,
        )
        dlq_pool.run_until_empty()

        dlq_job = store_tx.get_job("crash-dlq")
        dlq_logs = [e["event_type"] for e in store_tx.get_audit_log("crash-dlq")]
        if (
            dlq_job is None
            or dlq_job.status != JobStatus.DLQ
            or dlq_job.attempts != 2
            or dlq_job.lease_owner is not None
            or dlq_job.lease_expires_at is not None
            or "COMPLETED" in dlq_logs
            or "DEAD_LETTERED" not in dlq_logs
        ):
            _fail(
                "lease_race_or_partial_commit_leak",
                f"Job did not route cleanly to DLQ after max_attempts: job={dlq_job}, logs={dlq_logs}",
            )

        # Check 3: Expired lease reclamation (both retryable PENDING and exhausted DLQ)
        lease_db = tmp / "lease.db"
        store_lease = QueueStore(lease_db)
        store_lease.enqueue("lease-retry", {"ok": True}, max_attempts=3, now=500.0)
        c1 = store_lease.claim_next_job("dead-worker", lease_ttl=5.0, now=500.0)
        if c1 is None or c1.lease_owner != "dead-worker" or c1.lease_expires_at != 505.0:
            _fail(
                "lease_race_or_partial_commit_leak",
                f"Claimed job missing lease_owner/lease_expires_at: {c1}",
            )

        if store_lease.reclaim_expired_leases(now=504.0) != 0:
            _fail(
                "lease_race_or_partial_commit_leak",
                "Active non-expired lease was prematurely reclaimed at t=504.0",
            )
        if store_lease.claim_next_job("alive-worker", lease_ttl=5.0, now=504.0) is not None:
            _fail(
                "lease_race_or_partial_commit_leak",
                "Alive worker stole active non-expired lease at t=504.0",
            )

        reclaimed_cnt = store_lease.reclaim_expired_leases(now=506.0)
        reclaimed_job = store_lease.get_job("lease-retry")
        if (
            reclaimed_cnt != 1
            or reclaimed_job is None
            or reclaimed_job.status != JobStatus.PENDING
            or reclaimed_job.lease_owner is not None
            or reclaimed_job.lease_expires_at is not None
        ):
            _fail(
                "lease_race_or_partial_commit_leak",
                f"Expired lease not reclaimed to PENDING: count={reclaimed_cnt}, job={reclaimed_job}",
            )

        c2 = store_lease.claim_next_job("alive-worker", lease_ttl=5.0, now=506.0)
        if c2 is None or c2.lease_owner != "alive-worker" or c2.attempts != 2:
            _fail(
                "lease_race_or_partial_commit_leak",
                f"Alive worker failed to claim reclaimed job: {c2}",
            )
        store_lease.complete_job("lease-retry", "alive-worker", now=507.0)

        store_lease.enqueue("lease-dlq", {"ok": False}, max_attempts=1, now=600.0)
        store_lease.claim_next_job("dead-2", lease_ttl=5.0, now=600.0)
        store_lease.reclaim_expired_leases(now=606.0)
        exp_dlq = store_lease.get_job("lease-dlq")
        if exp_dlq is None or exp_dlq.status != JobStatus.DLQ:
            _fail(
                "lease_race_or_partial_commit_leak",
                f"Expired max_attempts job did not route to DLQ: {exp_dlq}",
            )

    # Check 4: Job model invariants and state transition validation
    bad_cases = [
        lambda: Job(job_id="b1", payload={}, attempts=-1),
        lambda: Job(job_id="b2", payload={}, max_attempts=0),
        lambda: Job(job_id="b3", payload={}, attempts=4, max_attempts=3),
        lambda: Job(job_id="b4", payload={}, status=JobStatus.RUNNING, lease_owner=None, lease_expires_at=None),
        lambda: Job(job_id="b5", payload={}, status=JobStatus.PENDING, lease_owner="w1", lease_expires_at=10.0),
    ]
    for idx, factory in enumerate(bad_cases):
        try:
            factory()
            _fail("invalid_model_or_transition", f"Job validation failed to reject invalid case #{idx}")
        except ValueError:
            pass

    for src, dst in [(JobStatus.COMPLETED, JobStatus.RUNNING), (JobStatus.DLQ, JobStatus.PENDING)]:
        try:
            validate_transition(src, dst)
            _fail("invalid_model_or_transition", f"Disallowed transition {src} -> {dst} was permitted")
        except (InvalidTransitionError, ValueError):
            pass

    # Check 5: Seeded full-jitter backoff validation & clamping
    try:
        compute_backoff(-1, 0.5, 5.0, random.Random(1))
        _fail("invalid_retry_backoff", "compute_backoff accepted negative attempt=-1")
    except ValueError:
        pass

    clamped = compute_backoff(10, 1.0, 5.0, random.Random(42))
    if not (0.0 <= clamped <= 5.0):
        _fail("invalid_retry_backoff", f"compute_backoff exceeded cap=5.0: {clamped}")

    d1 = compute_backoff(3, 0.5, 10.0, random.Random(99))
    d2 = compute_backoff(3, 0.5, 10.0, random.Random(99))
    if d1 != d2:
        _fail("invalid_retry_backoff", f"Seeded compute_backoff not deterministic: {d1} != {d2}")

    samples = {compute_backoff(3, 0.5, 10.0, random.Random(s)) for s in range(10)}
    if len(samples) < 5 or any(not (0.0 <= x <= 4.0) for x in samples):
        _fail("invalid_retry_backoff", f"compute_backoff lacked full-jitter variation or bounds: {samples}")

    print("ALL CHECKS PASSED")
    sys.exit(0)


if __name__ == "__main__":
    run_checks()
