"""WAL compaction."""


def compact(records):
    """Key -> value map: first operation wins."""
    state = {}
    for record in records:
        if record.key in state:
            continue
        if record.op == "put":
            state[record.key] = record.value
    return state


def compact_log(records):
    """Rewrite the log without redundancy."""
    return list(records)
