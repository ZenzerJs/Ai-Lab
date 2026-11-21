"""B+Tree with rebalancing insert/delete and inclusive range scans.

Conventions: `order` = max keys per node (from Config). Leaf nodes hold
(key, value) entries and are linked left-to-right. Internal separators
are copy-up separators: keys[i] equals the smallest key of the subtree
in children[i+1]. Search descends to the first separator > key.
"""
import bisect

from models import Config, DuplicateKey, KeyNotFound
from nodes import InternalNode, LeafNode


class BTree:
    def __init__(self, order=3):
        self.config = Config(order)
        self.root = LeafNode()

    def _leaf_for(self, key):
        node = self.root
        while not node.is_leaf:
            pos = bisect.bisect_right(node.keys, key)
            node = node.children[pos]
        return node

    def search(self, key):
        leaf = self._leaf_for(key)
        pos = bisect.bisect_left(leaf.keys, key)
        if pos < len(leaf.keys) and leaf.keys[pos] == key:
            return leaf.values[pos]
        return None

    def insert(self, key, value):
        """Insert or raise DuplicateKey; splits propagate up the path."""
        if not isinstance(key, int) or isinstance(key, bool):
            raise ValueError("keys must be ints")
        path = []
        node = self.root
        while not node.is_leaf:
            pos = bisect.bisect_right(node.keys, key)
            path.append((node, pos))
            node = node.children[pos]
        pos = bisect.bisect_left(node.keys, key)
        if pos < len(node.keys) and node.keys[pos] == key:
            raise DuplicateKey(key)
        node.insert(key, value)
        self._propagate_splits(path, node)

    def _propagate_splits(self, path, node):
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
        """Remove a key or raise KeyNotFound; underflow rebalances via
        borrow-or-merge and stale separators are refreshed."""
        path = []
        node = self.root
        while not node.is_leaf:
            pos = bisect.bisect_right(node.keys, key)
            path.append((node, pos))
            node = node.children[pos]
        try:
            node.remove(key)
        except KeyError:
            raise KeyNotFound(key)
        self._rebalance(path, node)

    def _rebalance(self, path, node):
        if not path:
            # Root: shrink an emptied internal root; an empty leaf is fine.
            if not node.is_leaf and not node.keys:
                self.root = node.children[0]
            return
        if len(node.keys) >= self.config.min_keys:
            self._refresh_separators(path)
            return
        parent, pos = path[-1]
        left = parent.children[pos - 1] if pos > 0 else None
        right = parent.children[pos + 1] if pos + 1 < len(parent.children) else None
        min_keys = self.config.min_keys

        if left is not None and len(left.keys) > min_keys:
            # Borrow the left sibling's last entry/separator-child.
            if node.is_leaf:
                k = left.keys.pop()
                v = left.values.pop()
                node.keys.insert(0, k)
                node.values.insert(0, v)
            else:
                sep = parent.keys[pos - 1]
                node.keys.insert(0, sep)
                node.children.insert(0, left.children.pop())
                parent.keys[pos - 1] = left.keys.pop()
            self._refresh_separators(path)
            return
        if right is not None and len(right.keys) > min_keys:
            # Borrow the right sibling's first entry/separator-child.
            if node.is_leaf:
                node.keys.append(right.keys.pop(0))
                node.values.append(right.values.pop(0))
            else:
                sep = parent.keys[pos]
                node.keys.append(sep)
                node.children.append(right.children.pop(0))
                parent.keys[pos] = right.keys.pop(0)
            return

        if left is not None:
            # Merge node into the left sibling.
            if node.is_leaf:
                left.keys.extend(node.keys)
                left.values.extend(node.values)
                left.next = node.next
            else:
                sep = parent.keys[pos - 1]
                left.keys.append(sep)
                left.keys.extend(node.keys)
                left.children.extend(node.children)
            parent.keys.pop(pos - 1)
            parent.children.pop(pos)
        else:
            # Merge the right sibling into node.
            if node.is_leaf:
                node.keys.extend(right.keys)
                node.values.extend(right.values)
                node.next = right.next
            else:
                sep = parent.keys[pos]
                node.keys.append(sep)
                node.keys.extend(right.keys)
                node.children.extend(right.children)
            parent.keys.pop(pos)
            parent.children.pop(pos + 1)
        self._rebalance(path[:-1], parent)

    def _refresh_separators(self, path):
        """Recompute separator keys along the descent path after a change."""
        for parent, pos in path:
            for i in range(len(parent.keys)):
                parent.keys[i] = self._min_key(parent.children[i + 1])

    def _min_key(self, node):
        while not node.is_leaf:
            node = node.children[0]
        return node.keys[0]

    def range_scan(self, lo, hi):
        """Inclusive [lo, hi] scan across the leaf chain."""
        if lo > hi:
            return []
        leaf = self._leaf_for(lo)
        out = []
        while leaf is not None:
            for k, v in zip(leaf.keys, leaf.values):
                if k < lo:
                    continue
                if k > hi:
                    return out
                out.append((k, v))
            leaf = leaf.next
        return out

    def items(self):
        """All (key, value) pairs in ascending key order via leaf chain."""
        node = self.root
        while not node.is_leaf:
            node = node.children[0]
        out = []
        while node is not None:
            out.extend(zip(node.keys, node.values))
            node = node.next
        return out

    def validate(self):
        """Assert structural invariants. Returns True or raises AssertionError."""
        cfg = self.config

        def check(node, is_root):
            assert node.keys == sorted(node.keys), "keys unsorted"
            if is_root:
                if not node.is_leaf:
                    assert len(node.keys) >= 1
            else:
                assert cfg.min_keys <= len(node.keys) <= cfg.max_keys, \
                    f"occupancy {len(node.keys)} out of bounds"
            if node.is_leaf:
                assert len(node.keys) == len(node.values)
            else:
                assert len(node.children) == len(node.keys) + 1, \
                    "children != keys + 1"
                for i in range(len(node.keys)):
                    assert node.keys[i] == self._min_key(node.children[i + 1]), \
                        "stale separator"
                for child in node.children:
                    check(child, False)

        check(self.root, True)
        chain = self.items()
        assert [k for k, _v in chain] == sorted(set(k for k, _v in chain))
        return True
