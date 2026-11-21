"""Index API over the B+Tree."""
from btree import BTree
from pager import PageStore


class Index:
    def __init__(self, order=3):
        self.tree = BTree(order)
        self.store = PageStore()

    def put(self, key, value):
        self.tree.insert(key, value)

    def get(self, key):
        return self.tree.search(key)

    def remove(self, key):
        self.tree.delete(key)

    def scan(self, lo, hi):
        return self.tree.range_scan(lo, hi)

    def snapshot(self):
        return self.store.dump()

    def verify(self):
        return True
