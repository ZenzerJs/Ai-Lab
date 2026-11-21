"""In-memory optimistic append-only streams and snapshots."""
from copy import deepcopy

from schema import ConflictError, Event


class EventStore:
    def __init__(self):
        self._streams = {}
        self._snapshots = {}

    def version(self, stream_id):
        return len(self._streams.get(stream_id, []))

    def append(self, stream_id, events, expected_version):
        current = self.version(stream_id)
        if type(expected_version) is not int or expected_version != current:
            raise ConflictError("expected version does not match")
        batch = [deepcopy(event) for event in events]
        for offset, event in enumerate(batch, 1):
            if not isinstance(event, Event):
                raise ValueError("expected Event")
            event.__post_init__()
            event.stream_version = current + offset
        if batch:
            self._streams.setdefault(stream_id, []).extend(batch)
        return deepcopy(batch)

    def read(self, stream_id, after_version=0):
        if type(after_version) is not int or after_version < 0:
            raise ValueError("invalid version")
        return deepcopy(self._streams.get(stream_id, [])[after_version:])

    def save_snapshot(self, stream_id, version, state):
        if type(version) is not int or not 0 <= version <= self.version(stream_id):
            raise ValueError("invalid snapshot version")
        self._snapshots[stream_id] = {"version": version, "state": deepcopy(state)}

    def get_snapshot(self, stream_id):
        return deepcopy(self._snapshots.get(stream_id))
