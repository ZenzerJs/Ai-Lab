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
        """
        Lease the next available job for a tenant under atomic lock.
        Prevents race condition where duplicate workers acquire the same job.
        """
        with self._lock:
            for job in self.store.list_ready(tenant_id):
                now = time.time()
                if job.leased_until is None or job.leased_until < now:
                    job.state = JobState.RUNNING
                    job.leased_until = now + self.lease_seconds
                    job.attempts += 1
                    return job
            return None
