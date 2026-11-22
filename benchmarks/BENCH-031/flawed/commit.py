"""Commits over a DAG: creation, ancestry and merge base."""
from objects import ObjectStore


def make_commit(store: ObjectStore, tree_oid: str, parents: list,
                message: str, ts: int) -> str:
    """Commit payload {tree, parents(sorted), message, ts} -> oid."""
    return store.put("commit", {"tree": tree_oid,
                                "parents": sorted(parents),
                                "message": message, "ts": ts})


def ancestors(store: ObjectStore, oid: str):
    """All ancestors of a commit oid, including itself."""
    out = set()
    stack = [oid]
    while stack:
        cur = stack.pop()
        if cur in out:
            continue
        out.add(cur)
        stack.extend(store.get(cur)[1]["parents"])
    return out


def merge_base(store: ObjectStore, a_oid: str, b_oid: str):
    """Lowest common ancestor of two commits (LCA).

    Among the common ancestors, the merge base is the one not an
    ancestor of any OTHER common ancestor — i.e. the deepest.
    Returns None for disjoint histories.
    """
    common = ancestors(store, a_oid) & ancestors(store, b_oid)
    for cand in common:
        if all(cand in ancestors(store, other)
               for other in common if other != cand):
            return cand
    return None
