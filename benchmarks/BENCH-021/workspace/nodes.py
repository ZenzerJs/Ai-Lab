"""B+Tree node types."""
import bisect


class LeafNode:
    is_leaf = True

    def __init__(self, keys=None, values=None):
        self.keys = list(keys or [])
        self.values = list(values or [])
        self.next = None

    def insert(self, key, value):
        pos = bisect.bisect_left(self.keys, key)
        self.keys.insert(pos, key)
        self.values.insert(pos, value)

    def remove(self, key):
        pos = bisect.bisect_left(self.keys, key)
        self.keys.pop(pos)
        self.values.pop(pos)

    def split(self):
        mid = len(self.keys) // 2 - 1
        right = LeafNode(self.keys[mid:], self.values[mid:])
        right.next = self.next
        self.keys = self.keys[:mid]
        self.values = self.values[:mid]
        self.next = right
        return right, self.keys[-1] if self.keys else right.keys[0]


class InternalNode:
    is_leaf = False

    def __init__(self, keys=None, children=None):
        self.keys = list(keys or [])
        self.children = list(children or [])

    def split(self):
        mid = len(self.keys) // 2
        promoted = self.keys[mid]
        right = InternalNode(self.keys[mid:], self.children[mid:])
        self.keys = self.keys[:mid]
        self.children = self.children[:mid]
        return right, promoted
