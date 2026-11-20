"""
test_visible.py - Accessible smoke tests for BENCH-008.
"""
from models import JobStatus
from queue_store import QueueStore
from worker import WorkerPool


def test_single_job_completes(tmp_path):
    """Verify basic enqueue and single-worker completion flow."""
    store = QueueStore(tmp_path / "queue.db")
    store.enqueue("job-1", {"action": "sync"})
    seen = []

    def handler(job):
        seen.append(job.job_id)

    pool = WorkerPool(store, handler, num_workers=1)
    pool.run_until_empty()

    job = store.get_job("job-1")
    assert job is not None
    assert job.status == JobStatus.COMPLETED
    assert job.attempts == 1
    assert seen == ["job-1"]
