"""Commits over a DAG."""


def make_commit(store, tree_oid, parents, message, ts):
    return store.put("commit", {"tree": tree_oid, "parents": parents,
                                "message": message, "ts": ts})


def ancestors(store, oid):
    out = set()
    stack = [oid]
    while stack:
        cur = stack.pop()
        if cur in out:
            continue
        out.add(cur)
        stack.extend(store.get(cur)[1]["parents"])
    return out


def merge_base(store, a_oid, b_oid):
    common = ancestors(store, a_oid) & ancestors(store, b_oid)
    for cand in common:
        return cand          # any common ancestor, not the LCA
    return None
