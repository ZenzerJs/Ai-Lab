"""Repository: commits over trees with ref bookkeeping and merges."""
from commit import ancestors, make_commit, merge_base
from merge3 import merge_blobs
from objects import ObjectStore
from refs import RefStore
from tree import flatten, tree_diff, write_tree


class Repo:
    """Object store + refs + a monotone commit counter."""

    def __init__(self):
        self.store = ObjectStore()
        self.refs = RefStore()
        self.ts = 0

    def commit(self, files: dict, message: str) -> str:
        """Write the tree, then a commit on top of HEAD."""
        self.ts += 1
        parents = [self.refs.head_oid()] if self.refs.head_oid() else []
        oid = make_commit(self.store, write_tree(self.store, files),
                          parents, message, self.ts)
        self.refs.advance_head(oid)
        return oid

    def files_at(self, oid: str) -> dict:
        return flatten(self.store, self.store.get(oid)[1]["tree"])

    def merge(self, other_ref: str):
        """Merge another ref into HEAD.

        Returns (oid, conflicts): a merge commit when histories share a
        base, with per-file three-way blob merges. Conflicting files
        carry conflict hunks and are listed in conflicts.
        """
        head = self.refs.head_oid()
        other = self.refs.get(other_ref)
        base = merge_base(self.store, head, other)
        if base is None:
            raise ValueError("no merge base")
        base_f = self.files_at(base)
        our_f = self.files_at(head)
        their_f = self.files_at(other)
        merged, conflicts = {}, []
        for path in sorted(set(our_f) | set(their_f) | set(base_f)):
            b, o, t = base_f.get(path), our_f.get(path), \
                their_f.get(path)
            if o == t:
                if o is not None:
                    merged[path] = o
            elif o == b:
                if t is not None:
                    merged[path] = t
            elif t == b:
                if o is not None:
                    merged[path] = o
            else:
                text, cf = merge_blobs(b or "", o or "", t or "")
                merged[path] = text
                if cf:
                    conflicts.append(path)
        self.ts += 1
        oid = make_commit(self.store, write_tree(self.store, merged),
                          [head, other], "merge", self.ts)
        self.refs.advance_head(oid)
        return oid, conflicts
