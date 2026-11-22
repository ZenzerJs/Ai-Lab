"""File trees as nested content-addressed nodes."""
from objects import ObjectStore


def write_tree(store: ObjectStore, files: dict) -> str:
    """Store every blob, then a tree object mapping path -> blob oid.

    The tree payload is the sorted list of [path, blob_id] pairs so the
    tree id is content-defined and order-independent.
    """
    entries = sorted([p, store.put("blob", c)] for p, c in files.items())
    return store.put("tree", entries)


def flatten(store: ObjectStore, tree_oid: str) -> dict:
    """Reconstruct path -> content from a tree oid."""
    kind, entries = store.get(tree_oid)
    if kind != "tree":
        raise TypeError(f"{tree_oid} is not a tree")
    return {p: store.get(b)[1] for p, b in entries}


def tree_diff(store: ObjectStore, old_oid: str, new_oid: str) -> list:
    """Sorted paths whose CONTENT differs between two trees.

    Compares blob ids per path: renames without content change don't
    count as edits of surviving paths, and identical trees return [].
    """
    a, b = flatten(store, old_oid), flatten(store, new_oid)
    return sorted(p for p in set(a) | set(b) if a.get(p) != b.get(p))
