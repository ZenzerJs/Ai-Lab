"""Multi-Tenant Queue Storage Backend."""
from typing import Dict, List, Optional
from queue_engine.schema import Job, JobState


class QueueStore:
    """In-memory multi-tenant job storage with isolation guarantees."""

    def __init__(self) -> None:
        self._jobs: Dict[str, Job] = {}

    def enqueue(self, job: Job) -> str:
        self._jobs[job.id] = job
        return job.id

    def get(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    def list_by_tenant(self, tenant_id: str) -> List[Job]:
        return [j for j in self._jobs.values() if j.tenant_id == tenant_id]

    def list_ready(self, tenant_id: str) -> List[Job]:
        return [
            j for j in self._jobs.values()
            if j.tenant_id == tenant_id and j.state in (JobState.PENDING, JobState.RETRYING)
        ]
