"""Index: stable put/get/remove/scan API over the B+Tree plus snapshot persistence."""
from btree import BTree
from nodes import InternalNode, LeafNode
from pager import PageStore


class Index:
    def __init__(self, order=3):
        self.tree = BTree(order)
        self.store = PageStore()

    def put(self, key, value):
        self.tree.insert(key, value)
        self._persist()

    def get(self, key):
        return self.tree.search(key)

    def remove(self, key):
        self.tree.delete(key)
        self._persist()

    def scan(self, lo, hi):
        return self.tree.range_scan(lo, hi)

    def _persist(self):
        self.store = PageStore()

        def walk(node):
            pid = self.store.allocate(node)
            if not node.is_leaf:
                for child in node.children:
                    walk(child)

        walk(self.tree.root)

    def snapshot(self):
        """Deterministic serialization of every node page."""
        return self.store.dump()

    def verify(self):
        return self.tree.validate()


def restore(snapshot, order=3):
    """Rebuild an Index whose leaf entries come from a snapshot's leaf pages."""
    index = Index(order)
    pages = snapshot
    leaves = [p for _pid, p in pages.items() if p["kind"] == "leaf"]
    for page in leaves:
        for k, v in zip(page["keys"], page["values"]):
            index.tree.insert(k, v)
    index._persist()
    return index
