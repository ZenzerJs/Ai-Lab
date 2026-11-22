"""Repository: commits over trees with refs and merges."""
from commit import ancestors, make_commit, merge_base
from merge3 import merge_blobs
from objects import ObjectStore
from refs import RefStore
from tree import flatten, tree_diff, write_tree


class Repo:
    def __init__(self):
        self.store = ObjectStore()
        self.refs = RefStore()
        self.ts = 0

    def commit(self, files, message):
        self.ts += 1
        parents = [self.refs.head_oid()] if self.refs.head_oid() else []
        oid = make_commit(self.store, write_tree(self.store, files),
                          parents, message, self.ts)
        self.refs.advance_head(oid)
        return oid

    def files_at(self, oid):
        return flatten(self.store, self.store.get(oid)[1]["tree"])

    def merge(self, other_ref):
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
            b = base_f.get(path, "")
            o = our_f.get(path)
            t = their_f.get(path)
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
                text, cf = merge_blobs(b, o or "", t or "")
                merged[path] = text
                conflicts.append(path)
        self.ts += 1
        oid = make_commit(self.store, write_tree(self.store, merged),
                          [head, other], "merge", self.ts)
        self.refs.advance_head(oid)
        return oid, conflicts
