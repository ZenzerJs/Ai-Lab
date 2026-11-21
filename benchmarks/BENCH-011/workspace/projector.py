"""Counter projection using full or snapshot-plus-tail replay."""
from copy import deepcopy

from upcaster import upcast


def apply(state, event):
    event = upcast(event)
    result = deepcopy(state)
    result["total"] += event.payload["delta"]
    result["count"] += 1
    return result


def replay(store, stream_id, use_snapshot=True):
    snapshot = store.get_snapshot(stream_id) if use_snapshot else None
    state = snapshot["state"] if snapshot else {"total": 0, "count": 0}
    version = snapshot["version"] if snapshot else 0
    for event in store.read(stream_id, after_version=0):
        state = apply(state, event)
    return state
