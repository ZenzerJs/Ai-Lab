from schema import Event
from store import EventStore
from projector import replay


def test_v3_stream():
    store = EventStore()
    store.append("counter", [Event("increment", {"delta": 2, "metadata": {}})], 0)
    assert store.version("counter") == 1
    assert replay(store, "counter") == {"total": 2, "count": 1}
