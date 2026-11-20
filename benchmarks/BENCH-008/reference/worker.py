"""
worker.py - Reference WorkerPool with lease release, retry backoff, and DLQ handling.
"""
import random
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from models import Job, JobStatus
from queue_store import QueueStore
from retry import compute_backoff


class WorkerPool:
    """Concurrent worker pool with atomic lease claiming, rollback/retry, and DLQ routing."""

    def __init__(
        self,
        store: QueueStore,
        handler: Callable[[Job], Any],
        num_workers: int = 4,
        lease_ttl: float = 5.0,
        backoff_base: float = 0.05,
        backoff_cap: float = 2.0,
        seed: int = 0,
        now_fn: Optional[Callable[[], float]] = None,
    ) -> None:
        self.store = store
        self.handler = handler
        self.num_workers = max(1, int(num_workers))
        self.lease_ttl = float(lease_ttl)
        self.backoff_base = float(backoff_base)
        self.backoff_cap = float(backoff_cap)
        self.seed = int(seed)
        self._uses_wall_clock = now_fn is None
        self._now = now_fn if now_fn is not None else time.time

    def process_one(
        self,
        worker_id: str = "worker-0",
        rng: Optional[random.Random] = None,
    ) -> Optional[Job]:
        """Reclaim expired leases, claim a ready job, and commit completion or failure rollback."""
        now = self._now()
        self.store.reclaim_expired_leases(now=now)
        job = self.store.claim_next_job(
            worker_id, lease_ttl=self.lease_ttl, now=now
        )
        if job is None:
            return None

        local_rng = rng if rng is not None else random.Random(self.seed)
        try:
            self.handler(job)
            return self.store.complete_job(job.job_id, worker_id, now=self._now())
        except Exception as exc:
            attempt_idx = max(0, job.attempts - 1)
            delay = compute_backoff(
                attempt=attempt_idx,
                base=self.backoff_base,
                cap=self.backoff_cap,
                rng=local_rng,
            )
            return self.store.fail_job(
                job.job_id,
                worker_id,
                error_msg=str(exc),
                backoff_seconds=delay,
                now=self._now(),
            )

    def run_until_empty(self, wait_for_retry: bool = True) -> Dict[str, int]:
        """Run worker threads concurrently until no claimable or retryable jobs remain."""
        errors: List[Exception] = []

        def _worker_loop(idx: int) -> None:
            wid = f"worker-{idx}"
            worker_rng = random.Random(self.seed + idx)
            try:
                while True:
                    job = self.process_one(wid, rng=worker_rng)
                    if job is not None:
                        continue
                    next_avail = self.store.next_available_at()
                    if next_avail is None or not wait_for_retry:
                        break
                    remaining = next_avail - self._now()
                    if remaining <= 0:
                        continue
                    if not self._uses_wall_clock:
                        break
                    time.sleep(min(0.02, remaining))
            except Exception as exc:
                errors.append(exc)

        threads = [
            threading.Thread(target=_worker_loop, args=(i,), daemon=True)
            for i in range(self.num_workers)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=20.0)

        if errors:
            raise errors[0]

        return {
            "completed": len(self.store.list_jobs(JobStatus.COMPLETED)),
            "dlq": len(self.store.list_jobs(JobStatus.DLQ)),
            "pending": len(self.store.list_jobs(JobStatus.PENDING)),
            "running": len(self.store.list_jobs(JobStatus.RUNNING)),
        }
