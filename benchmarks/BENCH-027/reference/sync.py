"""Repair planning and application for anti-entropy sync."""
from diff import diff_ranges


def plan_repair(local, remote) -> list:
    """Ordered ('fetch', start, end) ops covering every differing range.

    `local` and `remote` are MerkleTrees; each op says which leaf
    positions to copy from the remote replica's chunks.
    """
    return [("fetch", s, e) for s, e in diff_ranges(local, remote)]


def apply_plan(local_chunks: list, remote_chunks: list, plan: list) -> list:
    """Return a new chunk list with each fetched range copied from remote.

    Op order is preserved; ranges never overlap because diff_ranges
    emits disjoint groups. Remote chunks outside the plan are ignored.
    """
    out = list(local_chunks)
    for _op, start, end in plan:
        out[start:end] = remote_chunks[start:end]
    return out
