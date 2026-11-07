"""Test suite for EXP-009 Job Queue Engine."""
import concurrent.futures
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


def test_dag_multi_root_cycle_detection():
    resolver = DAGResolver()
    # Detached cyclic component alongside healthy component
    deps = {
        "ok_1": [],
        "ok_2": ["ok_1"],
        "loop_a": ["loop_b"],
        "loop_b": ["loop_a"],
    }
    assert resolver.has_cycle(deps) is True

    clean_deps = {
        "root_1": [],
        "root_2": [],
        "leaf": ["root_1", "root_2"],
    }
    assert resolver.has_cycle(clean_deps) is False


def test_worker_concurrent_leasing():
    store = QueueStore()
    store.enqueue(Job(id="shared_job", tenant_id="acme", payload={"task": "process"}))
    pool = WorkerPool(store, lease_seconds=60.0)

    # Launch 5 concurrent workers trying to lease the same ready job
    leased_jobs = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(pool.lease_job, "acme") for _ in range(5)]
        for f in concurrent.futures.as_completed(futures):
            res = f.result()
            if res is not None:
                leased_jobs.append(res)

    # Exactly one worker must successfully lease the job
    assert len(leased_jobs) == 1
    assert leased_jobs[0].id == "shared_job"
    assert leased_jobs[0].state == JobState.RUNNING


def test_retry_policy_dlq():
    policy = RetryPolicy(max_attempts=3)
    job = Job(id="j_fail", tenant_id="t1", payload={}, attempts=2, max_attempts=3)

    state = policy.evaluate_failure(job, "Network timeout")
    assert state == JobState.RETRYING

    job.attempts = 3
    state_dlq = policy.evaluate_failure(job, "Fatal DB constraint")
    assert state_dlq == JobState.DEAD_LETTER


def test_retry_jitter_prevents_thundering_herd():
    policy = RetryPolicy(base_seconds=2.0)
    delays = [policy.compute_delay(attempt=2, jitter=True) for _ in range(10)]
    # All delays should not be identical
    assert len(set(delays)) > 1
    # Without jitter, all delays should be identical
    fixed_delays = [policy.compute_delay(attempt=2, jitter=False) for _ in range(5)]
    assert len(set(fixed_delays)) == 1
