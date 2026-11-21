"""Protected deterministic checks for BENCH-024."""
import sys


def rejected(error, callback):
    try:
        callback()
    except error:
        return
    raise AssertionError(f"expected {error.__name__}")


def run_checks():
    try:
        from models import (CycleError, DeadlockError, DependencyError,
                            ResourceCapacityError, Task, TaskState)
        from graph import DependencyGraph
        from ready import ReadyQueue
        from resources import ResourcePool
        from scheduler import Scheduler

        def model_checks():
            for kwargs in ({"task_id": ""}, {"task_id": "a", "priority": 1.5},
                           {"task_id": "a", "priority": True},
                           {"task_id": "a", "deps": ["x"]},
                           {"task_id": "a", "deps": ("x", "x")},
                           {"task_id": "a", "deps": ("a",)},
                           {"task_id": "a", "resources": (("db", 0),)},
                           {"task_id": "a", "resources": (("db", True),)},
                           {"task_id": "a", "resources": ("db",)}):
                rejected(ValueError, lambda: Task(**kwargs))
            t = Task("a", deps=("b",), priority=5, resources=(("cpu", 2),))
            assert t.task_id == "a"

        def graph_checks():
            g = DependencyGraph()
            g.add(Task("a"))
            rejected(DependencyError, lambda: g.add(Task("a")))
            g.add(Task("b", deps=("a",)))
            g.add(Task("c", deps=("a", "b")))
            g.validate()
            assert g.topo_order() == ["a", "b", "c"]
            g2 = DependencyGraph()
            g2.add(Task("x", deps=("y",)))
            g2.add(Task("y", deps=("z",)))
            g2.add(Task("z", deps=("x",)))
            cycle = None
            try:
                g2.validate()
            except CycleError as exc:
                cycle = str(exc)
            assert cycle is not None, "cycle not detected"
            assert "x" in cycle and "y" in cycle and "z" in cycle
            g3 = DependencyGraph()
            g3.add(Task("a", deps=("ghost",)))
            rejected(DependencyError, lambda: g3.validate())
            rejected(CycleError, lambda: g3.topo_order())

        def ready_checks():
            q = ReadyQueue()
            for t in (Task("b", priority=1), Task("a", priority=3),
                      Task("c", priority=3), Task("d", priority=0)):
                q.push(t)
            assert [q.pop().task_id for _ in range(4)] == ["a", "c", "b", "d"]

        def resource_checks():
            rejected(ResourceCapacityError, lambda: ResourcePool({}))
            rejected(ResourceCapacityError, lambda: ResourcePool({"cpu": 0}))
            rejected(ResourceCapacityError, lambda: ResourcePool({"cpu": True}))
            pool = ResourcePool({"cpu": 2, "mem": 1})
            assert pool.try_acquire((("cpu", 2), ("mem", 1)))
            assert not pool.try_acquire((("cpu", 1),))
            assert pool.in_use("cpu") == 2
            pool.release((("cpu", 2), ("mem", 1)))
            assert pool.in_use("cpu") == 0
            rejected(ResourceCapacityError,
                     lambda: pool.release((("cpu", 1),)))
            # Atomic: partial over-demand acquires nothing.
            pool2 = ResourcePool({"cpu": 2})
            assert not pool2.try_acquire((("cpu", 1), ("gpu", 1)))
            assert pool2.in_use("cpu") == 0
            assert not pool2.check((("cpu", 9),))

        def scheduler_checks():
            g = DependencyGraph()
            pool = ResourcePool({"cpu": 4})
            for t in (Task("low", priority=0), Task("hi1", priority=9),
                      Task("hi2", priority=9), Task("mid", deps=("hi1",),
                                                    priority=5)):
                g.add(t)
            sched = Scheduler(g, pool)
            states = sched.run(lambda t: None)
            assert sched.order == ["hi1", "hi2", "low", "mid"]
            assert all(s is TaskState.DONE for s in states.values())
            assert pool.in_use("cpu") == 0   # always released

            g2 = DependencyGraph()
            g2.add(Task("root"))
            g2.add(Task("child", deps=("root",)))
            g2.add(Task("grand", deps=("child",)))
            g2.add(Task("other"))
            sched2 = Scheduler(g2, ResourcePool({"cpu": 1}))

            def boom(task):
                if task.task_id == "root":
                    raise RuntimeError("boom")

            states2 = sched2.run(boom)
            assert states2["root"] is TaskState.FAILED
            assert states2["child"] is TaskState.SKIPPED
            assert states2["grand"] is TaskState.SKIPPED
            assert states2["other"] is TaskState.DONE
            assert isinstance(sched2.results["root"], RuntimeError)

        def deadlock_checks():
            g = DependencyGraph()
            g.add(Task("a", deps=("b",)))
            g.add(Task("b", deps=("a",)))
            rejected(CycleError,
                     lambda: Scheduler(g, ResourcePool({"cpu": 1})))
            g2 = DependencyGraph()
            g2.add(Task("big", resources=(("cpu", 8),)))
            rejected(DeadlockError,
                     lambda: Scheduler(g2, ResourcePool({"cpu": 2}))
                     .run(lambda t: None))

        for check in (model_checks, graph_checks, ready_checks,
                      resource_checks, scheduler_checks, deadlock_checks):
            try:
                check()
            except Exception as exc:
                fail(f"{check.__name__}: {type(exc).__name__}: {exc}")
    except Exception as exc:
        fail(f"import_error: {exc}")
    print("ALL CHECKS PASSED")


def fail(detail):
    print("REASON: scheduling_invariant_violation", file=sys.stderr)
    print(detail, file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    run_checks()
