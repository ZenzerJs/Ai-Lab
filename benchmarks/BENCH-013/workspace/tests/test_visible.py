from clock import Clock
from lock_store import LockStore
from coordinator import LockCoordinator


def test_acquire_release_smoke():
    store = LockStore(Clock(lambda: 0))
    record = store.acquire("r", "a", 10)
    assert record.fencing_token == 1
    store.release("r", "a", record.fencing_token)
    assert store.owner("r") is None


def test_hold_smoke():
    store = LockStore(Clock(lambda: 0))
    with LockCoordinator(store).hold("r", "a", 10) as record:
        assert store.owner("r") == "a"
    assert store.owner("r") is None
