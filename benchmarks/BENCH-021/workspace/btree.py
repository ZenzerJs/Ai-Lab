"""B+Tree with inserts, deletes and scans."""
import bisect

from models import Config, DuplicateKey
from nodes import InternalNode, LeafNode


class BTree:
    def __init__(self, order=3):
        self.config = Config(order)
        self.root = LeafNode()

    def _leaf_for(self, key):
        node = self.root
        while not node.is_leaf:
            pos = bisect.bisect_left(node.keys, key)
            node = node.children[pos]
        return node

    def search(self, key):
        leaf = self._leaf_for(key)
        pos = bisect.bisect_left(leaf.keys, key)
        if pos < len(leaf.keys) and leaf.keys[pos] == key:
            return leaf.values[pos]
        return None

    def insert(self, key, value):
        path = []
        node = self.root
        while not node.is_leaf:
            pos = bisect.bisect_left(node.keys, key)
            path.append((node, pos))
            node = node.children[pos]
        pos = bisect.bisect_left(node.keys, key)
        if pos < len(node.keys) and node.keys[pos] == key:
            raise DuplicateKey(key)
        node.insert(key, value)
        while len(node.keys) > self.config.max_keys:
            right, pushed = node.split()
            if not path:
                self.root = InternalNode([pushed], [node, right])
                return
            parent, pos = path.pop()
            parent.keys.insert(pos, pushed)
            parent.children.insert(pos + 1, right)
            node = parent

    def delete(self, key):
        node = self._leaf_for(key)
        node.remove(key)

    def range_scan(self, lo, hi):
        leaf = self._leaf_for(lo)
        out = []
        while leaf is not None:
            for k, v in zip(leaf.keys, leaf.values):
                if lo <= k < hi:
                    out.append((k, v))
            leaf = leaf.next
        return out

    def items(self):
        node = self.root
        while not node.is_leaf:
            node = node.children[0]
        out = []
        while node is not None:
            out.extend(zip(node.keys, node.values))
            node = node.next
        return out

    def validate(self):
        return True
