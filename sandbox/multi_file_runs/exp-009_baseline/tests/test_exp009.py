"""Test suite for EXP-009 Job Queue Engine."""
from concurrent.futures import ThreadPoolExecutor
import pytest
from queue_engine.dag import DAGResolver
from queue_engine.retry import RetryPolicy
from queue_engine.schema import Job, JobState
from queue_engine.storage import QueueStore
from queue_engine.worker import WorkerPool


def test_queue_storage_tenant_isolation():
    store = QueueStore()
    store.enqueue(Job(id="j1", tenant_id="tenant_a", payload={"action": "email"}))
    store.enqueue(Job(id="j2", tenant_id="tenant_b", payload={"action": "invoice"}))

    assert len(store.list_by_tenant("tenant_a")) == 1
    assert store.list_by_tenant("tenant_a")[0].id == "j1"
    assert len(store.list_by_tenant("tenant_b")) == 1


def test_dag_resolution_order():
    resolver = DAGResolver()
    deps = {
        "job_c": ["job_a", "job_b"],
        "job_b": ["job_a"],
        "job_a": [],
    }
    order = resolver.resolve_execution_order(deps)
    assert order.index("job_a") < order.index("job_b")
    assert order.index("job_b") < order.index("job_c")


def test_dag_cycle_detection_multi_root_detached():
    resolver = DAGResolver()
    deps = {
        "b": ["a"],
        "a": [],
        "c": ["d"],
        "d": ["c"],
    }
    assert resolver.has_cycle(deps) is True
    with pytest.raises(ValueError, match="Cycle detected"):
        resolver.resolve_execution_order(deps)


def test_worker_pool_atomic_leasing_concurrency():
    store = QueueStore()
    store.enqueue(Job(id="single_job", tenant_id="tenant_x", payload={"val": 42}))
    pool = WorkerPool(store=store, lease_seconds=10.0)

    def claim():
        return pool.lease_job("tenant_x")

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(lambda _: claim(), range(10)))

    leased = [j for j in results if j is not None]
    assert len(leased) == 1
    assert leased[0].id == "single_job"
    assert leased[0].attempts == 1


def test_retry_policy_dlq():
    policy = RetryPolicy(max_attempts=3)
    job = Job(id="j_fail", tenant_id="t1", payload={}, attempts=2, max_attempts=3)

    state = policy.evaluate_failure(job, "Network timeout")
    assert state == JobState.RETRYING

    job.attempts = 3
    state_dlq = policy.evaluate_failure(job, "Fatal DB constraint")
    assert state_dlq == JobState.DEAD_LETTER


def test_retry_policy_jitter():
    policy = RetryPolicy(max_attempts=5, base_seconds=2.0, jitter=True)
    delays = [policy.compute_delay(2) for _ in range(20)]
    assert all(2.0 <= d <= 6.0 for d in delays)
    assert len(set(delays)) > 1
