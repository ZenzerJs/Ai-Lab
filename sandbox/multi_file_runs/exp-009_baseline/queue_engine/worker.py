"""Concurrent Worker Pool & Leased Consumer."""
import threading
import time
from typing import Optional
from queue_engine.schema import Job, JobState
from queue_engine.storage import QueueStore


class WorkerPool:
    """Manages worker consumer loops and job leases."""

    def __init__(self, store: QueueStore, lease_seconds: float = 30.0) -> None:
        self.store = store
        self.lease_seconds = lease_seconds
        self._lock = threading.Lock()

    def lease_job(self, tenant_id: str) -> Optional[Job]:
        """Lease the next available job for a tenant atomically under lock."""
        with self._lock:
            now = time.time()
            for job in self.store.list_ready(tenant_id):
                if job.leased_until is None or job.leased_until < now:
                    job.state = JobState.RUNNING
                    job.leased_until = now + self.lease_seconds
                    job.attempts += 1
                    return job
            return None

    def heartbeat(self, job: Job, extend_seconds: Optional[float] = None) -> bool:
        """Extend lease for an active running job."""
        with self._lock:
            if job.state != JobState.RUNNING:
                return False
            now = time.time()
            delta = extend_seconds if extend_seconds is not None else self.lease_seconds
            job.leased_until = now + delta
            return True

    def complete_job(self, job: Job) -> None:
        """Mark job as successfully completed."""
        with self._lock:
            job.state = JobState.COMPLETED
            job.leased_until = None
