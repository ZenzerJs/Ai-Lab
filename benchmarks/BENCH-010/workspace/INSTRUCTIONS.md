# BENCH-010: DAG Scheduler & Failure Propagation

Repair models.py, graph.py, scheduler.py, executor.py using Python stdlib only.

## Public API
- models.Task(name, dependencies=()) holds name, a defensive tuple copy of dependency
  names, status="pending", result=None, error=None. Reject empty names with ValueError.
- models.CycleError(ValueError) exposes .cycle: a closed list of names (first ==
  last) following dependency edges; its message contains that path.
- graph.Graph(tasks) owns a name -> Task dictionary as .tasks. Reject duplicate
  names and unknown dependencies with ValueError. Duplicate dependency edges are
  treated as one edge.
- Graph.topological_order() returns names in topological order, always selecting
  the lexicographically smallest currently-ready node (not merely sorting a DFS).
  Cycles, including self-loops, raise CycleError with a concrete cycle path.
- scheduler.Scheduler(graph).plan() returns the validated topological order.
  should_skip(task) is true when any direct dependency is failed OR skipped.
- executor.Executor(graph, handlers).run() invokes each pending task's zero-argument
  handler once its dependencies have succeeded; records its result and "succeeded".
  Handler exceptions are caught, stored as str(exc) in error, status "failed".
  All descendants of failures become "skipped" with error "upstream failure".
  Unrelated branches still execute. Return a name -> status dict.
  Terminal tasks (succeeded, failed, skipped) must never execute again, even with
  a new Executor over the same Graph. Results/errors persist on reruns.
  Validate the entire graph before ANY handler invocation, so cycles cause no
  partial side effects. Empty graphs return [] from ordering and {} from run.

Visible tests are smoke coverage only. No network or external dependencies.
