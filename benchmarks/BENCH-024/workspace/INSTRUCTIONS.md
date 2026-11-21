# BENCH-024: Priority DAG Scheduler with Bounded Resources

Repair only models.py, graph.py, resources.py, ready.py, and
scheduler.py. Python stdlib only; no network, sleeps, or paid services.

## API and invariants

- models.Task(task_id, deps, priority, resources): validated — nonempty
  str id, int priority (not bool), tuple deps with no duplicates and no
  self-reference, resources as (name, positive int) pairs. States:
  pending/ready/done/failed/skipped. Errors: CycleError, DependencyError,
  ResourceCapacityError, DeadlockError.
- graph.DependencyGraph: add() rejects duplicates; validate() rejects
  unknown deps and cycles (CycleError names the cycle nodes);
  topo_order() is Kahn's algorithm over sorted ids.
- resources.ResourcePool(capacities): positive-int capacities;
  check() reports whether a demand can ever fit; try_acquire() is
  all-or-nothing (partial demands acquire NOTHING); release() pairs and
  over-release raises ResourceCapacityError.
- ready.ReadyQueue: pops by (priority desc, task_id asc).
- scheduler.Scheduler(graph, pool).run(handler): READY requires every
  dep DONE; pops ready tasks in order; handler exceptions mark the task
  FAILED and every transitive dependent SKIPPED; resources always
  released; a demand exceeding capacity or an unschedulable remainder
  raises DeadlockError; run() returns {task_id: TaskState}.

Visible tests are smoke coverage, not the complete specification.
