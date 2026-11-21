"""Protected deterministic checks for BENCH-011."""
from copy import deepcopy
import sys


def rejected(error, callback):
    try:
        callback()
    except error:
        return
    raise AssertionError(f"expected {error.__name__}")


def run_checks():
    try:
        from schema import Event, ConflictError
        from upcaster import upcast
        from store import EventStore
        from projector import apply, replay

        for version, payload in ((1, {"amount": 7}), (2, {"delta": 7}),
                                 (3, {"delta": 7, "metadata": {}})):
            original = Event("increment", dict(payload, extra={"tags": ["keep"]}), version, 8)
            saved = deepcopy(original)
            migrated = upcast(original)
            assert migrated.schema_version == 3 and migrated.stream_version == 8
            assert migrated.payload == {"delta": 7, "metadata": {}, "extra": {"tags": ["keep"]}}
            migrated.payload["extra"]["tags"].append("changed")
            assert original == saved
        for version in (0, 4, True):
            rejected(ValueError, lambda: Event("increment", {}, version))
        rejected(ValueError, lambda: Event("unknown", {}))
        rejected(ValueError, lambda: Event("increment", {}, stream_version=-1))
        for delta in (True, "2", None):
            rejected(ValueError, lambda: upcast(Event("increment", {"delta": delta, "metadata": {}})))
        rejected(ValueError, lambda: upcast(Event("increment", {"delta": 1, "metadata": []})))

        store = EventStore()
        assert store.version("absent") == 0 and store.read("absent") == []
        assert replay(store, "absent") == {"total": 0, "count": 0}
        assert store.get_snapshot("absent") is None
        assert store.append("empty", [], 0) == []
        first = Event("increment", {"amount": 3, "nested": {"tags": ["original"]}}, 1)
        returned = store.append("s", iter([first]), 0)
        assert first.stream_version == 0 and returned[0].stream_version == 1
        first.payload["nested"]["tags"].append("input mutation")
        returned[0].payload["nested"]["tags"].append("return mutation")
        read = store.read("s")
        read[0].payload["nested"]["tags"].append("read mutation")
        assert store.read("s")[0].payload == {"amount": 3, "nested": {"tags": ["original"]}}
        assert EventStore().read("s") == []
        store.append("other", [Event("increment", {"delta": 99, "metadata": {}})], 0)
        for expected in (0, 2, True, -1):
            before = store.read("s")
            rejected(ConflictError, lambda: store.append("s", [], expected))
            rejected(ConflictError, lambda: store.append("s", [first], expected))
            assert store.read("s") == before
        rejected(ValueError, lambda: store.append("s", [first, object()], 1))
        assert store.version("s") == 1
        store.append("s", [Event("increment", {"delta": -1}, 2),
                           Event("increment", {"delta": 5, "metadata": {}})], 1)
        assert [e.stream_version for e in store.read("s")] == [1, 2, 3]
        assert [e.stream_version for e in store.read("s", 1)] == [2, 3]
        assert store.read("s", 3) == store.read("s", 100) == []
        for invalid in (-1, True, "1"):
            rejected(ValueError, lambda: store.read("s", invalid))
        for invalid in (-1, 4, True):
            rejected(ValueError, lambda: store.save_snapshot("s", invalid, {}))

        state = {"total": 0, "count": 0}
        saved_event = store.read("s")[0]
        result = apply(state, saved_event)
        assert state == {"total": 0, "count": 0} and result == {"total": 3, "count": 1}
        assert saved_event.schema_version == 1
        full = replay(store, "s", use_snapshot=False)
        assert full == {"total": 7, "count": 3}
        for boundary in range(4):
            state = {"total": 0, "count": 0}
            for event in store.read("s")[:boundary]:
                state = apply(state, event)
            store.save_snapshot("s", boundary, state)
            state["total"] = 999
            snapshot = store.get_snapshot("s")
            snapshot["state"]["count"] = 999
            assert replay(store, "s") == full
            assert replay(store, "s", use_snapshot=False) == full
        store.save_snapshot("absent", 0, {"total": 0, "count": 0})
        assert replay(store, "absent") == {"total": 0, "count": 0}
        store.append("s", [Event("increment", {"delta": 10, "metadata": {}})], 3)
        assert replay(store, "s") == replay(store, "s", False) == {"total": 17, "count": 4}
    except Exception as exc:
        print("REASON: event_store_invariant_violation", file=sys.stderr)
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    run_checks()
