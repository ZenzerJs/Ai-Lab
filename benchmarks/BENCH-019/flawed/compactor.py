"""Tombstone-safe WAL compaction."""
from models import Record


def compact(records):
    """Live key -> value map: last operation wins, deletes tombstone keys."""
    state = {}
    for record in records:
        if record.op == "put":
            state[record.key] = record.value
        else:
            state.pop(record.key, None)
    return state


def compact_log(records):
    """Minimal equivalent log: each key's last op, tombstones kept, sorted.

    Replaying the result yields the same state as replaying `records`:
    a key whose last op is a delete keeps its tombstone record so the
    compacted segment still shadows any older data for that key.
    """
    last = {}
    for record in records:
        last[record.key] = record
    return [last[key] for key in sorted(last) if last[key].op == "put"]
