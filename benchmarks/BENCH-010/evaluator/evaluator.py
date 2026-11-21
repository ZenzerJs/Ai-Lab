"""Protected deterministic checks for BENCH-010."""
import sys


def rejected(error, callback):
    try:
        callback()
    except error as exc:
        return exc
    raise AssertionError(f"expected {error.__name__}")


def run_checks():
    try:
        from models import Task, CycleError
        from graph import Graph
        from scheduler import Scheduler
        from executor import Executor

        assert Graph([]).topological_order() == []
        assert Executor(Graph([]), {}).run() == {}
        deps = ["z"]
        task = Task("a", deps)
        deps.append("missing")
        assert task.dependencies == ("z",)
        rejected(ValueError, lambda: Task(""))
        rejected(ValueError, lambda: Graph([Task("a"), Task("a")]))
        rejected(ValueError, lambda: Graph([Task("a", ["missing"])]))

        # A newly ready node must outrank an older ready node.
        for names in (("a", "b", "z"), ("z", "b", "a")):
            graph = Graph([Task(name, ["z"] if name == "a" else []) for name in names])
            assert Scheduler(graph).plan() == ["b", "z", "a"]
        graph = Graph([Task("z"), Task("a", ["z", "z"]), Task("b")])
        assert graph.topological_order() == ["b", "z", "a"]
        graph = Graph([Task("b"), Task("a", ["b"]), Task("z")])
        assert graph.topological_order() == ["b", "a", "z"]

        for tasks in ([Task("a", ["b"]), Task("b", ["c"]), Task("c", ["a"]), Task("free")],
                      [Task("self", ["self"])]):
            graph = Graph(tasks)
            calls = []
            handlers = {name: lambda: calls.append("called") for name in graph.tasks}
            exc = rejected(CycleError, lambda: Executor(graph, handlers).run())
            cycle = exc.cycle
            assert len(cycle) >= 2 and cycle[0] == cycle[-1]
            assert all(dst in graph.tasks[src].dependencies for src, dst in zip(cycle, cycle[1:]))
            assert all(name in str(exc) for name in cycle)
            assert calls == []

        graph = Graph([Task("root"), Task("child", ["root"]),
                       Task("leaf", ["child"]), Task("join", ["leaf", "ok"]),
                       Task("ok"), Task("independent")])
        calls = []

        def fail():
            calls.append("root")
            raise RuntimeError("boom")

        def success(name):
            calls.append(name)
            return {"name": name}

        handlers = {name: lambda n=name: success(n) for name in graph.tasks}
        handlers["root"] = fail
        expected = {"root": "failed", "child": "skipped", "leaf": "skipped",
                    "join": "skipped", "ok": "succeeded", "independent": "succeeded"}
        executor = Executor(graph, handlers)
        assert executor.run() == expected
        assert set(calls) == {"root", "ok", "independent"} and len(calls) == 3
        assert graph.tasks["root"].error == "boom"
        for name in ("child", "leaf", "join"):
            assert graph.tasks[name].error == "upstream failure"
        assert graph.tasks["ok"].result == {"name": "ok"}
        saved = list(calls)
        assert executor.run() == expected
        assert Executor(graph, handlers).run() == expected
        assert calls == saved
        assert graph.tasks["ok"].result == {"name": "ok"}
    except Exception as exc:
        print("REASON: dag_invariant_violation", file=sys.stderr)
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    run_checks()
