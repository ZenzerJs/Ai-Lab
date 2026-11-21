from models import Task
from graph import Graph
from executor import Executor


def test_success_chain():
    graph = Graph([Task("a"), Task("b", ["a"])])
    calls = []
    result = Executor(graph, {name: lambda n=name: calls.append(n) for name in ("a", "b")}).run()
    assert result == {"a": "succeeded", "b": "succeeded"}
    assert calls == ["a", "b"]
