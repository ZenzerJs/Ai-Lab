"""File trees as content-addressed nodes."""
from objects import ObjectStore


def write_tree(store, files):
    entries = sorted([p, store.put("blob", c)] for p, c in files.items())
    return store.put("tree", entries)


def flatten(store, tree_oid):
    kind, entries = store.get(tree_oid)
    if kind != "tree":
        raise TypeError(f"{tree_oid} is not a tree")
    return {p: store.get(b)[1] for p, b in entries}


def tree_diff(store, old_oid, new_oid):
    a, b = flatten(store, old_oid), flatten(store, new_oid)
    return sorted(set(a) ^ set(b))   # path names only
