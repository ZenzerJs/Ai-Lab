from graph import DependencyGraph
from models import Task, TaskState
from resources import ResourcePool
from scheduler import Scheduler


def test_schedules_smoke():
    g = DependencyGraph()
    g.add(Task("a"))
    g.add(Task("b", deps=("a",)))
    sched = Scheduler(g, ResourcePool({"cpu": 2}))
    states = sched.run(lambda t: None)
    assert all(s is TaskState.DONE for s in states.values())


def test_priority_order_smoke():
    g = DependencyGraph()
    g.add(Task("low", priority=0))
    g.add(Task("high", priority=9))
    sched = Scheduler(g, ResourcePool({"cpu": 1}))
    sched.run(lambda t: None)
    assert sched.order == ["high", "low"]
