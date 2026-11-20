"""
worker.py - Broken WorkerPool for BENCH-008.
"""
import random
import threading
import time
from typing import Any, Callable, Dict, Optional

from models import Job, JobStatus
from queue_store import QueueStore


class WorkerPool:
    """
    BROKEN: Fails to release lease / fail_job / route to DLQ on handler crash,
    and ignores expired leases.
    """

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
        self.num_workers = num_workers
        self.lease_ttl = lease_ttl
        self.backoff_base = backoff_base
        self.backoff_cap = backoff_cap
        self.seed = seed
        self._now = now_fn if now_fn is not None else time.time

    def process_one(self, worker_id: str = "worker-0") -> Optional[Job]:
        """BROKEN: Swallows handler failure leaving job stuck in RUNNING."""
        job = self.store.claim_next_job(
            worker_id, lease_ttl=self.lease_ttl, now=self._now()
        )
        if job is None:
            return None
        try:
            self.handler(job)
            return self.store.complete_job(job.job_id, worker_id, now=self._now())
        except Exception:
            # BUG: does not call store.fail_job, release lease, or route to DLQ
            return self.store.get_job(job.job_id)

    def run_until_empty(self, wait_for_retry: bool = True) -> Dict[str, int]:
        """Spawn worker threads until no claimable jobs remain."""
        errors = []

        def _worker_loop(idx: int) -> None:
            wid = f"worker-{idx}"
            try:
                while True:
                    job = self.process_one(wid)
                    if job is None:
                        break
            except Exception as exc:
                errors.append(exc)

        threads = [
            threading.Thread(target=_worker_loop, args=(i,), daemon=True)
            for i in range(self.num_workers)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15.0)

        if errors:
            raise errors[0]

        return {
            "completed": len(self.store.list_jobs(JobStatus.COMPLETED)),
            "dlq": len(self.store.list_jobs(JobStatus.DLQ)),
            "pending": len(self.store.list_jobs(JobStatus.PENDING)),
            "running": len(self.store.list_jobs(JobStatus.RUNNING)),
        }
