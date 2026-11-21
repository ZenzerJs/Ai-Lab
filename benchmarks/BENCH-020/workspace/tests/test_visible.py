from bulkhead import Bulkhead
from client import ResilientClient
from breaker import CircuitBreaker


def test_success_smoke():
    client = ResilientClient(CircuitBreaker(), Bulkhead(2))
    assert client.call(lambda: "ok") == "ok"


def test_retry_smoke():
    calls = []

    def once():
        calls.append(1)
        if len(calls) == 1:
            raise TransientError("x")
        return "done"

    from models import TransientError
    client = ResilientClient(CircuitBreaker(), Bulkhead(1),
                             clock=lambda: 0.0)
    assert client.call(once, idempotency_key="k") == "done"
    assert len(calls) == 2
